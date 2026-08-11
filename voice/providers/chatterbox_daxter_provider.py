"""Proveedor B1 mediante worker Python 3.11 persistente y completamente local."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
import hashlib
import importlib.util
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
from time import perf_counter
import wave

from voice.models import SynthesisRequest, SynthesisResult
from voice.providers.base_tts_provider import BaseTTSProvider
from voice.config import VOICE_PROVIDER_TIMEOUT_SECONDS


logger = logging.getLogger(__name__)


class ChatterboxDaxterProvider(BaseTTSProvider):
    provider_id = "chatterbox_daxter"

    def __init__(
        self,
        *,
        profile_path: Path | None = None,
        catalog_path: Path | None = None,
        reference_path: Path | None = None,
        worker_command: list[str] | None = None,
        cache_dir: Path | None = None,
        timeout_seconds: float = VOICE_PROVIDER_TIMEOUT_SECONDS,
        postprocess: bool = True,
    ) -> None:
        root = Path(__file__).resolve().parents[2]
        self.profile_path = Path(profile_path or root / "voice_profiles" / "daxter_es_jak2.json")
        self.catalog_path = Path(catalog_path or root / "voice_profiles" / "DAXTER_EMOTION_CATALOG_FINAL.json")
        self.profile = json.loads(self.profile_path.read_text(encoding="utf-8"))
        default_lab = Path.home() / "Emuladores" / "dataset_daxter_completo" / "correctos" / "auditoria_1060"
        lab_root = Path(os.getenv("ATLAS_DAXTER_VOICE_LAB_ROOT", str(default_lab)))
        relative_reference = Path(self.profile["reference_file"])
        self.reference_path = Path(reference_path or lab_root / relative_reference)
        python = os.getenv("ATLAS_CHATTERBOX_PYTHON", "").strip()
        self._explicit_worker = worker_command is not None or bool(python)
        if worker_command is not None:
            self.worker_command = list(worker_command)
        elif python:
            self.worker_command = [python, str(root / "tools" / "chatterbox_worker.py")]
        else:
            self.worker_command = [sys.executable, str(root / "tools" / "chatterbox_worker.py")]
        self.cache_dir = Path(cache_dir or os.getenv("ATLAS_TTS_CACHE_DIR", root / "runtime" / "voice" / "cache"))
        self.timeout_seconds = timeout_seconds
        self.postprocess = bool(postprocess)
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.RLock()

    def is_available(self) -> bool:
        executable = Path(self.worker_command[0])
        return bool(
            (executable.is_file() or shutil.which(self.worker_command[0]))
            and self.profile_path.is_file()
            and self.catalog_path.is_file()
            and self.reference_path.is_file()
            and Path(self.worker_command[-1]).is_file()
            and (self._explicit_worker or importlib.util.find_spec("chatterbox") is not None)
        )

    def supports_voice(self, provider_voice_id: str) -> bool:
        return provider_voice_id == self.profile["profile_id"]

    def _cache_key(self, request: SynthesisRequest) -> str:
        payload = {
            "text": " ".join(request.text.split()),
            "voice": request.voice_profile_id or request.provider_voice_id,
            "emotion": request.emotion,
            "intensity": request.intensity,
            "profile_version": request.profile_version,
            "postprocess_version": "trim-fade-v1" if self.postprocess else "none",
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _valid_wav(path: Path) -> bool:
        try:
            with wave.open(str(path), "rb") as audio:
                return audio.getnchannels() == 1 and audio.getsampwidth() == 2 and audio.getnframes() > 0
        except (OSError, EOFError, wave.Error):
            return False

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        started = perf_counter()
        if not self.is_available():
            return SynthesisResult(False, None, request.voice_id, self.provider_id, "Chatterbox B1 local no está configurado.")
        if not self.supports_voice(request.provider_voice_id):
            return SynthesisResult(False, None, request.voice_id, self.provider_id, "Perfil Daxter no soportado.")
        key = self._cache_key(request)
        cached = self.cache_dir / f"{key}.wav"
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        if self._valid_wav(cached):
            shutil.copy2(cached, request.output_path)
            logger.info("TTS B1 cache hit key=%s", key[:12])
            return SynthesisResult(
                True, request.output_path, request.voice_id, self.provider_id,
                cache_hit=True, latency_ms=round((perf_counter() - started) * 1000, 3),
                emotion=request.emotion, intensity=request.intensity,
            )

        payload = {
            "text": request.text,
            "output_path": str(request.output_path.resolve()),
            "profile_path": str(self.profile_path.resolve()),
            "catalog_path": str(self.catalog_path.resolve()),
            "reference_path": str(self.reference_path.resolve()),
            "emotion": request.emotion,
            "intensity": request.intensity,
            "seed": int(key[:8], 16),
            "postprocess": self.postprocess,
        }
        try:
            response = self._request_worker(payload)
        except (OSError, RuntimeError, TimeoutError) as exc:
            request.output_path.unlink(missing_ok=True)
            logger.warning("TTS B1 failed key=%s error=%s", key[:12], type(exc).__name__)
            return SynthesisResult(False, None, request.voice_id, self.provider_id, str(exc))
        if not response.get("success") or not self._valid_wav(request.output_path):
            request.output_path.unlink(missing_ok=True)
            return SynthesisResult(False, None, request.voice_id, self.provider_id, str(response.get("error") or "Chatterbox no generó un WAV válido."))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.cache_dir / f".{key}.{os.getpid()}.tmp"
        shutil.copy2(request.output_path, temporary)
        temporary.replace(cached)
        logger.info("TTS B1 generated key=%s latency_ms=%.3f", key[:12], (perf_counter() - started) * 1000)
        return SynthesisResult(
            True, request.output_path, request.voice_id, self.provider_id,
            cache_hit=False, latency_ms=round((perf_counter() - started) * 1000, 3),
            emotion=request.emotion, intensity=request.intensity,
        )

    def _request_worker(self, payload: dict) -> dict:
        with self._lock:
            process = self._ensure_worker()
            assert process.stdin is not None and process.stdout is not None
            process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            process.stdin.flush()
            deadline = perf_counter() + self.timeout_seconds
            while True:
                remaining = deadline - perf_counter()
                if remaining <= 0:
                    self.cancel_current()
                    raise TimeoutError("Chatterbox agotó el tiempo de síntesis")
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(process.stdout.readline)
                    try:
                        line = future.result(timeout=remaining)
                    except FutureTimeout as exc:
                        self.cancel_current()
                        raise TimeoutError("Chatterbox agotó el tiempo de síntesis") from exc
                if not line:
                    self.cancel_current()
                    raise RuntimeError("El worker Chatterbox terminó sin respuesta")
                if line.startswith("ATLAS_JSON:"):
                    return json.loads(line.removeprefix("ATLAS_JSON:"))

    def _ensure_worker(self) -> subprocess.Popen[str]:
        if self._process is not None and self._process.poll() is None:
            return self._process
        env = os.environ.copy()
        env["HF_HUB_OFFLINE"] = "1"
        env["TRANSFORMERS_OFFLINE"] = "1"
        env["NO_PROXY"] = "*"
        self._process = subprocess.Popen(
            self.worker_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
            env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        logger.info("TTS B1 worker started offline=true")
        return self._process

    def cancel_current(self) -> None:
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                logger.info("TTS B1 worker cancellation requested")
                self._process.terminate()
                try:
                    self._process.wait(timeout=3.0)
                except subprocess.TimeoutExpired:
                    self._process.kill()
            self._process = None

    def close(self) -> None:
        self.cancel_current()

    def health(self) -> dict[str, object]:
        return {
            "available": self.is_available(),
            "profile": self.profile["profile_id"],
            "profile_version": self.profile["version"],
            "reference_local": self.reference_path.is_file(),
            "offline": True,
            "worker_loaded": self._process is not None and self._process.poll() is None,
        }
