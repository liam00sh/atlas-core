from voice.models import AssistantIdentity
from voice.preferences.voice_preferences import VoicePreferences


def test_default_preferences_use_official_voices() -> None:
    preferences = VoicePreferences()

    assert (
        preferences.preferred_voice_for(AssistantIdentity.DAXTER)
        == "daxter_official"
    )
    assert (
        preferences.preferred_voice_for(AssistantIdentity.COCO)
        == "coco_official"
    )


def test_preferences_round_trip() -> None:
    original = VoicePreferences(
        daxter_voice_id="daxter_alex",
        coco_voice_id="coco_dora",
        speech_rate=1.05,
    )

    restored = VoicePreferences.from_dict(original.to_dict())

    assert restored == original
