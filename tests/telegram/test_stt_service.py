from __future__ import annotations

from pathlib import Path
from dataclasses import replace
import time
import wave

import pytest

from voice.stt import AudioConverter, BaseSTTProvider, STTConfig, STTError, STTResult, STTService
from telegram_interface.multimedia import TelegramMultimediaProcessor
from tests.telegram.conftest import link_user, make_message
from telegram_interface.models import TelegramMessage


class FakeProvider(BaseSTTProvider):
    def __init__(self, text=" Hola   món ", *, available=True, delay=0.0, language="ca"):
        self.text = text
        self.available = available
        self.delay = delay
        self.language = language
        self.calls = []

    def is_available(self):
        return self.available

    def transcribe(self, path, language_hint=None):
        self.calls.append((Path(path), language_hint))
        if self.delay:
            time.sleep(self.delay)
        return STTResult(self.text, self.language)

    def health(self):
        return {"available": self.available}

    def supported_languages(self):
        return ("auto", "es", "ca", "en")


class FakeConverter:
    def __init__(self, *, error=None):
        self.error = error
        self.calls = 0

    def to_mono_16khz(self, source, destination, *, max_seconds):
        self.calls += 1
        if self.error:
            raise self.error
        with wave.open(str(destination), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(16000)
            output.writeframes(b"\x00\x00" * 1600)
        return 0.1


def build_service(tmp_path, provider=None, converter=None, **config):
    return STTService(
        provider or FakeProvider(),
        converter or FakeConverter(),
        config=STTConfig(**config),
        work_dir=tmp_path / "work",
    )


@pytest.mark.parametrize("language", ["es", "ca", "en", None])
def test_transcribes_once_with_user_language_hint_and_cleans_wav(tmp_path, language):
    provider = FakeProvider()
    service = build_service(tmp_path, provider=provider)

    result, timings = service.transcribe(tmp_path / "opaque.ogg", language_hint=language)

    assert result.text == "Hola món"
    assert provider.calls[0][1] == language
    assert len(provider.calls) == 1
    assert set(timings) == {"audio.convert", "stt.transcribe"}
    assert not list((tmp_path / "work").glob("*.wav"))


def test_unavailable_provider_does_not_convert_or_leave_files(tmp_path):
    converter = FakeConverter()
    service = build_service(tmp_path, provider=FakeProvider(available=False), converter=converter)
    with pytest.raises(STTError) as raised:
        service.transcribe(tmp_path / "opaque.ogg")
    assert raised.value.code == "stt_unavailable"
    assert converter.calls == 0


def test_corrupt_audio_error_is_preserved_and_cleanup_runs(tmp_path):
    service = build_service(
        tmp_path,
        converter=FakeConverter(error=STTError("audio_corrupt", "corrupto")),
    )
    with pytest.raises(STTError) as raised:
        service.transcribe(tmp_path / "opaque.ogg")
    assert raised.value.code == "audio_corrupt"
    assert not list((tmp_path / "work").glob("*.wav"))


def test_duration_limit_error_is_preserved_without_calling_provider(tmp_path):
    provider = FakeProvider()
    service = build_service(
        tmp_path,
        provider=provider,
        converter=FakeConverter(error=STTError("audio_too_long", "largo")),
    )
    with pytest.raises(STTError) as raised:
        service.transcribe(tmp_path / "opaque.ogg")
    assert raised.value.code == "audio_too_long"
    assert provider.calls == []


def test_stt_timeout_is_bounded_and_cleanup_runs(tmp_path):
    service = build_service(tmp_path, provider=FakeProvider(delay=0.05), timeout_seconds=0.005)
    with pytest.raises(STTError) as raised:
        service.transcribe(tmp_path / "opaque.ogg")
    assert raised.value.code == "stt_timeout"
    assert not list((tmp_path / "work").glob("*.wav"))


def test_empty_transcription_is_rejected(tmp_path):
    with pytest.raises(STTError) as raised:
        build_service(tmp_path, provider=FakeProvider("   ")).transcribe(tmp_path / "opaque.ogg")
    assert raised.value.code == "audio_empty"


def test_audio_converter_rejects_absent_ffmpeg(tmp_path):
    with pytest.raises(STTError) as raised:
        AudioConverter(ffmpeg_path="").to_mono_16khz(
            tmp_path / "in.ogg", tmp_path / "out.wav", max_seconds=1
        )
    assert raised.value.code == "ffmpeg_unavailable"


def test_gateway_routes_voice_transcript_once_with_bound_user_and_session(
    tmp_path, gateway, linker
):
    link_user(linker, atlas_user="REDACTED_bc04a68d9192")
    provider = FakeProvider("dime el tiempo", language="es")
    gateway.media_processor = TelegramMultimediaProcessor(
        stt=build_service(tmp_path, provider=provider),
        language_resolver=lambda user: {"REDACTED_bc04a68d9192": "es", "REDACTED_2c7b6821719d": "ca"}.get(user),
    )
    message = replace(
        make_message("", user_id="100", chat_id="200"),
        media_type="voice",
        local_path=str(tmp_path / "opaque.ogg"),
        media_status="quarantined",
        detected_mime="audio/ogg",
    )

    response = gateway.handle(message)

    assert response.text == "REDACTED_bc04a68d9192:dime el tiempo"
    assert len(provider.calls) == 1
    assert provider.calls[0][1] == "es"
    assert {"audio.convert", "stt.transcribe"} <= response.stage_timings_ms.keys()


def test_language_hint_and_core_context_are_isolated_between_users(tmp_path):
    provider = FakeProvider("consulta")
    processor = TelegramMultimediaProcessor(
        stt=build_service(tmp_path, provider=provider),
        language_resolver=lambda user: {"User-A": "es", "User-B": "ca"}[user],
    )
    seen = []

    class Core:
        def process(self, text, context):
            seen.append((text, context.atlas_user_id, context.session_id))
            return "ok"

    from datetime import UTC, datetime
    from telegram_interface.models import TelegramAccountState, TelegramMessage, TelegramRequestContext, TelegramUser

    for index, user in enumerate(("User-A", "User-B"), start=1):
        context = TelegramRequestContext(
            "telegram", user, f"telegram:{index}:{index}", str(index), str(index),
            index, datetime.now(UTC), "daxter", TelegramAccountState.LINKED,
            frozenset({"telegram.use"}),
        )
        message = TelegramMessage(
            index, index, TelegramUser(str(index), str(index)), "",
            media_type="voice", local_path=str(tmp_path / f"{index}.ogg"),
            media_status="quarantined",
        )
        processor.process(message, context, Core())

    assert [call[1] for call in provider.calls] == ["es", "ca"]
    assert [item[1:] for item in seen] == [
        ("User-A", "telegram:1:1"),
        ("User-B", "telegram:2:2"),
    ]


def test_telegram_audio_duration_metadata_is_parsed_without_trusting_filename():
    parsed = TelegramMessage.from_update({
        "update_id": 9,
        "message": {
            "message_id": 10, "date": 1,
            "from": {"id": 1}, "chat": {"id": 2, "type": "private"},
            "voice": {"file_id": "opaque", "duration": 181, "file_size": 100},
        },
    })
    assert parsed is not None
    assert parsed.media_duration_seconds == 181.0
