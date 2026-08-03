from voice.catalog.voices import VOICE_CATALOG
from voice.models import AssistantIdentity


def test_catalog_contains_approved_alternative_voices() -> None:
    assert VOICE_CATALOG["daxter_alex"].provider_voice_id == "em_alex"
    assert VOICE_CATALOG["daxter_santa"].provider_voice_id == "em_santa"
    assert VOICE_CATALOG["coco_dora"].provider_voice_id == "ef_dora"


def test_voice_identity_is_kept_separate_from_voice() -> None:
    assert VOICE_CATALOG["daxter_alex"].identity is AssistantIdentity.DAXTER
    assert VOICE_CATALOG["coco_dora"].identity is AssistantIdentity.COCO


def test_alternative_voices_are_marked_as_latam() -> None:
    assert VOICE_CATALOG["daxter_alex"].region == "LATAM"
    assert VOICE_CATALOG["daxter_santa"].region == "LATAM"
    assert VOICE_CATALOG["coco_dora"].region == "LATAM"
