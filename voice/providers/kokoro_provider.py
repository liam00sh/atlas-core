"""Adaptador desacoplado para un proceso externo de Kokoro."""

from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import threading
import time
from pathlib import Path

from voice.config import KOKORO_COMMAND, VOICE_PROVIDER_TIMEOUT_SECONDS
from voice.models import SynthesisRequest, SynthesisResult
from voice.providers.base_tts_provider import BaseTTSProvider

def _split_windows_command(command: str) -> list[str]:
    """
    Divide un comando de Windows conservando correctamente las rutas
    que contienen espacios, pero elimina las comillas exteriores.
    """
    matches = re.findall(
        r'"([^"]*)"|(\S+)',
        command,
    )

    return [
        quoted or unquoted
        for quoted, unquoted in matches
    ]

class KokoroProvider(BaseTTSProvider):
    """Invoca un puente externo de Kokoro mediante entrada/salida JSON."""

    provider_id = "kokoro"

    def __init__(
        self,
        command: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._command = (command or KOKORO_COMMAND).strip()
        self._timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else VOICE_PROVIDER_TIMEOUT_SECONDS
        )
        self._process: subprocess.Popen[str] | None = None
        self._responses: queue.Queue[str] = queue.Queue()
        self._lock = threading.RLock()

    def is_available(self) -> bool:
        return bool(self._command)

    def supports_voice(self, provider_voice_id: str) -> bool:
        return provider_voice_id in {"em_alex", "em_santa", "ef_dora"}

    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        if not self.is_available():
            return SynthesisResult(
                success=False,
                output_path=None,
                voice_id=request.voice_id,
                provider_id=self.provider_id,
                error="ATLAS_KOKORO_COMMAND no está configurado.",
            )

        if not self.supports_voice(request.provider_voice_id):
            return SynthesisResult(
                success=False,
                output_path=None,
                voice_id=request.voice_id,
                provider_id=self.provider_id,
                error=(
                    "Kokoro no admite la voz "
                    f"'{request.provider_voice_id}'."
                ),
            )

        request.output_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "text": request.text,
            "voice": request.provider_voice_id,
            "output_path": str(request.output_path),
            "request_id": str(request.output_path),
            "speed": request.speed,
            "volume": request.volume,
        }

        if self._uses_persistent_bridge():
            persistent = self._synthesize_persistent(request, payload)
            if persistent is not None:
                return persistent

        try:
            completed = subprocess.run(
                _split_windows_command(self._command),
                input=json.dumps(payload, ensure_ascii=False),
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=self._timeout_seconds,
                check=False,
            )
        except (OSError, UnicodeError, subprocess.SubprocessError) as exc:
            return SynthesisResult(
                success=False,
                output_path=None,
                voice_id=request.voice_id,
                provider_id=self.provider_id,
                error=str(exc),
            )

        if completed.returncode != 0:
            error = completed.stderr.strip() or completed.stdout.strip()
            return SynthesisResult(
                success=False,
                output_path=None,
                voice_id=request.voice_id,
                provider_id=self.provider_id,
                error=error or "El proceso Kokoro terminó con error.",
            )

        output_path = Path(request.output_path)
        if not output_path.exists() or output_path.stat().st_size == 0:
            return SynthesisResult(
                success=False,
                output_path=None,
                voice_id=request.voice_id,
                provider_id=self.provider_id,
                error="Kokoro no generó un archivo de audio válido.",
            )

        return SynthesisResult(
            success=True,
            output_path=output_path,
            voice_id=request.voice_id,
            provider_id=self.provider_id,
        )

    def warm_up_async(self) -> None:
        """Carga el puente oficial en segundo plano sin bloquear el arranque."""

        if not self._uses_persistent_bridge():
            return
        threading.Thread(
            target=self._ensure_process,
            name="atlas-kokoro-warmup",
            daemon=True,
        ).start()

    def close(self) -> None:
        with self._lock:
            process, self._process = self._process, None
            if process is not None and process.poll() is None:
                process.terminate()

    def _uses_persistent_bridge(self) -> bool:
        enabled = os.getenv("ATLAS_KOKORO_PERSISTENT", "false").strip().casefold()
        return enabled not in {"0", "false", "no", "off"} and any(
            Path(part).name.casefold() == "kokoro_bridge.py"
            for part in _split_windows_command(self._command)
        )

    def _ensure_process(self) -> subprocess.Popen[str] | None:
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                return self._process
            try:
                process = subprocess.Popen(
                    [*_split_windows_command(self._command), "--server"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except (OSError, ValueError):
                return None
            self._process = process

            def read_responses() -> None:
                assert process.stdout is not None
                for line in process.stdout:
                    self._responses.put(line)

            threading.Thread(
                target=read_responses,
                name="atlas-kokoro-responses",
                daemon=True,
            ).start()
            return process

    def _synthesize_persistent(
        self,
        request: SynthesisRequest,
        payload: dict[str, object],
    ) -> SynthesisResult | None:
        with self._lock:
            process = self._ensure_process()
            if process is None or process.stdin is None:
                return None
            try:
                process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
                process.stdin.flush()
                deadline = time.monotonic() + self._timeout_seconds
                response = None
                while time.monotonic() < deadline:
                    remaining = max(0.1, deadline - time.monotonic())
                    candidate = json.loads(self._responses.get(timeout=remaining))
                    if candidate.get("request_id") == payload["request_id"]:
                        response = candidate
                        break
                if response is None:
                    raise queue.Empty
            except (BrokenPipeError, OSError, queue.Empty, json.JSONDecodeError):
                self.close()
                return None
        if not response.get("success"):
            return SynthesisResult(
                False, None, request.voice_id, self.provider_id,
                str(response.get("error") or "Kokoro terminó con error."),
            )
        output_path = Path(request.output_path)
        if not output_path.exists() or output_path.stat().st_size == 0:
            return SynthesisResult(
                False, None, request.voice_id, self.provider_id,
                "Kokoro no generó un archivo de audio válido.",
            )
        return SynthesisResult(
            True, output_path, request.voice_id, self.provider_id,
        )
