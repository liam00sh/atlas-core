from __future__ import annotations

from pathlib import Path
import zipfile

import pytest

from telegram_interface.config import TelegramConfig
from telegram_interface.models import TelegramMessage, TelegramUser
from telegram_interface.polling import TelegramPoller
from telegram_interface.media import (
    TelegramMediaDownloader,
    TelegramMediaEnvelope,
    TelegramMediaError,
    TelegramMediaLimits,
    TelegramMediaQuarantine,
    TelegramMediaValidator,
)


class _Client:
    def __init__(self, payload: bytes, remote_path: str = "voice/file.bin") -> None:
        self.payload = payload
        self.remote_path = remote_path
        self.downloads = 0

    def get_file(self, *, file_id):
        return {"file_path": self.remote_path, "file_size": len(self.payload)}

    def download_file(self, *, file_path, destination, max_bytes):
        self.downloads += 1
        path = Path(destination)
        path.write_bytes(self.payload)
        return path


def _downloader(tmp_path, client):
    return TelegramMediaDownloader(
        client,
        TelegramMediaQuarantine(tmp_path / "quarantine"),
        TelegramMediaValidator(),
        TelegramMediaLimits(1024, 1024, 1024, 1024),
    )


def test_detects_real_type_without_trusting_declared_name_or_mime(tmp_path):
    client = _Client(b"OggS" + b"\x00" * 32)
    result = _downloader(tmp_path, client).download(
        TelegramMediaEnvelope("voice", "opaque-id", declared_size=36)
    )
    try:
        assert result.detected_mime == "audio/ogg"
        assert result.quarantine_path.suffix == ".ogg"
        assert result.sha256 and len(result.sha256) == 64
        assert set(result.timings_ms) == {"media.download", "media.validation"}
    finally:
        TelegramMediaQuarantine(tmp_path / "quarantine").cleanup(result.quarantine_path)


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (b"MZ" + b"\x00" * 30, "media_executable"),
        (b"OggS" + b"MZ" + b"\x00" * 30, "media_polyglot"),
        (b"", "media_empty"),
    ],
)
def test_rejects_executables_polyglots_and_empty_files(tmp_path, payload, code):
    with pytest.raises(TelegramMediaError) as raised:
        _downloader(tmp_path, _Client(payload)).download(
            TelegramMediaEnvelope("voice", "opaque-id")
        )
    assert raised.value.code == code
    assert not list((tmp_path / "quarantine").rglob("*.*"))


@pytest.mark.parametrize("remote_path", ["../secret", "/absolute/file", "https://evil.invalid/file"])
def test_rejects_unsafe_telegram_file_paths_before_download(tmp_path, remote_path):
    client = _Client(b"OggSdata", remote_path)
    with pytest.raises(TelegramMediaError) as raised:
        _downloader(tmp_path, client).download(TelegramMediaEnvelope("voice", "id"))
    assert raised.value.code == "metadata_missing"
    assert client.downloads == 0


def test_rejects_video_and_animation_at_transport_boundary(tmp_path):
    for media_type in ("video", "animation"):
        with pytest.raises(TelegramMediaError) as raised:
            _downloader(tmp_path, _Client(b"content")).download(
                TelegramMediaEnvelope(media_type, "id")
            )
        assert raised.value.code == "rejected_type"


def test_rejects_docx_with_path_traversal(tmp_path):
    path = tmp_path / "bad.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "types")
        archive.writestr("word/document.xml", "doc")
        archive.writestr("../escape.txt", "bad")
    with pytest.raises(TelegramMediaError) as raised:
        TelegramMediaValidator().validate(path, media_type="document", max_bytes=4096)
    assert raised.value.code == "media_path_traversal"


def test_rejects_docx_with_backslash_traversal(tmp_path):
    path = tmp_path / "bad-backslash.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "types")
        archive.writestr("word/document.xml", "doc")
        archive.writestr("..\\escape.txt", "bad")
    with pytest.raises(TelegramMediaError) as raised:
        TelegramMediaValidator().validate(path, media_type="document", max_bytes=4096)
    assert raised.value.code == "media_path_traversal"


def test_download_client_cannot_redirect_destination_outside_quarantine(tmp_path):
    outside = tmp_path / "outside.ogg"

    class RedirectingClient(_Client):
        def download_file(self, **_kwargs):
            outside.write_bytes(b"OggS" + b"\x00" * 20)
            return outside

    with pytest.raises(TelegramMediaError) as raised:
        _downloader(tmp_path, RedirectingClient(b"ignored")).download(
            TelegramMediaEnvelope("voice", "opaque")
        )
    assert raised.value.code == "media_path_traversal"
    assert outside.exists()


def test_generic_mp4_container_is_not_accepted_as_proven_audio(tmp_path):
    payload = b"\x00\x00\x00\x18ftypisom" + b"\x00" * 20
    with pytest.raises(TelegramMediaError) as raised:
        _downloader(tmp_path, _Client(payload)).download(TelegramMediaEnvelope("audio", "opaque"))
    assert raised.value.code == "rejected_type"


def test_media_limits_are_typed_configuration_without_secret_content():
    config = TelegramConfig.from_env(
        {
            "ATLAS_TELEGRAM_ENABLED": "false",
            "ATLAS_TELEGRAM_VOICE_MAX_BYTES": "4096",
            "ATLAS_TELEGRAM_MEDIA_TTL_HOURS": "6",
        }
    )

    assert config.media_voice_max_bytes == 4096
    assert config.media_ttl_hours == 6
    assert config.safe_summary()["media_limits_bytes"]["voice"] == 4096


def test_audio_over_duration_limit_is_rejected_before_telegram_download(tmp_path, storage):
    client = _Client(b"OggS" + b"\x00" * 20)
    gateway = type("Gateway", (), {})()
    poller = TelegramPoller(
        client=client, gateway=gateway, storage=storage,
        media_root=tmp_path / "quarantine", audio_max_duration_seconds=30,
    )
    try:
        message = TelegramMessage(
            1, 1, TelegramUser("external", "chat"), "", media_type="voice",
            file_id="opaque", file_size=24, media_duration_seconds=31,
        )
        assert poller._prepare_media(message).media_status == "audio_too_long"
        assert client.downloads == 0
    finally:
        poller.stop()
