"""Transcripción local desacoplada, sin descargas ni persistencia de contenido."""
from __future__ import annotations

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
from time import perf_counter
from typing import Iterable
import unicodedata
import wave


class STTError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class STTResult:
    text: str
    language: str | None = None
    duration_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class STTConfig:
    model: str = "small"
    model_path: Path | None = None
    device: str = "cpu"
    compute_type: str = "int8"
    timeout_seconds: float = 90.0
    max_audio_seconds: float = 180.0
    allow_model_download: bool = False

    @classmethod
    def from_env(cls, env=None) -> "STTConfig":
        values = os.environ if env is None else env
        path = str(values.get("ATLAS_STT_MODEL_PATH", "")).strip()
        return cls(
            model=str(values.get("ATLAS_STT_MODEL", "small")).strip() or "small",
            model_path=Path(path) if path else None,
            device=str(values.get("ATLAS_STT_DEVICE", "cpu")).strip() or "cpu",
            compute_type=str(values.get("ATLAS_STT_COMPUTE_TYPE", "int8")).strip() or "int8",
            timeout_seconds=float(values.get("ATLAS_STT_TIMEOUT_SECONDS", "90")),
            max_audio_seconds=float(values.get("ATLAS_STT_MAX_AUDIO_SECONDS", "180")),
            allow_model_download=str(values.get("ATLAS_STT_ALLOW_MODEL_DOWNLOAD", "false")).casefold() in {"1", "true", "yes", "on"},
        )


class BaseSTTProvider(ABC):
    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def transcribe(self, path: str | Path, language_hint: str | None = None) -> STTResult: ...

    @abstractmethod
    def health(self) -> dict[str, object]: ...

    @abstractmethod
    def supported_languages(self) -> Iterable[str]: ...


class FasterWhisperSTTProvider(BaseSTTProvider):
    """Adaptador opcional. Nunca descarga modelos salvo habilitación explícita."""

    def __init__(self, config: STTConfig | None = None) -> None:
        self.config = config or STTConfig.from_env()
        self._model = None

    def is_available(self) -> bool:
        package = importlib.util.find_spec("faster_whisper") is not None
        model_ready = bool(
            self.config.allow_model_download
            or (self.config.model_path and self.config.model_path.is_dir())
        )
        return package and model_ready

    def health(self) -> dict[str, object]:
        return {
            "available": self.is_available(),
            "provider": "faster-whisper",
            "device": self.config.device,
            "model_local": bool(self.config.model_path and self.config.model_path.is_dir()),
            "download_allowed": self.config.allow_model_download,
        }

    def supported_languages(self) -> Iterable[str]:
        return ("auto", "es", "ca", "en")

    def transcribe(self, path: str | Path, language_hint: str | None = None) -> STTResult:
        if not self.is_available():
            raise STTError("stt_unavailable", "El reconocimiento de voz local no está disponible.")
        if self._model is None:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]

            source = str(self.config.model_path or self.config.model)
            self._model = WhisperModel(
                source,
                device=self.config.device,
                compute_type=self.config.compute_type,
                local_files_only=not self.config.allow_model_download,
            )
        segments, info = self._model.transcribe(
            str(path),
            language=language_hint or None,
            vad_filter=True,
        )
        text = " ".join(str(segment.text).strip() for segment in segments).strip()
        return STTResult(
            text=text,
            language=getattr(info, "language", language_hint),
            duration_seconds=getattr(info, "duration", None),
        )


class AudioConverter:
    def __init__(self, *, ffmpeg_path: str | None = None, timeout_seconds: float = 30.0) -> None:
        self.ffmpeg_path = shutil.which("ffmpeg") if ffmpeg_path is None else ffmpeg_path
        self.timeout_seconds = timeout_seconds

    def is_available(self) -> bool:
        return bool(self.ffmpeg_path)

    def to_mono_16khz(self, source: str | Path, destination: str | Path, *, max_seconds: float) -> float:
        if not self.ffmpeg_path:
            raise STTError("ffmpeg_unavailable", "FFmpeg no está disponible.")
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        command = [
            self.ffmpeg_path, "-nostdin", "-v", "error", "-y", "-i", str(source),
            "-t", str(max_seconds + 0.1), "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(target),
        ]
        try:
            completed = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=self.timeout_seconds,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired as exc:
            target.unlink(missing_ok=True)
            raise STTError("audio_convert_timeout", "La conversión de audio agotó el tiempo.") from exc
        except OSError as exc:
            target.unlink(missing_ok=True)
            raise STTError("ffmpeg_unavailable", "FFmpeg no está disponible.") from exc
        if completed.returncode != 0 or not target.is_file():
            target.unlink(missing_ok=True)
            raise STTError("audio_corrupt", "El audio no se puede convertir.")
        try:
            with wave.open(str(target), "rb") as audio:
                if audio.getnchannels() != 1 or audio.getframerate() != 16000:
                    raise STTError("audio_invalid_format", "La conversión no produjo WAV mono a 16 kHz.")
                frames = audio.getnframes()
                duration = frames / float(audio.getframerate())
        except (wave.Error, EOFError) as exc:
            target.unlink(missing_ok=True)
            raise STTError("audio_corrupt", "El WAV convertido no es válido.") from exc
        if frames <= 0 or duration <= 0:
            target.unlink(missing_ok=True)
            raise STTError("audio_empty", "El audio no contiene voz utilizable.")
        if duration > max_seconds:
            target.unlink(missing_ok=True)
            raise STTError("audio_too_long", "El audio supera la duración permitida.")
        return duration


class STTService:
    def __init__(
        self,
        provider: BaseSTTProvider,
        converter: AudioConverter,
        *,
        config: STTConfig | None = None,
        work_dir: str | Path,
        clock=perf_counter,
    ) -> None:
        self.provider = provider
        self.converter = converter
        self.config = config or STTConfig.from_env()
        self.work_dir = Path(work_dir)
        self.clock = clock

    def transcribe(self, source: str | Path, *, language_hint: str | None = None) -> tuple[STTResult, dict[str, float]]:
        if not self.provider.is_available():
            raise STTError("stt_unavailable", "El reconocimiento de voz local no está disponible.")
        self.work_dir.mkdir(parents=True, exist_ok=True)
        wav_path = self.work_dir / f"stt_{os.urandom(16).hex()}.wav"
        timings: dict[str, float] = {}
        try:
            started = self.clock()
            duration = self.converter.to_mono_16khz(
                source, wav_path, max_seconds=self.config.max_audio_seconds
            )
            timings["audio.convert"] = round((self.clock() - started) * 1000, 3)
            started = self.clock()
            executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="atlas-stt")
            future = executor.submit(self.provider.transcribe, wav_path, language_hint)
            try:
                result = future.result(timeout=self.config.timeout_seconds)
            except FutureTimeout as exc:
                future.cancel()
                future.add_done_callback(lambda _future: self._safe_unlink(wav_path))
                executor.shutdown(wait=False, cancel_futures=True)
                raise STTError("stt_timeout", "La transcripción agotó el tiempo.") from exc
            else:
                executor.shutdown(wait=True)
            timings["stt.transcribe"] = round((self.clock() - started) * 1000, 3)
            text = unicodedata.normalize("NFC", " ".join(result.text.split())).strip()
            if not text:
                raise STTError("audio_empty", "No se ha detectado habla utilizable.")
            return STTResult(text, result.language, result.duration_seconds or duration), timings
        finally:
            self._safe_unlink(wav_path)

    @staticmethod
    def _safe_unlink(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
