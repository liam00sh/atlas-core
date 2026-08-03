"""Proveedores TTS disponibles."""

from .base_tts_provider import BaseTTSProvider
from .kokoro_provider import KokoroProvider

__all__ = ["BaseTTSProvider", "KokoroProvider"]
