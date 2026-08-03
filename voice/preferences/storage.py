"""Persistencia de preferencias de voz por usuario."""

from __future__ import annotations

import json
from pathlib import Path

from voice.preferences.voice_preferences import VoicePreferences


class VoicePreferenceStore:
    """Almacén JSON independiente para preferencias de voz."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self, user_id: str) -> VoicePreferences:
        data = self._read_all()
        return VoicePreferences.from_dict(
            data.get(user_id.casefold())
        )

    def save(
        self,
        user_id: str,
        preferences: VoicePreferences,
    ) -> None:
        data = self._read_all()
        data[user_id.casefold()] = preferences.to_dict()

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def _read_all(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}

        raw = self.path.read_text(encoding="utf-8").strip()
        if not raw:
            return {}

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}

        if not isinstance(data, dict):
            return {}

        return data
