"""Reconocimiento facial privado contra galería consentida; desactivado por defecto."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
import math
import os
from pathlib import Path
import re
import threading
from typing import Callable, Protocol, Sequence
from time import perf_counter


class FacePolicyError(PermissionError):
    pass


class FaceRecognitionError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class FaceAccessContext:
    user_id: str
    permissions: frozenset[str]
    chat_type: str = "private"
    linked: bool = True
    is_guest: bool = False
    is_admin: bool = False


@dataclass(frozen=True, slots=True)
class FaceIdentityRecord:
    person_id: str
    embeddings: tuple[tuple[float, ...], ...]
    model_version: str
    consent_at: str
    created_at: str
    updated_at: str
    active: bool = True
    revoked_at: str | None = None


@dataclass(frozen=True, slots=True)
class FaceMatch:
    status: str
    person_id: str | None = None
    confidence: float | None = None


class FaceRecognitionProvider(Protocol):
    def is_available(self) -> bool: ...
    def model_version(self) -> str: ...
    def embeddings(self, path: str | Path) -> Sequence[Sequence[float]]: ...
    def similarity(self, left: Sequence[float], right: Sequence[float]) -> float: ...


class FaceIdentityStore:
    """Solo persiste identificadores internos y vectores biométricos mínimos."""

    _ID = re.compile(r"^[a-z0-9][a-z0-9_-]{2,63}$")

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()

    def list_active(self, *, model_version: str | None = None) -> tuple[FaceIdentityRecord, ...]:
        records = self._read()
        return tuple(
            record for record in records.values()
            if record.active and (model_version is None or record.model_version == model_version)
        )

    def get(self, person_id: str) -> FaceIdentityRecord | None:
        return self._read().get(self._validate_id(person_id))

    def upsert(self, record: FaceIdentityRecord) -> None:
        key = self._validate_id(record.person_id)
        self._validate_record(record)
        with self._lock:
            records = self._read()
            records[key] = record
            self._write(records)

    def revoke(self, person_id: str, *, at: str) -> bool:
        key = self._validate_id(person_id)
        with self._lock:
            records = self._read()
            current = records.get(key)
            if current is None:
                return False
            records[key] = FaceIdentityRecord(
                current.person_id, (), current.model_version, current.consent_at,
                current.created_at, at, False, at,
            )
            self._write(records)
            return True

    def delete(self, person_id: str) -> bool:
        key = self._validate_id(person_id)
        with self._lock:
            records = self._read()
            removed = records.pop(key, None) is not None
            if removed:
                self._write(records)
            return removed

    def _read(self) -> dict[str, FaceIdentityRecord]:
        with self._lock:
            try:
                payload = json.loads(self.path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                return {}
            except (OSError, json.JSONDecodeError) as exc:
                raise FaceRecognitionError("face_store_corrupt", "El almacén facial no se puede leer con seguridad.") from exc
            raw_records = payload.get("identities", {}) if isinstance(payload, dict) else {}
            result: dict[str, FaceIdentityRecord] = {}
            if not isinstance(payload, dict) or not isinstance(raw_records, dict):
                raise FaceRecognitionError("face_store_corrupt", "El almacén facial tiene una estructura no válida.")
            for key, raw in raw_records.items():
                try:
                    record = FaceIdentityRecord(
                        person_id=str(raw["person_id"]),
                        embeddings=tuple(tuple(float(value) for value in vector) for vector in raw.get("embeddings", ())),
                        model_version=str(raw["model_version"]),
                        consent_at=str(raw["consent_at"]),
                        created_at=str(raw["created_at"]),
                        updated_at=str(raw["updated_at"]),
                        active=bool(raw.get("active", True)),
                        revoked_at=str(raw["revoked_at"]) if raw.get("revoked_at") else None,
                    )
                    self._validate_record(record)
                    result[self._validate_id(str(key))] = record
                except (KeyError, TypeError, ValueError) as exc:
                    raise FaceRecognitionError("face_store_corrupt", "El almacén facial contiene un registro no válido.") from exc
            return result

    def _write(self, records: dict[str, FaceIdentityRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{os.urandom(8).hex()}.tmp")
        payload = {"version": 1, "identities": {key: asdict(value) for key, value in records.items()}}
        descriptor = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            try:
                self.path.chmod(0o600)
            except OSError:
                pass
        finally:
            temporary.unlink(missing_ok=True)

    @classmethod
    def _validate_id(cls, value: str) -> str:
        clean = str(value).strip().casefold()
        if not cls._ID.fullmatch(clean):
            raise ValueError("Identificador facial interno no válido.")
        return clean

    @staticmethod
    def _validate_record(record: FaceIdentityRecord) -> None:
        dimensions = {len(vector) for vector in record.embeddings}
        if len(dimensions) > 1:
            raise ValueError("Los embeddings faciales no comparten dimensión.")
        for vector in record.embeddings:
            if not vector or len(vector) > 4096 or any(not math.isfinite(value) for value in vector):
                raise ValueError("Embedding facial no válido.")


class PrivateFaceRecognitionService:
    def __init__(
        self,
        store: FaceIdentityStore,
        provider: FaceRecognitionProvider,
        *,
        high_threshold: float = 0.88,
        low_threshold: float = 0.72,
        clock: Callable[[], datetime] | None = None,
        audit: Callable[[str, str], None] | None = None,
    ) -> None:
        if not 0 <= low_threshold < high_threshold <= 1:
            raise ValueError("Umbrales faciales no válidos.")
        self.store = store
        self.provider = provider
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
        self.clock = clock or (lambda: datetime.now(UTC))
        self.audit = audit or (lambda _action, _result: None)

    def enroll(self, person_id: str, photos: Sequence[str | Path], context: FaceAccessContext, *, consent_at: datetime, reinforced_confirmation: bool) -> FaceIdentityRecord:
        self._require(context, "face.enroll", admin=True)
        if not reinforced_confirmation:
            raise FacePolicyError("El alta facial requiere confirmación reforzada.")
        if consent_at.tzinfo is None or consent_at > self.clock():
            raise FacePolicyError("La fecha de consentimiento no es válida.")
        if len(photos) < 2:
            raise FaceRecognitionError("face_more_samples_required", "Se necesitan varias fotos válidas.")
        self._available()
        vectors: list[tuple[float, ...]] = []
        for photo in photos:
            faces = self.provider.embeddings(photo)
            if len(faces) != 1:
                raise FaceRecognitionError("face_image_not_suitable", "Cada foto debe contener un único rostro claro.")
            vectors.append(tuple(float(value) for value in faces[0]))
        now = self.clock().isoformat()
        previous = self.store.get(person_id)
        record = FaceIdentityRecord(
            FaceIdentityStore._validate_id(person_id), tuple(vectors), self.provider.model_version(),
            consent_at.isoformat(), previous.created_at if previous else now, now, True, None,
        )
        self.store.upsert(record)
        self.audit("face.enroll", "ok")
        return record

    def recognize(self, photo: str | Path, context: FaceAccessContext) -> tuple[FaceMatch, ...]:
        matches, _timings = self.recognize_with_timings(photo, context)
        return matches

    def recognize_with_timings(self, photo: str | Path, context: FaceAccessContext) -> tuple[tuple[FaceMatch, ...], dict[str, float]]:
        self._require(context, "face.recognize")
        self._available()
        started = perf_counter()
        probes = self.provider.embeddings(photo)
        detect_ms = round((perf_counter() - started) * 1000, 3)
        if not probes:
            return (FaceMatch("image_not_suitable"),), {"face.detect": detect_ms, "face.compare": 0.0}
        records = self.store.list_active(model_version=self.provider.model_version())
        matches: list[FaceMatch] = []
        started = perf_counter()
        for probe in probes:
            best_id = None
            best = -1.0
            for record in records:
                score = max((self.provider.similarity(probe, candidate) for candidate in record.embeddings), default=-1.0)
                if score > best:
                    best, best_id = score, record.person_id
            if best_id is not None and best >= self.high_threshold:
                matches.append(FaceMatch("recognized", best_id, round(best, 4)))
            elif best_id is not None and best >= self.low_threshold:
                matches.append(FaceMatch("possible_match", None, round(best, 4)))
            else:
                matches.append(FaceMatch("unrecognized"))
        self.audit("face.recognize", "ok")
        return tuple(matches), {
            "face.detect": detect_ms,
            "face.compare": round((perf_counter() - started) * 1000, 3),
        }

    def revoke(self, person_id: str, context: FaceAccessContext, *, reinforced_confirmation: bool, delete: bool = True) -> bool:
        self._require(context, "face.revoke", admin=True)
        if not reinforced_confirmation:
            raise FacePolicyError("La revocación facial requiere confirmación reforzada.")
        changed = self.store.delete(person_id) if delete else self.store.revoke(person_id, at=self.clock().isoformat())
        self.audit("face.revoke", "ok" if changed else "not_found")
        return changed

    def disable(self, person_id: str, context: FaceAccessContext, *, reinforced_confirmation: bool) -> bool:
        return self.revoke(person_id, context, reinforced_confirmation=reinforced_confirmation, delete=False)

    def regenerate(self, person_id: str, photos: Sequence[str | Path], context: FaceAccessContext, *, reinforced_confirmation: bool) -> FaceIdentityRecord:
        current = self.store.get(person_id)
        if current is None or not current.active:
            raise FaceRecognitionError("face_identity_missing", "La identidad facial no está activa.")
        return self.enroll(
            person_id,
            photos,
            context,
            consent_at=datetime.fromisoformat(current.consent_at),
            reinforced_confirmation=reinforced_confirmation,
        )

    def status(self, context: FaceAccessContext) -> dict[str, object]:
        self._require(context, "face.status", admin=True)
        return {"enabled": self.provider.is_available(), "active_identities": len(self.store.list_active())}

    def _require(self, context: FaceAccessContext, permission: str, *, admin: bool = False) -> None:
        if context.chat_type != "private" or not context.linked or context.is_guest:
            raise FacePolicyError("El reconocimiento facial solo admite chats privados vinculados y no invitados.")
        if permission not in context.permissions or (admin and not context.is_admin):
            raise FacePolicyError(f"Falta el permiso específico {permission}.")

    def _available(self) -> None:
        if not self.provider.is_available():
            raise FaceRecognitionError("face_provider_unavailable", "El proveedor facial local no está disponible.")
