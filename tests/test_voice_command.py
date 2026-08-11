import pytest

from commands import voice as voice_command
from voice.preferences.manager import VoicePreferenceManager


@pytest.fixture
def isolated_manager(tmp_path, monkeypatch):
    manager = VoicePreferenceManager(
        storage_path=tmp_path / "preferences.json",
        user_provider=lambda: "Alex",
    )
    monkeypatch.setattr(
        voice_command,
        "_manager",
        lambda: manager,
    )
    return manager


def test_command_changes_daxter_voice(
    isolated_manager,
) -> None:
    voice_command.execute("daxter alex")

    assert (
        isolated_manager.get_current().daxter_voice_id
        == "daxter_alex"
    )


def test_command_changes_coco_voice(
    isolated_manager,
) -> None:
    voice_command.execute("coco dora")

    assert (
        isolated_manager.get_current().coco_voice_id
        == "coco_dora"
    )


def test_command_changes_rate_and_volume(
    isolated_manager,
) -> None:
    voice_command.execute("velocidad 1.10")
    voice_command.execute("volumen 0.80")

    preferences = isolated_manager.get_current()
    assert preferences.speech_rate == 1.10
    assert preferences.speech_volume == 0.80


def test_manager_rejects_unsafe_rate(
    isolated_manager,
) -> None:
    with pytest.raises(ValueError):
        isolated_manager.set_speech_rate(2.0)


def test_manager_rejects_unsafe_volume(
    isolated_manager,
) -> None:
    with pytest.raises(ValueError):
        isolated_manager.set_speech_volume(1.5)
