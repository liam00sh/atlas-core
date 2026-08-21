"""Proveedor Chatterbox local persistente para la voz Daxter validada."""

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

from tools.chatterbox_es_es_runtime import resolve_es_es_model_dir


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
        postprocess_options: dict[str, object] | None = None,
        candidate: str | None = None,
        source_path: Path | None = None,
        model_dir: Path | None = None,
        generation_policy: dict[str, object] | None = None,
        diagnostic_raw_dir: Path | None = None,
        cache_enabled: bool = True,
    ) -> None:
        root = Path(__file__).resolve().parents[2]
        self.profile_path = Path(profile_path or root / "voice_profiles" / "daxter_es_jak2.json")
        self.catalog_path = Path(catalog_path or root / "voice_profiles" / "DAXTER_EMOTION_CATALOG_FINAL.json")
        self.profile = json.loads(self.profile_path.read_text(encoding="utf-8"))
        default_lab = Path.home() / "Emuladores" / "dataset_daxter_completo" / "correctos" / "auditoria_1060"
        lab_root = Path(os.getenv("ATLAS_DAXTER_VOICE_LAB_ROOT", str(default_lab)))
        relative_reference = Path(self.profile["reference_file"])
        self.reference_path = Path(reference_path or lab_root / relative_reference)
        candidate = (candidate or os.getenv("ATLAS_CHATTERBOX_CANDIDATE", "v2")).strip().casefold()
        if candidate not in {"v2", "es_es"}:
            raise ValueError("La variante Chatterbox debe ser 'v2' o 'es_es'.")
        self.candidate = candidate
        configured_source = source_path or os.getenv("ATLAS_CHATTERBOX_SOURCE", "").strip()
        configured_model = model_dir or os.getenv("ATLAS_CHATTERBOX_MODEL_DIR", "").strip()
        self.source_path = Path(configured_source) if configured_source else None
        self.source_module = (
            self.source_path / "chatterbox" / "src" / "chatterbox" / "tts.py"
            if self.source_path is not None else None
        )
        self.model_dir = Path(configured_model) if configured_model else None
        self.model_route = (
            resolve_es_es_model_dir(self.model_dir)
            if self.candidate == "es_es" and self.model_dir is not None else None
        )
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
        accepted_boundary = dict(self.profile.get("final_boundary_policy") or {})
        accepted_postprocess = dict(accepted_boundary.get("postprocess") or {})
        accepted_generation = dict(accepted_boundary.get("generation_policy") or {})
        self.postprocess_options = dict(postprocess_options or accepted_postprocess or {
            "trim_start": False,
            "trim_end": True,
            "threshold": 0.0005,
            "end_padding_ms": 200,
            "ensure_end_padding": True,
            "pre_roll_ms": 40,
            "fade_ms": 5,
        })
        self.generation_policy = dict(generation_policy or accepted_generation or {
            "floor": 120, "ceiling": 260, "tokens_per_char": 2.0,
            "punctuation_bonus": 4, "digit_bonus": 2,
        })
        self.diagnostic_raw_dir = Path(diagnostic_raw_dir) if diagnostic_raw_dir else None
        self.cache_enabled = bool(cache_enabled)
        self._process: subprocess.Popen[str] | None = None
        self._lock = threading.RLock()
        self.last_worker_diagnostics: dict[str, object] = {}

    def is_available(self) -> bool:
        executable = Path(self.worker_command[0])
        return bool(
            (executable.is_file() or shutil.which(self.worker_command[0]))
            and self.profile_path.is_file()
            and self.catalog_path.is_file()
            and self.reference_path.is_file()
            and Path(self.worker_command[-1]).is_file()
            and (self._explicit_worker or importlib.util.find_spec("chatterbox") is not None)
            and (self.candidate != "es_es" or bool(
                self.source_module and self.source_module.is_file()
                and self.model_route and self.model_route.ready
            ))
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
            "synthesis_version": "complete-boundaries-v1",
            "postprocess_version": self.postprocess_options if self.postprocess else "none",
            "generation_policy": self.generation_policy,
            "candidate": self.candidate,
            "model_revision": self.model_dir.name if self.model_dir else "bundled",
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _generation_seed(request: SynthesisRequest) -> int:
        payload = {
            "text": " ".join(request.text.split()),
            "voice": request.voice_profile_id or request.provider_voice_id,
            "emotion": request.emotion,
            "intensity": request.intensity,
            "profile_version": request.profile_version,
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return int(hashlib.sha256(encoded).hexdigest()[:8], 16)

    @staticmethod
    def _wav_metrics(path: Path) -> tuple[int, float]:
        with wave.open(str(path), "rb") as audio:
            samples = audio.getnframes() * audio.getnchannels()
            duration_ms = audio.getnframes() / float(audio.getframerate()) * 1000
        return samples, round(duration_ms, 3)

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
            return SynthesisResult(False, None, request.voice_id, self.provider_id, "Chatterbox local no está configurado.")
        if not self.supports_voice(request.provider_voice_id):
            return SynthesisResult(False, None, request.voice_id, self.provider_id, "Perfil Daxter no soportado.")
        key = self._cache_key(request)
        cached = self.cache_dir / f"{key}.wav"
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        cache_metadata = cached.with_suffix(".json")
        if self.cache_enabled and self._valid_wav(cached):
            shutil.copy2(cached, request.output_path)
            samples, duration_ms = self._wav_metrics(request.output_path)
            logger.info("TTS Chatterbox cache hit candidate=%s key=%s", self.candidate, key[:12])
            metadata = {}
            try:
                metadata = json.loads(cache_metadata.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                pass
            return SynthesisResult(
                True, request.output_path, request.voice_id, self.provider_id,
                cache_hit=True, latency_ms=round((perf_counter() - started) * 1000, 3),
                emotion=request.emotion, intensity=request.intensity,
                chars_sent_to_tts=len(request.text), chars_synthesized=len(request.text),
                synthesized_samples=samples, wav_duration_ms=duration_ms,
                generation_tokens_budgeted=int(metadata.get("generation_tokens_budgeted", 0)),
                generation_tokens_used=int(metadata.get("generation_tokens_used", 0)),
                reached_generation_limit=bool(metadata.get("reached_generation_limit", False)),
                generation_units=tuple(metadata.get("generation_units") or ()),
            )

        payload = {
            "text": request.text,
            "output_path": str(request.output_path.resolve()),
            "profile_path": str(self.profile_path.resolve()),
            "catalog_path": str(self.catalog_path.resolve()),
            "reference_path": str(self.reference_path.resolve()),
            "emotion": request.emotion,
            "intensity": request.intensity,
            "seed": self._generation_seed(request),
            "postprocess": self.postprocess,
            "postprocess_options": self.postprocess_options,
            "generation_policy": self.generation_policy,
        }
        if self.diagnostic_raw_dir is not None:
            payload["diagnostic_raw_output_path"] = str(
                (self.diagnostic_raw_dir / request.output_path.name).resolve()
            )
        try:
            response = self._request_worker(payload)
        except (OSError, RuntimeError, TimeoutError) as exc:
            request.output_path.unlink(missing_ok=True)
            logger.warning("TTS Chatterbox failed candidate=%s key=%s error=%s", self.candidate, key[:12], type(exc).__name__)
            return SynthesisResult(False, None, request.voice_id, self.provider_id, str(exc))
        self.last_worker_diagnostics = dict(response.get("runtime") or {})
        if not response.get("success") or not self._valid_wav(request.output_path):
            request.output_path.unlink(missing_ok=True)
            return SynthesisResult(False, None, request.voice_id, self.provider_id, str(response.get("error") or "Chatterbox no generó un WAV válido."))
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            temporary = self.cache_dir / f".{key}.{os.getpid()}.tmp"
            shutil.copy2(request.output_path, temporary)
            temporary.replace(cached)
            cache_metadata.write_text(json.dumps({
                "generation_tokens_budgeted": response.get("generation_tokens_budgeted", 0),
                "generation_tokens_used": response.get("generation_tokens_used", 0),
                "reached_generation_limit": response.get("reached_generation_limit", False),
                "generation_units": response.get("generation_units") or [],
            }, ensure_ascii=False), encoding="utf-8")
        samples, duration_ms = self._wav_metrics(request.output_path)
        logger.info("TTS Chatterbox generated candidate=%s key=%s latency_ms=%.3f", self.candidate, key[:12], (perf_counter() - started) * 1000)
        return SynthesisResult(
            True, request.output_path, request.voice_id, self.provider_id,
            cache_hit=False, latency_ms=round((perf_counter() - started) * 1000, 3),
            emotion=request.emotion, intensity=request.intensity,
            chars_sent_to_tts=len(request.text),
            chars_synthesized=int(response.get("chars_synthesized", len(request.text))),
            synthesized_samples=int(response.get("synthesized_samples", samples)),
            wav_duration_ms=float(response.get("wav_duration_ms", duration_ms)),
            generation_tokens_budgeted=int(response.get("generation_tokens_budgeted", 0)),
            generation_tokens_used=int(response.get("generation_tokens_used", 0)),
            reached_generation_limit=bool(response.get("reached_generation_limit", False)),
            generation_units=tuple(response.get("generation_units") or ()),
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
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["ATLAS_CHATTERBOX_CANDIDATE"] = self.candidate
        if self.source_path is not None:
            env["ATLAS_CHATTERBOX_SOURCE"] = str(self.source_path.resolve())
        if self.model_dir is not None:
            effective = self.model_route.effective if self.model_route is not None else self.model_dir.resolve()
            env["ATLAS_CHATTERBOX_MODEL_DIR"] = str(effective)
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
        logger.info("TTS Chatterbox worker started candidate=%s offline=true", self.candidate)
        return self._process

    def cancel_current(self) -> None:
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                logger.info("TTS Chatterbox worker cancellation requested")
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
            "candidate": self.candidate,
            "reference_local": self.reference_path.is_file(),
            "offline": True,
            "worker_loaded": self._process is not None and self._process.poll() is None,
            "model_requested": str(self.model_route.requested) if self.model_route else None,
            "model_effective": str(self.model_route.effective) if self.model_route else None,
            "missing_model_files": list(self.model_route.missing_effective) if self.model_route else [],
            "source_module": str(self.source_module) if self.source_module else None,
        }
