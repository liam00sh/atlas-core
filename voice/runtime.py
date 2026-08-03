"""Construcción opcional del servicio de voz."""

from __future__ import annotations

from voice.config import VOICE_ENABLED
from voice.service import VoiceService


def build_voice_service() -> VoiceService | None:
    """Devuelve el servicio solo cuando está habilitado y disponible."""

    if not VOICE_ENABLED:
        return None

    service = VoiceService()
    if not service.is_available():
        return None

    return service
