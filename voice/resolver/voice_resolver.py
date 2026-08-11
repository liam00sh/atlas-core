"""Resolución de la voz solicitada y su cadena de recuperación."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from voice.catalog.voices import VOICE_CATALOG
from voice.models import AssistantIdentity, VoiceDefinition, VoiceSelection


AvailabilityCheck = Callable[[VoiceDefinition], bool]


DEFAULT_FALLBACKS: dict[AssistantIdentity, tuple[str, ...]] = {
    AssistantIdentity.DAXTER: (
        "daxter_official",
        "daxter_alex",
        "daxter_santa",
    ),
    AssistantIdentity.COCO: (
        "coco_official",
        "coco_dora",
    ),
}


class VoiceResolver:
    """Elige una voz compatible, disponible y autorizada."""

    def __init__(
        self,
        catalog: dict[str, VoiceDefinition] | None = None,
        availability_check: AvailabilityCheck | None = None,
    ) -> None:
        self._catalog = catalog or VOICE_CATALOG
        self._availability_check = availability_check or (
            lambda voice: voice.enabled
        )

    def resolve(
        self,
        *,
        identity: AssistantIdentity | str,
        requested_voice_id: str,
        fallback_enabled: bool = True,
    ) -> VoiceSelection:
        resolved_identity = AssistantIdentity(identity)
        candidates = self._candidate_chain(
            resolved_identity,
            requested_voice_id,
            fallback_enabled,
        )

        for candidate_id in candidates:
            voice = self._catalog.get(candidate_id)
            if voice is None or voice.identity is not resolved_identity:
                continue
            if self._availability_check(voice):
                fallback_used = candidate_id != requested_voice_id
                return VoiceSelection(
                    requested_voice_id=requested_voice_id,
                    selected_voice_id=candidate_id,
                    fallback_used=fallback_used,
                    reason=(
                        "voz solicitada disponible"
                        if not fallback_used
                        else "fallback compatible disponible"
                    ),
                )

        return VoiceSelection(
            requested_voice_id=requested_voice_id,
            selected_voice_id=None,
            fallback_used=False,
            reason="ninguna voz compatible está disponible; usar texto",
        )

    @staticmethod
    def _deduplicate(values: Iterable[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(values))

    def _candidate_chain(
        self,
        identity: AssistantIdentity,
        requested_voice_id: str,
        fallback_enabled: bool,
    ) -> tuple[str, ...]:
        if not fallback_enabled:
            return (requested_voice_id,)

        return self._deduplicate(
            (requested_voice_id, *DEFAULT_FALLBACKS[identity])
        )

    def candidates(
        self,
        *,
        identity: AssistantIdentity | str,
        requested_voice_id: str,
        fallback_enabled: bool = True,
    ) -> tuple[str, ...]:
        return self._candidate_chain(
            AssistantIdentity(identity), requested_voice_id, fallback_enabled
        )
