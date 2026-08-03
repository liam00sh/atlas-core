"""Gestión de preferencias de voz del usuario activo."""

from __future__ import annotations

from pathlib import Path

from voice.models import AssistantIdentity
from voice.preferences.storage import VoicePreferenceStore
from voice.preferences.voice_preferences import VoicePreferences


class VoicePreferenceManager:
    """Carga, valida y guarda preferencias de voz por usuario."""

    MIN_SPEECH_RATE = 0.75
    MAX_SPEECH_RATE = 1.35
    MIN_SPEECH_VOLUME = 0.10
    MAX_SPEECH_VOLUME = 1.00

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

        self._save(preferences)
        return preferences

    def set_fallback_enabled(
        self,
        enabled: bool,
    ) -> VoicePreferences:
        preferences = self.get_current()
        preferences.fallback_enabled = enabled
        self._save(preferences)
        return preferences

    def set_speech_rate(
        self,
        value: float,
    ) -> VoicePreferences:
        value = float(value)
        if not self.MIN_SPEECH_RATE <= value <= self.MAX_SPEECH_RATE:
            raise ValueError(
                "La velocidad debe estar entre "
                f"{self.MIN_SPEECH_RATE:.2f} y "
                f"{self.MAX_SPEECH_RATE:.2f}."
            )

        preferences = self.get_current()
        preferences.speech_rate = value
        self._save(preferences)
        return preferences

    def set_speech_volume(
        self,
        value: float,
    ) -> VoicePreferences:
        value = float(value)
        if not self.MIN_SPEECH_VOLUME <= value <= self.MAX_SPEECH_VOLUME:
            raise ValueError(
                "El volumen debe estar entre "
                f"{self.MIN_SPEECH_VOLUME:.2f} y "
                f"{self.MAX_SPEECH_VOLUME:.2f}."
            )

        preferences = self.get_current()
        preferences.speech_volume = value
        self._save(preferences)
        return preferences

    def _save(
        self,
        preferences: VoicePreferences,
    ) -> None:
        self.store.save(
            self.user_provider(),
            preferences,
        )
