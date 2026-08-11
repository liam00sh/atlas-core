"""Transcripción local desacoplada, sin descargas ni persistencia de contenido."""
from __future__ import annotations

from abc import ABC, abstractmethod
from array import array
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from enum import StrEnum
import importlib.util
import logging
import os
from pathlib import Path
import shutil
import subprocess
from time import perf_counter
from typing import Iterable
import inspect
import unicodedata
import wave


logger = logging.getLogger(__name__)


CONTEXT_HOTWORDS = {
    "general": "Daxter Atlas Telegram Docker",
    "home_assistant": "enciende apaga acuario pequeño luz Home Assistant",
    "confirmation": "confirmar cancelar cancelado cancela no déjalo",
    "reminder": "recuérdame mañana horas Atlas",
}


def contextual_hotwords(context_hint: str, fallback: str = "") -> str:
    selected = CONTEXT_HOTWORDS.get(str(context_hint).strip().casefold())
    return selected or fallback


def _repair_utf8_mojibake(value: str) -> str:
    if "\u00c3" not in value:
        return value
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


class STTError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class STTConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class STTResult:
    text: str
    language: str | None = None
    duration_seconds: float | None = None
    confidence: STTConfidence = STTConfidence.HIGH
    confidence_score: float | None = None
    avg_logprob: float | None = None
    no_speech_probability: float | None = None
    language_probability: float | None = None
    mean_word_probability: float | None = None
    min_word_probability: float | None = None
    compression_ratio: float | None = None
    vad_speech_seconds: float | None = None
    audio_rms: float | None = None
    audio_peak: float | None = None
    silence_ratio: float | None = None
    clipping_ratio: float | None = None


@dataclass(frozen=True, slots=True)
class STTConfig:
    model: str = "small"
    model_path: Path | None = None
    device: str = "auto"
    compute_type: str = "auto"
    timeout_seconds: float = 90.0
    max_audio_seconds: float = 180.0
    allow_model_download: bool = False
    language_hint: str | None = None
    high_logprob: float = -0.55
    medium_logprob: float = -1.05
    high_no_speech: float = 0.35
    medium_no_speech: float = 0.65
    high_language_probability: float = 0.50
    medium_language_probability: float = 0.25
    beam_size: int = 3
    initial_prompt: str = ""
    hotwords: str = "Atlas Daxter Telegram Home Assistant acuario"

    @classmethod
    def from_env(cls, env=None) -> "STTConfig":
        values = os.environ if env is None else env
        path = str(values.get("ATLAS_STT_MODEL_PATH", "")).strip()
        return cls(
            model=str(values.get("ATLAS_STT_MODEL", "small")).strip() or "small",
            model_path=Path(path) if path else None,
            device=str(values.get("ATLAS_STT_DEVICE", "auto")).strip().casefold() or "auto",
            compute_type=str(values.get("ATLAS_STT_COMPUTE_TYPE", "auto")).strip().casefold() or "auto",
            timeout_seconds=float(values.get("ATLAS_STT_TIMEOUT", values.get("ATLAS_STT_TIMEOUT_SECONDS", "90"))),
            max_audio_seconds=float(values.get("ATLAS_STT_MAX_AUDIO_SECONDS", "180")),
            allow_model_download=str(values.get("ATLAS_STT_ALLOW_MODEL_DOWNLOAD", "false")).casefold() in {"1", "true", "yes", "on"},
            language_hint=(str(values.get("ATLAS_STT_LANGUAGE_HINT", "")).strip() or None),
            beam_size=max(1, int(values.get("ATLAS_STT_BEAM_SIZE", "3"))),
            initial_prompt=str(values.get(
                "ATLAS_STT_INITIAL_PROMPT",
                "",
            )).strip(),
            hotwords=str(values.get(
                "ATLAS_STT_HOTWORDS",
                "Atlas Daxter Telegram Home Assistant acuario",
            )).strip(),
        )


@dataclass(frozen=True, slots=True)
class STTBackend:
    device: str
    compute_type: str
    fallback_reason: str | None = None


def _windows_dll_available(name: str) -> bool:
    if os.name != "nt":
        return True
    search = [Path(item) for item in os.environ.get("PATH", "").split(os.pathsep) if item]
    cuda_path = os.environ.get("CUDA_PATH")
    if cuda_path:
        search.append(Path(cuda_path) / "bin")
    return any((directory / name).is_file() for directory in search)


def resolve_stt_backend(config: STTConfig) -> STTBackend:
    requested = "cuda" if config.device in {"cuda", "gpu"} else config.device
    if requested not in {"auto", "cuda", "cpu"}:
        return STTBackend("cpu", "int8", f"dispositivo no reconocido: {requested}")
    reason = None
    cuda_ready = False
    if requested in {"auto", "cuda"}:
        try:
            import ctranslate2  # type: ignore[import-not-found]

            cuda_ready = int(ctranslate2.get_cuda_device_count()) > 0
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            reason = f"CUDA no disponible en CTranslate2 ({type(exc).__name__})"
        if cuda_ready and os.name == "nt":
            missing = [name for name in ("cublas64_12.dll", "cudnn64_9.dll") if not _windows_dll_available(name)]
            if missing:
                cuda_ready = False
                reason = "faltan bibliotecas CUDA/cuDNN: " + ", ".join(missing)
        elif not cuda_ready and reason is None:
            reason = "CTranslate2 no detecta una GPU CUDA utilizable"
    if requested in {"auto", "cuda"} and cuda_ready:
        compute = "float16" if config.compute_type == "auto" else config.compute_type
        return STTBackend("cuda", compute)
    compute = "int8" if config.compute_type == "auto" else config.compute_type
    if requested == "cpu":
        reason = None
    return STTBackend("cpu", compute, reason)


def find_local_faster_whisper_model(config: STTConfig) -> Path | None:
    required = ("config.json", "model.bin", "tokenizer.json")
    if config.model_path and all((config.model_path / name).is_file() for name in required):
        return config.model_path
    model_name = config.model.removeprefix("faster-whisper-")
    cache_root = Path(
        os.environ.get("HUGGINGFACE_HUB_CACHE")
        or Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
    )
    repository = cache_root / f"models--Systran--faster-whisper-{model_name}"
    ref = repository / "refs" / "main"
    candidates: list[Path] = []
    if ref.is_file():
        try:
            revision = ref.read_text(encoding="utf-8").strip()
        except OSError:
            revision = ""
        if revision:
            candidates.append(repository / "snapshots" / revision)
    snapshots = repository / "snapshots"
    if snapshots.is_dir():
        candidates.extend(item for item in snapshots.iterdir() if item.is_dir())
    return next((item for item in candidates if all((item / name).is_file() for name in required)), None)


def classify_stt_confidence(
    *, avg_logprob: float | None, no_speech_probability: float | None,
    language_probability: float | None, config: STTConfig,
    mean_word_probability: float | None = None,
    compression_ratio: float | None = None,
    vad_speech_seconds: float | None = None,
    duration_seconds: float | None = None,
    audio_rms: float | None = None,
    silence_ratio: float | None = None,
    clipping_ratio: float | None = None,
) -> tuple[STTConfidence, float | None]:
    evidence = [value for value in (avg_logprob, no_speech_probability, language_probability) if value is not None]
    if not evidence:
        return STTConfidence.MEDIUM, None
    logprob = avg_logprob if avg_logprob is not None else config.medium_logprob
    no_speech = no_speech_probability if no_speech_probability is not None else config.high_no_speech
    language = language_probability if language_probability is not None else config.high_language_probability
    log_score = max(0.0, min(1.0, (logprob + 1.5) / 1.5))
    score = round((log_score * 0.55) + ((1.0 - no_speech) * 0.30) + (language * 0.15), 3)
    vad_ratio = (
        vad_speech_seconds / duration_seconds
        if vad_speech_seconds is not None and duration_seconds and duration_seconds > 0
        else None
    )
    high_quality = all((
        mean_word_probability is None or mean_word_probability >= 0.70,
        compression_ratio is None or compression_ratio <= 2.4,
        vad_ratio is None or vad_ratio >= 0.08,
        audio_rms is None or audio_rms >= 150.0,
        silence_ratio is None or silence_ratio <= 0.85,
        clipping_ratio is None or clipping_ratio <= 0.05,
    ))
    medium_quality = all((
        mean_word_probability is None or mean_word_probability >= 0.45,
        compression_ratio is None or compression_ratio <= 3.0,
        vad_ratio is None or vad_ratio >= 0.03,
        audio_rms is None or audio_rms >= 40.0,
        silence_ratio is None or silence_ratio <= 0.95,
        clipping_ratio is None or clipping_ratio <= 0.20,
    ))
    if (
        logprob >= config.high_logprob
        and no_speech <= config.high_no_speech
        and language >= config.high_language_probability
        and high_quality
    ):
        return STTConfidence.HIGH, score
    if (
        logprob >= config.medium_logprob
        and no_speech <= config.medium_no_speech
        and language >= config.medium_language_probability
        and medium_quality
    ):
        return STTConfidence.MEDIUM, score
    return STTConfidence.LOW, score


class BaseSTTProvider(ABC):
    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def transcribe(
        self,
        path: str | Path,
        language_hint: str | None = None,
        *,
        hotwords: str | None = None,
    ) -> STTResult: ...

    @abstractmethod
    def health(self) -> dict[str, object]: ...

    @abstractmethod
    def supported_languages(self) -> Iterable[str]: ...


class FasterWhisperSTTProvider(BaseSTTProvider):
    """Adaptador opcional. Nunca descarga modelos salvo habilitación explícita."""

    def __init__(self, config: STTConfig | None = None) -> None:
        self.config = config or STTConfig.from_env()
        self._initial_prompt = (
            self.config.initial_prompt
            if str(os.environ.get("ATLAS_STT_INITIAL_PROMPT", "")).strip()
            else ""
        )
        self._model = None
        self._backend = resolve_stt_backend(self.config)
        self._model_source: Path | str | None = None

    def is_available(self) -> bool:
        package = importlib.util.find_spec("faster_whisper") is not None
        model_ready = bool(self.config.allow_model_download or find_local_faster_whisper_model(self.config))
        return package and model_ready

    def health(self) -> dict[str, object]:
        return {
            "available": self.is_available(),
            "provider": "faster-whisper",
            "device": self._backend.device,
            "compute_type": self._backend.compute_type,
            "fallback_reason": self._backend.fallback_reason,
            "model_local": bool(find_local_faster_whisper_model(self.config)),
            "download_allowed": self.config.allow_model_download,
        }

    def supported_languages(self) -> Iterable[str]:
        return ("auto", "es", "ca", "en")

    def transcribe(
        self,
        path: str | Path,
        language_hint: str | None = None,
        *,
        hotwords: str | None = None,
    ) -> STTResult:
        if not self.is_available():
            raise STTError("stt_unavailable", "El reconocimiento de voz local no está disponible.")
        try:
            model = self._get_model()
            segments_iter, info = model.transcribe(
                str(path), language=language_hint or self.config.language_hint,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 350},
                word_timestamps=True,
                beam_size=self.config.beam_size,
                temperature=0.0,
                condition_on_previous_text=False,
                initial_prompt=_repair_utf8_mojibake(self._initial_prompt) or None,
                hotwords=hotwords or self.config.hotwords or None,
            )
            segments = list(segments_iter)
        except (OSError, RuntimeError) as exc:
            if self._backend.device != "cuda":
                raise STTError("stt_runtime_error", "El proveedor STT local no ha podido transcribir el audio.") from exc
            logger.warning("STT CUDA no disponible (%s); se activa fallback CPU.", type(exc).__name__)
            self._backend = STTBackend("cpu", "int8", f"fallo de carga CUDA ({type(exc).__name__})")
            self._model = None
            try:
                model = self._get_model()
                segments_iter, info = model.transcribe(
                    str(path), language=language_hint or self.config.language_hint,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 350},
                    word_timestamps=True,
                    beam_size=self.config.beam_size,
                    temperature=0.0,
                    condition_on_previous_text=False,
                    initial_prompt=_repair_utf8_mojibake(self._initial_prompt) or None,
                    hotwords=hotwords or self.config.hotwords or None,
                )
                segments = list(segments_iter)
            except (OSError, RuntimeError) as cpu_exc:
                raise STTError("stt_runtime_error", "El proveedor STT local no ha podido transcribir el audio.") from cpu_exc
        text = " ".join(str(segment.text).strip() for segment in segments).strip()
        weights = [max(0.001, float(getattr(segment, "end", 0)) - float(getattr(segment, "start", 0))) for segment in segments]
        total_weight = sum(weights)
        avg_logprob = (
            sum(float(getattr(segment, "avg_logprob")) * weight for segment, weight in zip(segments, weights)) / total_weight
            if segments and total_weight else None
        )
        no_speech = max((float(getattr(segment, "no_speech_prob", 0.0)) for segment in segments), default=None)
        language_probability = getattr(info, "language_probability", None)
        word_probabilities = [
            float(getattr(word, "probability"))
            for segment in segments
            for word in (getattr(segment, "words", None) or ())
            if getattr(word, "probability", None) is not None
        ]
        mean_word_probability = (
            sum(word_probabilities) / len(word_probabilities) if word_probabilities else None
        )
        compression_ratio = max(
            (float(getattr(segment, "compression_ratio", 0.0)) for segment in segments),
            default=None,
        )
        vad_speech_seconds = getattr(info, "duration_after_vad", None)
        confidence, score = classify_stt_confidence(
            avg_logprob=avg_logprob,
            no_speech_probability=no_speech,
            language_probability=language_probability,
            config=self.config,
            mean_word_probability=mean_word_probability,
            compression_ratio=compression_ratio,
            vad_speech_seconds=vad_speech_seconds,
            duration_seconds=getattr(info, "duration", None),
        )
        return STTResult(
            text=text,
            language=getattr(info, "language", language_hint),
            duration_seconds=getattr(info, "duration", None),
            confidence=confidence,
            confidence_score=score,
            avg_logprob=avg_logprob,
            no_speech_probability=no_speech,
            language_probability=language_probability,
            mean_word_probability=mean_word_probability,
            min_word_probability=min(word_probabilities, default=None),
            compression_ratio=compression_ratio,
            vad_speech_seconds=vad_speech_seconds,
        )

    def _get_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # type: ignore[import-not-found]

            local = find_local_faster_whisper_model(self.config)
            source: str | Path = local or self.config.model.removeprefix("faster-whisper-")
            self._model_source = source
            self._model = WhisperModel(
                str(source), device=self._backend.device,
                compute_type=self._backend.compute_type,
                local_files_only=not self.config.allow_model_download,
            )
        return self._model


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

    def transcribe(
        self,
        source: str | Path,
        *,
        language_hint: str | None = None,
        context_hint: str = "general",
    ) -> tuple[STTResult, dict[str, float]]:
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
            quality = self._analyze_wav_quality(wav_path)
            timings["audio.convert"] = round((self.clock() - started) * 1000, 3)
            started = self.clock()
            executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="atlas-stt")
            provider_parameters = inspect.signature(self.provider.transcribe).parameters
            hotwords = contextual_hotwords(context_hint, self.config.hotwords)
            if "hotwords" in provider_parameters:
                future = executor.submit(
                    self.provider.transcribe,
                    wav_path,
                    language_hint,
                    hotwords=hotwords,
                )
            else:
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
            has_provider_evidence = any(value is not None for value in (
                result.avg_logprob,
                result.no_speech_probability,
                result.language_probability,
                result.mean_word_probability,
                result.compression_ratio,
                result.vad_speech_seconds,
            ))
            if has_provider_evidence:
                confidence, score = classify_stt_confidence(
                    avg_logprob=result.avg_logprob,
                    no_speech_probability=result.no_speech_probability,
                    language_probability=result.language_probability,
                    config=self.config,
                    mean_word_probability=result.mean_word_probability,
                    compression_ratio=result.compression_ratio,
                    vad_speech_seconds=result.vad_speech_seconds,
                    duration_seconds=result.duration_seconds or duration,
                    audio_rms=quality["audio_rms"],
                    silence_ratio=quality["silence_ratio"],
                    clipping_ratio=quality["clipping_ratio"],
                )
            else:
                confidence, score = result.confidence, result.confidence_score
            return STTResult(
                text=text,
                language=result.language,
                duration_seconds=result.duration_seconds or duration,
                confidence=confidence,
                confidence_score=score,
                avg_logprob=result.avg_logprob,
                no_speech_probability=result.no_speech_probability,
                language_probability=result.language_probability,
                mean_word_probability=result.mean_word_probability,
                min_word_probability=result.min_word_probability,
                compression_ratio=result.compression_ratio,
                vad_speech_seconds=result.vad_speech_seconds,
                audio_rms=quality["audio_rms"],
                audio_peak=quality["audio_peak"],
                silence_ratio=quality["silence_ratio"],
                clipping_ratio=quality["clipping_ratio"],
            ), timings
        finally:
            self._safe_unlink(wav_path)

    @staticmethod
    def _safe_unlink(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    @staticmethod
    def _analyze_wav_quality(path: Path) -> dict[str, float]:
        with wave.open(str(path), "rb") as audio:
            samples = array("h", audio.readframes(audio.getnframes()))
        if not samples:
            return {"audio_rms": 0.0, "audio_peak": 0.0, "silence_ratio": 1.0, "clipping_ratio": 0.0}
        if os.sys.byteorder == "big":
            samples.byteswap()
        squares = sum(int(sample) * int(sample) for sample in samples)
        peak = max(abs(int(sample)) for sample in samples)
        silent = sum(abs(int(sample)) < 320 for sample in samples)
        clipped = sum(abs(int(sample)) >= 32700 for sample in samples)
        count = len(samples)
        return {
            "audio_rms": round((squares / count) ** 0.5, 3),
            "audio_peak": round(peak / 32768.0, 6),
            "silence_ratio": round(silent / count, 6),
            "clipping_ratio": round(clipped / count, 6),
        }
