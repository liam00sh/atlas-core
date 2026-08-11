"""Catálogo inicial de voces de Atlas."""

from __future__ import annotations

from voice.exceptions import VoiceNotFoundError
from voice.models import AssistantIdentity, VoiceDefinition


VOICE_CATALOG: dict[str, VoiceDefinition] = {
    "daxter_official": VoiceDefinition(
        voice_id="daxter_official",
        display_name="Daxter oficial",
        identity=AssistantIdentity.DAXTER,
        provider_id="chatterbox_daxter",
        provider_voice_id="daxter_es_jak2",
        language="es",
        region="ES",
        is_official=True,
        enabled=True,
        metadata={"status": "human_validated_b1", "profile": "voice_profiles/daxter_es_jak2.json"},
    ),
    "daxter_alex": VoiceDefinition(
        voice_id="daxter_alex",
        display_name="Daxter alternativa Alex",
        identity=AssistantIdentity.DAXTER,
        provider_id="kokoro",
        provider_voice_id="em_alex",
        language="es",
        region="LATAM",
        is_official=False,
    ),
    "daxter_santa": VoiceDefinition(
        voice_id="daxter_santa",
        display_name="Daxter alternativa Santa",
        identity=AssistantIdentity.DAXTER,
        provider_id="kokoro",
        provider_voice_id="em_santa",
        language="es",
        region="LATAM",
        is_official=False,
    ),
    "coco_official": VoiceDefinition(
        voice_id="coco_official",
        display_name="Coco oficial",
        identity=AssistantIdentity.COCO,
        provider_id="coco_official",
        provider_voice_id="coco_official",
        language="es",
        region="ES",
        is_official=True,
        enabled=False,
        metadata={"status": "pendiente"},
    ),
    "coco_dora": VoiceDefinition(
        voice_id="coco_dora",
        display_name="Coco alternativa Dora",
        identity=AssistantIdentity.COCO,
        provider_id="kokoro",
        provider_voice_id="ef_dora",
        language="es",
        region="LATAM",
        is_official=False,
    ),
}


def get_voice_definition(voice_id: str) -> VoiceDefinition:
    """Devuelve una voz o lanza una excepción clara."""

    try:
        return VOICE_CATALOG[voice_id]
    except KeyError as exc:
        raise VoiceNotFoundError(
            f"La voz '{voice_id}' no existe en el catálogo."
        ) from exc
