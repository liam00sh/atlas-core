from __future__ import annotations

import hashlib
import wave
from dataclasses import dataclass, field
from pathlib import Path

from .constants import EMOTIONS, INTENTIONS, QUALITY, REVIEW_STATUS
from .models import ProjectConfig, Sample


@dataclass(slots=True)
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked_files: int = 0
    total_duration: float = 0.0

    @property
    def valid(self) -> bool:
        return not self.errors

    @property
    def status(self) -> str:
        return "VALID" if self.valid else "INVALID"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_dataset(config: ProjectConfig, samples: list[Sample], full_hash: bool = True) -> ValidationResult:
    result = ValidationResult()
    ids: set[str] = set()
    paths: set[str] = set()
    hashes: dict[str, str] = {}
    for sample in samples:
        prefix = sample.sample_id or "<sin-id>"
        if sample.sample_id in ids:
            result.errors.append(f"sample_id duplicado: {sample.sample_id}")
        ids.add(sample.sample_id)
        normalized = Path(sample.relative_path)
        if normalized.is_absolute() or ".." in normalized.parts:
            result.errors.append(f"{prefix}: ruta no relativa o insegura")
            continue
        key = normalized.as_posix().casefold()
        if key in paths:
            result.errors.append(f"ruta duplicada: {sample.relative_path}")
        paths.add(key)
        audio = config.audio_root / normalized
        if not audio.is_file():
            result.errors.append(f"{prefix}: audio ausente: {sample.relative_path}")
            continue
        try:
            with wave.open(str(audio), "rb") as wav:
                if wav.getcomptype() != "NONE":
                    result.errors.append(f"{prefix}: WAV no PCM")
                duration = wav.getnframes() / wav.getframerate()
                result.total_duration += duration
                if sample.sample_rate and wav.getframerate() != sample.sample_rate:
                    result.errors.append(f"{prefix}: frecuencia no coincide")
                if sample.channels and wav.getnchannels() != sample.channels:
                    result.errors.append(f"{prefix}: canales no coinciden")
        except (wave.Error, EOFError, OSError) as exc:
            result.errors.append(f"{prefix}: WAV corrupto: {exc}")
            continue
        result.checked_files += 1
        if full_hash:
            digest = sha256_file(audio)
            if sample.sha256 and digest != sample.sha256:
                result.errors.append(f"{prefix}: hash SHA-256 incorrecto")
            if digest in hashes and hashes[digest] != sample.sample_id:
                result.errors.append(f"audio duplicado exacto: {hashes[digest]} y {sample.sample_id}")
            hashes[digest] = sample.sample_id
        if sample.emotion not in EMOTIONS:
            result.errors.append(f"{prefix}: emoción inválida: {sample.emotion}")
        if sample.intention not in INTENTIONS:
            result.errors.append(f"{prefix}: intención inválida: {sample.intention}")
        if sample.quality not in QUALITY:
            result.errors.append(f"{prefix}: calidad inválida: {sample.quality}")
        if sample.review_status not in REVIEW_STATUS:
            result.errors.append(f"{prefix}: estado inválido: {sample.review_status}")
    if any(sample.review_status == "pending_review" for sample in samples):
        result.warnings.append("El dataset no puede cerrarse: quedan muestras pending_review")
    return result
