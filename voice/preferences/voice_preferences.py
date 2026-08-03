"""Preferencias persistibles de voz para cada usuario."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from voice.models import AssistantIdentity


@dataclass(slots=True)
class VoicePreferences:
    """Preferencias de voz independientes de la personalidad."""

    daxter_voice_id: str = "daxter_official"
    coco_voice_id: str = "coco_official"
    fallback_enabled: bool = True
    notify_voice_fallback: bool = True
    speech_rate: float = 1.0
    speech_volume: float = 1.0

    def preferred_voice_for(
        self,
        identity: AssistantIdentity | str,
    ) -> str:
        resolved = AssistantIdentity(identity)
        if resolved is AssistantIdentity.DAXTER:
            return self.daxter_voice_id
        return self.coco_voice_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "daxter_voice_id": self.daxter_voice_id,
            "coco_voice_id": self.coco_voice_id,
            "fallback_enabled": self.fallback_enabled,
            "notify_voice_fallback": self.notify_voice_fallback,
            "speech_rate": self.speech_rate,
            "speech_volume": self.speech_volume,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "VoicePreferences":
        values = data or {}
        return cls(
            daxter_voice_id=str(
                values.get("daxter_voice_id", "daxter_official")
            ),
            coco_voice_id=str(
                values.get("coco_voice_id", "coco_official")
            ),
            fallback_enabled=bool(values.get("fallback_enabled", True)),
            notify_voice_fallback=bool(
                values.get("notify_voice_fallback", True)
            ),
            speech_rate=float(values.get("speech_rate", 1.0)),
            speech_volume=float(values.get("speech_volume", 1.0)),
        )
