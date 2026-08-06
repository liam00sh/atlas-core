"""Transporte multimedia Telegram seguro, común y sin análisis de contenido."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import secrets
from time import perf_counter, time
from typing import Mapping
import zipfile

from telegram_interface.client import TelegramClientError, TelegramClientProtocol


class TelegramMediaError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class TelegramMediaEnvelope:
    media_type: str
    file_id: str
    declared_size: int | None = None
    declared_mime: str | None = None
    remote_path: str | None = None
    quarantine_path: Path | None = None
    detected_mime: str | None = None
    byte_size: int | None = None
    sha256: str | None = field(default=None, repr=False)
    timings_ms: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TelegramMediaLimits:
    voice: int = 12 * 1024 * 1024
    audio: int = 25 * 1024 * 1024
    photo: int = 12 * 1024 * 1024
    document: int = 20 * 1024 * 1024

    def for_type(self, media_type: str) -> int:
        if media_type not in {"voice", "audio", "photo", "document"}:
            raise TelegramMediaError("rejected_type", "Tipo multimedia no permitido.")
        return int(getattr(self, media_type))


class TelegramMediaValidator:
    """Detecta tipo real y estructuras peligrosas sin confiar en Telegram."""

    EXTENSIONS = {
        "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
        "audio/ogg": ".ogg", "audio/wav": ".wav", "audio/mpeg": ".mp3",
        "audio/mp4": ".m4a", "application/pdf": ".pdf",
        "text/plain": ".txt", "text/markdown": ".md", "application/json": ".json",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    }
    ALLOWED_BY_TYPE = {
        "voice": {"audio/ogg"},
        "audio": {"audio/ogg", "audio/wav", "audio/mpeg", "audio/mp4"},
        "photo": {"image/jpeg", "image/png", "image/webp"},
        "document": {
            "image/jpeg", "image/png", "image/webp", "application/pdf",
            "text/plain", "text/markdown", "application/json",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
    }
    EXECUTABLE_SIGNATURES = (b"MZ", b"\x7fELF", b"#!", b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf")
    GENERIC_MIMES = frozenset({"application/octet-stream", "binary/octet-stream"})
    DECLARED_MIME_ALIASES = {
        "audio/ogg": frozenset({"audio/ogg", "audio/opus", "audio/x-ogg", "application/ogg"}),
        "audio/wav": frozenset({"audio/wav", "audio/wave", "audio/x-wav"}),
        "audio/mpeg": frozenset({"audio/mpeg", "audio/mp3"}),
        "audio/mp4": frozenset({"audio/mp4", "audio/x-m4a"}),
    }
    _OGG_CRC_TABLE: tuple[int, ...] | None = None

    def validate(
        self,
        path: str | Path,
        *,
        media_type: str,
        max_bytes: int,
        declared_mime: str | None = None,
    ) -> tuple[str, int, str]:
        target = Path(path)
        size = target.stat().st_size
        if size <= 0:
            raise TelegramMediaError("media_empty", "El archivo está vacío.")
        if size > max_bytes:
            raise TelegramMediaError("rejected_too_large", "El archivo supera el límite.")
        data = target.read_bytes()
        if data.startswith(self.EXECUTABLE_SIGNATURES):
            raise TelegramMediaError("media_executable", "Contenido ejecutable rechazado.")
        mime = self._detect(data, target)
        if mime not in self.ALLOWED_BY_TYPE.get(media_type, set()):
            raise TelegramMediaError("rejected_type", "La firma real no corresponde a un formato permitido.")
        declared = str(declared_mime or "").split(";", 1)[0].strip().casefold()
        if declared and declared not in self.GENERIC_MIMES:
            aliases = self.DECLARED_MIME_ALIASES.get(mime, frozenset({mime}))
            if declared not in aliases:
                raise TelegramMediaError("mime_mismatch", "El MIME declarado contradice la firma real.")
        self._validate_structure(data, target, mime)
        return mime, size, hashlib.sha256(data).hexdigest()

    def _detect(self, data: bytes, path: Path) -> str:
        if data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return "image/webp"
        if data.startswith(b"OggS"):
            return "audio/ogg"
        if data.startswith(b"RIFF") and data[8:12] == b"WAVE":
            return "audio/wav"
        if data.startswith(b"ID3") or data[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}:
            return "audio/mpeg"
        if len(data) >= 12 and data[4:8] == b"ftyp":
            if data[8:12] in {b"M4A ", b"M4B "}:
                return "audio/mp4"
            raise TelegramMediaError("rejected_type", "El contenedor MP4 no demuestra ser solo audio.")
        if data.startswith(b"%PDF-"):
            return "application/pdf"
        if data.startswith(b"PK\x03\x04") and zipfile.is_zipfile(path):
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise TelegramMediaError("media_corrupt", "Formato binario desconocido.") from exc
        if "\x00" in text or any(ord(char) < 9 for char in text):
            raise TelegramMediaError("media_corrupt", "Texto con bytes de control rechazado.")
        try:
            json.loads(text)
            return "application/json"
        except json.JSONDecodeError:
            return "text/markdown" if path.suffix.casefold() in {".md", ".markdown"} else "text/plain"

    def _validate_structure(self, data: bytes, path: Path, mime: str) -> None:
        if mime == "audio/ogg":
            self._validate_ogg(data)
        if mime == "image/jpeg" and not data.rstrip().endswith(b"\xff\xd9"):
            raise TelegramMediaError("media_corrupt", "JPEG incompleto.")
        if mime == "image/png":
            marker = data.rfind(b"IEND")
            if marker < 0 or len(data[marker + 4 :].strip(b"\x00\r\n\t ")) > 4:
                raise TelegramMediaError("media_corrupt", "PNG incompleto o con datos añadidos.")
        if mime in {"image/webp", "audio/wav"}:
            if len(data) < 12 or int.from_bytes(data[4:8], "little") + 8 != len(data):
                raise TelegramMediaError("media_corrupt", "Contenedor RIFF incompleto.")
        if mime == "application/pdf":
            if b"%%EOF" not in data[-2048:]:
                raise TelegramMediaError("media_corrupt", "PDF incompleto.")
            forbidden = (b"/JavaScript", b"/JS", b"/Launch", b"/EmbeddedFile")
            if any(marker in data for marker in forbidden):
                raise TelegramMediaError("media_active_content", "PDF con contenido activo rechazado.")
        if mime.endswith("wordprocessingml.document"):
            self._validate_docx(path)

    @classmethod
    def _validate_ogg(cls, data: bytes) -> None:
        """Valida páginas, CRC, secuencias y cabeceras Opus/Vorbis."""
        streams: dict[int, dict[str, object]] = {}
        offset = 0
        while offset < len(data):
            remaining = len(data) - offset
            if data[offset : offset + 4] != b"OggS":
                if data[offset:].startswith(cls.EXECUTABLE_SIGNATURES):
                    raise TelegramMediaError("media_polyglot", "Contenido añadido tras el OGG.")
                raise TelegramMediaError("media_corrupt", "Captura OggS ausente entre páginas.")
            if remaining < 27:
                raise TelegramMediaError("media_corrupt", "Página OGG truncada.")
            if data[offset + 4] != 0:
                raise TelegramMediaError("media_corrupt", "Versión de bitstream OGG no admitida.")
            flags = data[offset + 5]
            if flags & ~0x07:
                raise TelegramMediaError("media_corrupt", "Flags de página OGG no válidos.")
            segment_count = data[offset + 26]
            header_end = offset + 27 + segment_count
            if header_end > len(data):
                raise TelegramMediaError("media_corrupt", "Tabla de segmentos OGG truncada.")
            lacing = data[offset + 27 : header_end]
            body_end = header_end + sum(lacing)
            if body_end > len(data):
                raise TelegramMediaError("media_corrupt", "Contenido de página OGG truncado.")
            page = bytearray(data[offset:body_end])
            expected_crc = int.from_bytes(page[22:26], "little")
            page[22:26] = b"\x00\x00\x00\x00"
            if cls._ogg_crc(page) != expected_crc:
                raise TelegramMediaError("media_corrupt", "CRC de página OGG no válido.")

            serial = int.from_bytes(data[offset + 14 : offset + 18], "little")
            sequence = int.from_bytes(data[offset + 18 : offset + 22], "little")
            bos = bool(flags & 0x02)
            continued = bool(flags & 0x01)
            eos = bool(flags & 0x04)
            state = streams.get(serial)
            if state is None:
                if not bos or continued or sequence != 0:
                    raise TelegramMediaError("media_corrupt", "Flujo OGG sin página inicial válida.")
                state = {
                    "sequence": sequence,
                    "partial": bytearray(),
                    "packets": [],
                    "packet_count": 0,
                    "eos": False,
                }
                streams[serial] = state
            else:
                if bos or bool(state["eos"]):
                    raise TelegramMediaError("media_corrupt", "Secuencia de páginas OGG incoherente.")
                expected_sequence = (int(state["sequence"]) + 1) & 0xFFFFFFFF
                if sequence != expected_sequence:
                    raise TelegramMediaError("media_corrupt", "Falta una página OGG o está desordenada.")
                if continued != bool(state["partial"]):
                    raise TelegramMediaError("media_corrupt", "Continuación de paquete OGG incoherente.")
                state["sequence"] = sequence

            partial = state["partial"]
            packets = state["packets"]
            assert isinstance(partial, bytearray) and isinstance(packets, list)
            cursor = header_end
            for length in lacing:
                partial.extend(data[cursor : cursor + length])
                cursor += length
                if len(partial) > 1024 * 1024:
                    raise TelegramMediaError("media_corrupt", "Paquete OGG excesivamente grande.")
                if length < 255:
                    if len(packets) < 4:
                        packets.append(bytes(partial))
                    state["packet_count"] = int(state["packet_count"]) + 1
                    partial.clear()
            if eos:
                if partial:
                    raise TelegramMediaError("media_corrupt", "OGG termina con un paquete incompleto.")
                state["eos"] = True
            offset = body_end

        if not streams or any(bool(state["partial"]) for state in streams.values()):
            raise TelegramMediaError("media_corrupt", "Flujo OGG termina con un paquete incompleto.")
        for state in streams.values():
            packets = state["packets"]
            assert isinstance(packets, list)
            cls._validate_ogg_codec(packets, int(state["packet_count"]))

    @classmethod
    def _ogg_crc(cls, data: bytes | bytearray) -> int:
        if cls._OGG_CRC_TABLE is None:
            table = []
            for value in range(256):
                register = value << 24
                for _ in range(8):
                    register = ((register << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if register & 0x80000000 else (register << 1) & 0xFFFFFFFF
                table.append(register)
            cls._OGG_CRC_TABLE = tuple(table)
        crc = 0
        for value in data:
            crc = ((crc << 8) & 0xFFFFFFFF) ^ cls._OGG_CRC_TABLE[((crc >> 24) & 0xFF) ^ value]
        return crc

    @staticmethod
    def _validate_ogg_codec(packets: list[bytes], packet_count: int) -> None:
        if not packets:
            raise TelegramMediaError("media_corrupt", "OGG no contiene cabecera de códec.")
        identification = packets[0]
        if identification.startswith(b"OpusHead"):
            if len(identification) < 19 or identification[8] == 0 or identification[9] == 0:
                raise TelegramMediaError("media_corrupt", "Cabecera OpusHead no válida.")
            mapping_family = identification[18]
            if mapping_family == 0 and (identification[9] > 2 or len(identification) != 19):
                raise TelegramMediaError("media_corrupt", "Mapeo de canales Opus incoherente.")
            if mapping_family != 0 and len(identification) < 21 + identification[9]:
                raise TelegramMediaError("media_corrupt", "Tabla de canales Opus truncada.")
            if len(packets) < 3 or not packets[1].startswith(b"OpusTags") or packet_count < 3:
                raise TelegramMediaError("media_corrupt", "Cabeceras obligatorias Opus incompletas.")
            return
        if identification.startswith(b"\x01vorbis"):
            if len(identification) != 30 or int.from_bytes(identification[7:11], "little") != 0:
                raise TelegramMediaError("media_corrupt", "Cabecera de identificación Vorbis no válida.")
            channels = identification[11]
            sample_rate = int.from_bytes(identification[12:16], "little")
            blocksize = identification[28]
            if not channels or not sample_rate or not (6 <= (blocksize & 0x0F) <= (blocksize >> 4) <= 13) or not (identification[29] & 1):
                raise TelegramMediaError("media_corrupt", "Parámetros Vorbis no válidos.")
            if len(packets) < 4 or not packets[1].startswith(b"\x03vorbis") or not packets[2].startswith(b"\x05vorbis") or packet_count < 4:
                raise TelegramMediaError("media_corrupt", "Cabeceras obligatorias Vorbis incompletas.")
            return
        raise TelegramMediaError("rejected_type", "El OGG no contiene audio Opus o Vorbis permitido.")

    @staticmethod
    def _validate_docx(path: Path) -> None:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > 2000:
                raise TelegramMediaError("media_zip_bomb", "Documento con demasiadas entradas.")
            total = 0
            for info in infos:
                parts = PurePosixPath(info.filename).parts
                if info.filename.startswith(("/", "\\")) or ".." in parts or "\\" in info.filename or ":" in parts[0]:
                    raise TelegramMediaError("media_path_traversal", "Ruta interna insegura.")
                if info.filename.casefold().endswith(("vbaproject.bin", ".exe", ".dll", ".js", ".ps1")):
                    raise TelegramMediaError("media_active_content", "Macros o ejecutables rechazados.")
                total += int(info.file_size)
                if total > 100 * 1024 * 1024 or (info.compress_size and info.file_size / info.compress_size > 100):
                    raise TelegramMediaError("media_zip_bomb", "Documento comprimido peligroso.")
            names = {item.filename for item in infos}
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise TelegramMediaError("media_corrupt", "El archivo ZIP no es un DOCX válido.")


class TelegramMediaQuarantine:
    def __init__(self, root: str | Path, *, clock=time) -> None:
        self.root = Path(root)
        self.clock = clock

    def allocate(self, extension: str) -> Path:
        day = datetime.fromtimestamp(self.clock(), tz=UTC).strftime("%Y-%m-%d")
        folder = self.root / day
        folder.mkdir(parents=True, exist_ok=True)
        try:
            folder.chmod(0o700)
        except OSError:
            pass
        return folder / f"{secrets.token_hex(16)}{extension}"

    def secure(self, path: Path) -> None:
        try:
            path.chmod(0o600)
        except OSError:
            pass

    def cleanup(self, path: str | Path | None) -> None:
        if path is None:
            return
        target = Path(path)
        try:
            target.resolve().relative_to(self.root.resolve())
        except (OSError, ValueError):
            return
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass

    def cleanup_expired(self, *, ttl_hours: int, now: float | None = None) -> None:
        if not self.root.exists():
            return
        cutoff = (self.clock() if now is None else now) - max(0, ttl_hours) * 3600
        for path in self.root.rglob("*"):
            try:
                if path.is_file() and path.stat().st_mtime <= cutoff:
                    self.cleanup(path)
            except OSError:
                continue


class TelegramMediaDownloader:
    def __init__(self, client: TelegramClientProtocol, quarantine: TelegramMediaQuarantine, validator: TelegramMediaValidator, limits: TelegramMediaLimits) -> None:
        self.client = client
        self.quarantine = quarantine
        self.validator = validator
        self.limits = limits

    def download(self, envelope: TelegramMediaEnvelope) -> TelegramMediaEnvelope:
        limit = self.limits.for_type(envelope.media_type)
        if envelope.media_type == "document" and not (envelope.declared_mime or "").strip():
            raise TelegramMediaError("rejected_type", "El documento no declara un tipo permitido.")
        if envelope.declared_size and envelope.declared_size > limit:
            raise TelegramMediaError("rejected_too_large", "El archivo supera el límite.")
        download_started = perf_counter()
        metadata = self.client.get_file(file_id=envelope.file_id)
        remote_path = self._safe_remote_path(metadata.get("file_path"))
        metadata_size = int(metadata.get("file_size") or 0)
        if metadata_size and metadata_size > limit:
            raise TelegramMediaError("rejected_too_large", "El archivo supera el límite.")
        provisional = self.quarantine.allocate(".quarantine")
        downloaded_path = provisional
        try:
            path = self.client.download_file(file_path=remote_path, destination=provisional, max_bytes=limit)
            downloaded_path = Path(path)
            try:
                downloaded_path.resolve().relative_to(self.quarantine.root.resolve())
            except (OSError, ValueError) as exc:
                raise TelegramMediaError("media_path_traversal", "La descarga salió de la cuarentena.") from exc
            self.quarantine.secure(path)
            downloaded_ms = round((perf_counter() - download_started) * 1000, 3)
            validation_started = perf_counter()
            mime, size, digest = self.validator.validate(
                path,
                media_type=envelope.media_type,
                max_bytes=limit,
                declared_mime=envelope.declared_mime,
            )
            validation_ms = round((perf_counter() - validation_started) * 1000, 3)
            final = path.with_suffix(self.validator.EXTENSIONS[mime])
            os.replace(path, final)
            self.quarantine.secure(final)
            return TelegramMediaEnvelope(
                media_type=envelope.media_type, file_id=envelope.file_id,
                declared_size=envelope.declared_size, declared_mime=envelope.declared_mime,
                remote_path=remote_path,
                quarantine_path=final, detected_mime=mime, byte_size=size,
                sha256=digest,
                timings_ms={"media.download": downloaded_ms, "media.validation": validation_ms},
            )
        except Exception:
            self.quarantine.cleanup(provisional)
            if downloaded_path != provisional:
                self.quarantine.cleanup(downloaded_path)
            raise

    @staticmethod
    def _safe_remote_path(value: object) -> str:
        remote = str(value or "").strip()
        parts = PurePosixPath(remote).parts
        if not remote or "://" in remote or ".." in parts or remote.startswith(("/", "\\")):
            raise TelegramMediaError("metadata_missing", "Ruta remota insegura.")
        return remote


class TelegramMediaCleanup:
    def __init__(self, quarantine: TelegramMediaQuarantine) -> None:
        self.quarantine = quarantine

    def cleanup(self, envelope: TelegramMediaEnvelope | None) -> None:
        if envelope is not None:
            self.quarantine.cleanup(envelope.quarantine_path)


class TelegramMediaPipeline:
    def __init__(self, downloader: TelegramMediaDownloader) -> None:
        self.downloader = downloader

    def receive(
        self,
        *,
        media_type: str,
        file_id: str,
        declared_size: int | None = None,
        declared_mime: str | None = None,
    ) -> TelegramMediaEnvelope:
        return self.downloader.download(
            TelegramMediaEnvelope(media_type, file_id, declared_size, declared_mime)
        )
