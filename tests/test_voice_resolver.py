from voice.catalog.voices import VOICE_CATALOG
from voice.models import AssistantIdentity
from voice.resolver.voice_resolver import VoiceResolver


def test_daxter_official_falls_back_to_alex() -> None:
    available = {"daxter_alex"}
    resolver = VoiceResolver(
        availability_check=lambda voice: voice.voice_id in available
    )

    result = resolver.resolve(
        identity=AssistantIdentity.DAXTER,
        requested_voice_id="daxter_official",
    )

    assert result.selected_voice_id == "daxter_alex"
    assert result.fallback_used is True


def test_selected_alternative_is_not_reported_as_failure() -> None:
    resolver = VoiceResolver(
        availability_check=lambda voice: voice.voice_id == "daxter_santa"
    )

    result = resolver.resolve(
        identity=AssistantIdentity.DAXTER,
        requested_voice_id="daxter_santa",
    )

    assert result.selected_voice_id == "daxter_santa"
    assert result.fallback_used is False


def test_coco_uses_text_when_no_voice_is_available() -> None:
    resolver = VoiceResolver(availability_check=lambda voice: False)

    result = resolver.resolve(
        identity=AssistantIdentity.COCO,
        requested_voice_id="coco_official",
    )

    assert result.selected_voice_id is None
    assert "usar texto" in result.reason
