from telegram_interface.response_modes import (
    TelegramResponseMode,
    detect_response_mode_directive,
    resolve_delivery_mode,
)
from telegram_interface.voice_delivery import TelegramVoiceResult


def test_voice_is_synonym_for_audio() -> None:
    assert (
        detect_response_mode_directive(
            "Respóndeme solo por voz"
        )
        is TelegramResponseMode.AUDIO_ONLY
    )


def test_audio_only_prefers_audio_when_available() -> None:
    assert (
        resolve_delivery_mode(
            configured_mode="audio_only",
            incoming_media_type=None,
            audio_available=True,
        )
        == "audio"
    )


def test_automatic_audio_input_prefers_audio() -> None:
    assert (
        resolve_delivery_mode(
            configured_mode="automatic",
            incoming_media_type="voice",
            audio_available=True,
        )
        == "audio"
    )


def test_voice_result_can_represent_failure() -> None:
    result = TelegramVoiceResult(
        success=False,
        ogg_path=None,
        error="fallo",
    )
    assert result.success is False
    assert result.ogg_path is None
