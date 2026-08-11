"""Proveedores TTS disponibles."""

from .base_tts_provider import BaseTTSProvider
from .chatterbox_daxter_provider import ChatterboxDaxterProvider
from .kokoro_provider import KokoroProvider

__all__ = ["BaseTTSProvider", "ChatterboxDaxterProvider", "KokoroProvider"]
