"""Gestión de preferencias de voz del usuario activo."""

from __future__ import annotations

from pathlib import Path

from voice.models import AssistantIdentity
from voice.preferences.storage import VoicePreferenceStore
from voice.preferences.voice_preferences import VoicePreferences


class VoicePreferenceManager:
    """Carga, valida y guarda preferencias de voz por usuario."""

    def __init__(
        self,
        *,
        storage_path: Path,
        user_provider,
    ) -> None:
        self.store = VoicePreferenceStore(storage_path)
        self.user_provider = user_provider

    def get_current(self) -> VoicePreferences:
        return self.store.load(self.user_provider())

    def set_voice(
        self,
        *,
        identity: AssistantIdentity | str,
        voice_id: str,
    ) -> VoicePreferences:
        resolved = AssistantIdentity(identity)
        preferences = self.get_current()

        if resolved is AssistantIdentity.DAXTER:
            preferences.daxter_voice_id = voice_id
        else:
            preferences.coco_voice_id = voice_id

        self.store.save(
            self.user_provider(),
            preferences,
        )
        return preferences

    def set_fallback_enabled(
        self,
        enabled: bool,
    ) -> VoicePreferences:
        preferences = self.get_current()
        preferences.fallback_enabled = enabled
        self.store.save(
            self.user_provider(),
            preferences,
        )
        return preferences
