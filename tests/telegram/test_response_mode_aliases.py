from telegram_interface.response_modes import (
    TelegramResponseMode,
    detect_response_mode_directive,
)


def test_short_mode_text_is_detected() -> None:
    assert detect_response_mode_directive("Modo texto") is TelegramResponseMode.TEXT_ONLY


def test_short_mode_voice_is_detected() -> None:
    assert detect_response_mode_directive("Modo voz") is TelegramResponseMode.AUDIO_ONLY


def test_short_mode_audio_is_detected() -> None:
    assert detect_response_mode_directive("Modo audio") is TelegramResponseMode.AUDIO_ONLY


def test_automatic_phrase_is_detected() -> None:
    assert detect_response_mode_directive("Responde por automático") is TelegramResponseMode.AUTOMATIC


def test_mode_automatic_is_detected() -> None:
    assert detect_response_mode_directive("Modo automático") is TelegramResponseMode.AUTOMATIC
