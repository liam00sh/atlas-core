from voice.preferences.storage import VoicePreferenceStore
from voice.preferences.voice_preferences import VoicePreferences


def test_preferences_are_persistent(tmp_path) -> None:
    store = VoicePreferenceStore(tmp_path / "preferences.json")
    preferences = VoicePreferences(
        daxter_voice_id="daxter_santa",
        coco_voice_id="coco_dora",
    )

    store.save("Alex", preferences)
    restored = store.load("Alex")

    assert restored == preferences
