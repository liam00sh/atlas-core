from telegram_interface.response_modes import (
    TelegramResponseMode,
    TelegramResponseModeStore,
    confirmation_text,
    detect_response_mode_directive,
    resolve_delivery_mode,
)
from telegram_interface.storage import TelegramStorage


def test_detects_text_only() -> None:
    assert (
        detect_response_mode_directive(
            "Respóndeme únicamente por texto"
        )
        is TelegramResponseMode.TEXT_ONLY
    )


def test_detects_audio_only() -> None:
    assert (
        detect_response_mode_directive(
            "A partir de ahora responde solo por audio"
        )
        is TelegramResponseMode.AUDIO_ONLY
    )


def test_cancel_restores_automatic() -> None:
    assert (
        detect_response_mode_directive(
            "Deja de responder solo por texto"
        )
        is TelegramResponseMode.AUTOMATIC
    )


def test_mode_is_persistent_per_user(tmp_path) -> None:
    storage = TelegramStorage(tmp_path / "state.json")
    modes = TelegramResponseModeStore(storage)

    modes.set("REDACTED_2c7b6821719d", TelegramResponseMode.AUDIO_ONLY)

    assert modes.get("REDACTED_f73137d930c3") is TelegramResponseMode.AUDIO_ONLY
    assert modes.get("REDACTED_bc04a68d9192") is TelegramResponseMode.AUTOMATIC


def test_automatic_follows_input_type() -> None:
    assert (
        resolve_delivery_mode(
            configured_mode="automatic",
            incoming_media_type=None,
            audio_available=True,
        )
        == "text"
    )
    assert (
        resolve_delivery_mode(
            configured_mode="automatic",
            incoming_media_type="voice",
            audio_available=True,
        )
        == "audio"
    )


def test_audio_only_falls_back_without_losing_preference() -> None:
    assert (
        resolve_delivery_mode(
            configured_mode="audio_only",
            incoming_media_type=None,
            audio_available=False,
        )
        == "text"
    )


def test_confirmation_describes_audio_fallback() -> None:
    assert "respaldo" in confirmation_text("audio_only")
