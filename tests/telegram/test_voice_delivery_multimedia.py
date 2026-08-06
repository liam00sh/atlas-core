from __future__ import annotations

from pathlib import Path

import pytest

from telegram_interface.client import TelegramClientError
from telegram_interface.models import GatewayResponse
from telegram_interface.polling import TelegramPoller
from telegram_interface.response_modes import (
    TelegramResponseMode,
    TelegramResponseModeStore,
    detect_response_mode_directive,
    resolve_delivery_mode,
)
from telegram_interface.voice_delivery import TelegramVoiceRenderer, TelegramVoiceResult
from voice.models import SynthesisResult
from voice.preferences.voice_preferences import VoicePreferences
from voice.service import VoiceService
from tests.telegram.conftest import link_user, make_message


class Provider:
    provider_id = "kokoro"

    def is_available(self):
        return True

    def supports_voice(self, _voice):
        return True

    def synthesize(self, request):
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_bytes(b"RIFFfake")
        return SynthesisResult(True, request.output_path, request.voice_id, self.provider_id)


class Player:
    def __init__(self):
        self.calls = []

    def is_available(self):
        return True

    def play(self, path):
        self.calls.append(path)
        return True


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (" MODO   VOZ ", TelegramResponseMode.AUDIO_ONLY),
        ("Responde por texto", TelegramResponseMode.TEXT_ONLY),
        ("modo automático", TelegramResponseMode.AUTOMATIC),
    ],
)
def test_response_mode_aliases_are_explicit_and_normalized(text, expected):
    assert detect_response_mode_directive(text) is expected
    assert detect_response_mode_directive(f"Me gusta decir {text} en una conversación") is None


def test_response_modes_are_persistent_and_isolated_by_atlas_user(storage):
    modes = TelegramResponseModeStore(storage)
    modes.set("User-A", TelegramResponseMode.AUDIO_ONLY)
    modes.set("User-B", TelegramResponseMode.TEXT_ONLY)
    restarted = TelegramResponseModeStore(storage)
    assert restarted.get("User-A") is TelegramResponseMode.AUDIO_ONLY
    assert restarted.get("User-B") is TelegramResponseMode.TEXT_ONLY


def test_gateway_consumes_mode_command_without_calling_core_and_keeps_users_isolated(gateway, linker, storage):
    modes = TelegramResponseModeStore(storage)
    gateway.response_mode_store = modes
    link_user(linker, user_id="100", chat_id="200", atlas_user="REDACTED_bc04a68d9192")
    response = gateway.handle(make_message("MODO VOZ", user_id="100", chat_id="200"))
    assert "responderé por voz" in response.text
    assert not response.text.startswith("REDACTED_bc04a68d9192:")
    assert modes.get("REDACTED_bc04a68d9192") is TelegramResponseMode.AUDIO_ONLY
    assert modes.get("REDACTED_2c7b6821719d") is TelegramResponseMode.AUTOMATIC


def test_automatic_uses_voice_only_for_audio_input():
    assert resolve_delivery_mode(configured_mode="automatic", incoming_media_type="voice", audio_available=True) == "audio"
    assert resolve_delivery_mode(configured_mode="automatic", incoming_media_type=None, audio_available=True) == "text"
    assert resolve_delivery_mode(configured_mode="audio_only", incoming_media_type=None, audio_available=False) == "text"


def test_renderer_never_plays_on_pc_and_cleans_wav(monkeypatch, tmp_path):
    player = Player()
    service = VoiceService(provider=Provider(), player=player, output_dir=tmp_path / "wav")

    def convert(command, **_kwargs):
        Path(command[-1]).write_bytes(b"OggSfake")
        return type("Completed", (), {"returncode": 0})()

    monkeypatch.setattr("telegram_interface.voice_delivery.subprocess.run", convert)
    renderer = TelegramVoiceRenderer(
        voice_service=service,
        preference_resolver=lambda _user: VoicePreferences(),
        personality_resolver=lambda user: "coco" if user == "User-B" else "daxter",
        output_dir=tmp_path / "ogg",
        ffmpeg_path="ffmpeg",
    )
    result = renderer.render("Respuesta", user_id="User-B")
    try:
        assert result.success
        assert result.ogg_path and result.ogg_path.read_bytes().startswith(b"OggS")
        assert player.calls == []
        assert not list((tmp_path / "wav").glob("*.wav"))
    finally:
        renderer.cleanup(result)
    assert not list((tmp_path / "ogg").glob("*.ogg"))


class Client:
    def __init__(self, *, upload_error=False):
        self.batches = [[{
            "update_id": 1,
            "message": {
                "message_id": 2, "date": 1,
                "from": {"id": 10}, "chat": {"id": 20, "type": "private"},
                "text": "hola",
            },
        }]]
        self.sent_text = []
        self.sent_voice = []
        self.upload_error = upload_error

    def get_webhook_info(self): return {"url": ""}
    def get_updates(self, **_kwargs): return self.batches.pop(0) if self.batches else []
    def send_message(self, **kwargs): self.sent_text.append(kwargs); return {}
    def send_voice(self, **kwargs):
        self.sent_voice.append(kwargs)
        if self.upload_error:
            raise TelegramClientError("fallo", code="upload", retryable=False)
        return {}


class Gateway:
    linker = type("Linker", (), {"get_account": lambda self, _user: {"state": "linked", "atlas_user_id": "User-A"}})()
    audit = None

    def handle(self, _message):
        return GatewayResponse("respuesta completa", delivery_hint="audio")


class Renderer:
    def __init__(self, tmp_path, *, render_error=False):
        self.path = tmp_path / "out.ogg"
        self.cleaned = 0
        self.render_error = render_error

    def is_available(self): return True
    def render(self, _text, *, user_id):
        if self.render_error:
            raise RuntimeError("fallo TTS simulado")
        self.path.write_bytes(b"OggS")
        return TelegramVoiceResult(True, self.path, timings_ms={"tts.synthesize": 1.0})
    def cleanup(self, result):
        self.cleaned += 1
        result.ogg_path.unlink(missing_ok=True)


@pytest.mark.parametrize("upload_error", [False, True])
def test_poller_sends_one_complete_response_and_falls_back_to_text_on_upload_error(storage, tmp_path, upload_error):
    client = Client(upload_error=upload_error)
    renderer = Renderer(tmp_path)
    poller = TelegramPoller(client=client, gateway=Gateway(), storage=storage, voice_renderer=renderer)
    poller.run(max_cycles=1)
    if upload_error:
        assert len(client.sent_text) == 1
    else:
        assert client.sent_text == []
    assert len(client.sent_voice) == 1
    assert renderer.cleaned == 1
    assert not renderer.path.exists()


def test_unexpected_tts_error_falls_back_to_one_text_response(storage, tmp_path):
    client = Client()
    renderer = Renderer(tmp_path, render_error=True)
    TelegramPoller(
        client=client, gateway=Gateway(), storage=storage, voice_renderer=renderer
    ).run(max_cycles=1)
    assert len(client.sent_text) == 1
    assert client.sent_voice == []
