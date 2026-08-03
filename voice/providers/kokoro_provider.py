"""Adaptador desacoplado para un proceso externo de Kokoro."""

from __future__ import annotations

import json
import shlex
import subprocess
from pathlib import Path

from voice.config import (
    KOKORO_COMMAND,
    VOICE_PROVIDER_TIMEOUT_SECONDS,
)
from voice.models import SynthesisRequest, SynthesisResult
from voice.providers.base_tts_provider import BaseTTSProvider


class KokoroProvider(BaseTTSProvider):
    """Invoca un puente externo de Kokoro mediante entrada/salida JSON.

    El puente se ejecuta en un entorno Python 3.12 separado. Atlas Core no
    importa el paquete ``kokoro`` ni depende directamente de él.
    """

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

        request.output_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "text": request.text,
            "voice": request.voice_id,
            "output_path": str(request.output_path),
            "speed": request.speed,
            "volume": request.volume,
        }

        try:
            completed = subprocess.run(
                shlex.split(self._command, posix=False),
                input=json.dumps(payload, ensure_ascii=False),
                text=True,
                capture_output=True,
                timeout=self._timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
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
