"""Subsistema de voz del Proyecto Atlas."""

from .catalog.voices import VOICE_CATALOG, get_voice_definition
from .models import (
    AssistantIdentity,
    SynthesisRequest,
    SynthesisResult,
    VoiceDefinition,
    VoiceSelection,
)
from .preferences.voice_preferences import VoicePreferences
from .resolver.voice_resolver import VoiceResolver

__all__ = [
    "AssistantIdentity",
    "SynthesisRequest",
    "SynthesisResult",
    "VoiceDefinition",
    "VoiceSelection",
    "VoicePreferences",
    "VoiceResolver",
    "VOICE_CATALOG",
    "get_voice_definition",
]
