"""Servicio de alto nivel para resolver, sintetizar y reproducir voz."""

from __future__ import annotations

import re
import time
from pathlib import Path

from voice.catalog.voices import VOICE_CATALOG
from voice.config import (
    COCO_PREFERRED_VOICE,
    DAXTER_PREFERRED_VOICE,
    VOICE_OUTPUT_DIR,
)
from voice.models import (
    AssistantIdentity,
    SynthesisRequest,
    SynthesisResult,
)
from voice.player import WavePlayer
from voice.providers.kokoro_provider import KokoroProvider
from voice.resolver.voice_resolver import VoiceResolver


class VoiceService:
    """Orquesta selección, síntesis y reproducción."""

    def __init__(
        self,
        *,
        provider: KokoroProvider | None = None,
        player: WavePlayer | None = None,
        output_dir: Path | None = None,
    ) -> None:
        self.provider = provider or KokoroProvider()
        self.player = player or WavePlayer()
        self.output_dir = output_dir or VOICE_OUTPUT_DIR
        self.resolver = VoiceResolver(
            availability_check=self._is_voice_available,
        )

    def is_available(self) -> bool:
        return self.provider.is_available() and self.player.is_available()

    def preferred_voice(
        self,
        identity: AssistantIdentity,
    ) -> str:
        if identity is AssistantIdentity.COCO:
            return COCO_PREFERRED_VOICE
        return DAXTER_PREFERRED_VOICE

    def speak(
        self,
        text: str,
        *,
        identity: AssistantIdentity | str,
        requested_voice_id: str | None = None,
        speed: float = 1.0,
        volume: float = 1.0,
    ) -> SynthesisResult:
        resolved_identity = AssistantIdentity(identity)
        clean_text = self.clean_console_text(text)

        if not clean_text:
            return SynthesisResult(
                success=False,
                output_path=None,
                voice_id=requested_voice_id or "",
                provider_id="none",
                error="No hay texto reproducible.",
            )

        requested = requested_voice_id or self.preferred_voice(
            resolved_identity
        )
        selection = self.resolver.resolve(
            identity=resolved_identity,
            requested_voice_id=requested,
            fallback_enabled=True,
        )

        if selection.selected_voice_id is None:
            return SynthesisResult(
                success=False,
                output_path=None,
                voice_id=requested,
                provider_id="none",
                error=selection.reason,
            )

        definition = VOICE_CATALOG[selection.selected_voice_id]
        output_path = self._build_output_path(definition.voice_id)

        result = self.provider.synthesize(
            SynthesisRequest(
                text=clean_text,
                voice_id=definition.voice_id,
                provider_voice_id=definition.provider_voice_id,
                output_path=output_path,
                speed=speed,
                volume=volume,
            )
        )

        if result.success and result.output_path is not None:
            if not self.player.play(result.output_path):
                return SynthesisResult(
                    success=False,
                    output_path=result.output_path,
                    voice_id=result.voice_id,
                    provider_id=result.provider_id,
                    error="No se pudo reproducir el WAV.",
                )

        return result

    def _is_voice_available(self, definition) -> bool:
        if not definition.enabled:
            return False
        if definition.provider_id != self.provider.provider_id:
            return False
        return (
            self.provider.is_available()
            and self.provider.supports_voice(
                definition.provider_voice_id
            )
        )

    def _build_output_path(self, voice_id: str) -> Path:
        safe_voice = re.sub(r"[^a-z0-9_-]+", "_", voice_id.casefold())
        timestamp = time.time_ns()
        return self.output_dir / f"{safe_voice}_{timestamp}.wav"

    @staticmethod
    def clean_console_text(text: str) -> str:
        """Quita ruido visual que no debe pronunciarse."""

        lines: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(("INFO:", "DEBUG:", "WARNING:", "ERROR:")):
                continue
            if set(line) <= {"=", "-", "_", "*"}:
                continue
            lines.append(line)

        combined = " ".join(lines)
        combined = re.sub(r"\s+", " ", combined).strip()
        return combined
