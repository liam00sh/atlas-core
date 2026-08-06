from __future__ import annotations

from pathlib import Path
import wave

import pytest

from telegram_interface.media import TelegramMediaError, TelegramMediaValidator
from tests.telegram.ogg_fixtures import make_ogg_opus, make_ogg_unknown, make_ogg_vorbis


def _validate(tmp_path: Path, name: str, payload: bytes, **kwargs):
    path = tmp_path / name
    path.write_bytes(payload)
    return TelegramMediaValidator().validate(
        path,
        media_type=kwargs.pop("media_type", "audio"),
        max_bytes=1024 * 1024,
        **kwargs,
    )


@pytest.mark.parametrize("extension", [".oga", ".ogg"])
def test_accepts_valid_opus_by_content_for_ogg_extensions(tmp_path, extension):
    mime, size, digest = _validate(
        tmp_path,
        "recording" + extension,
        make_ogg_opus(audio_packet=b"audio with accidental marker #! inside"),
    )
    assert mime == "audio/ogg"
    assert size > 100
    assert len(digest) == 64


def test_accepts_valid_telegram_voice_mime(tmp_path):
    mime, _, _ = _validate(
        tmp_path,
        "opaque.quarantine",
        make_ogg_opus(),
        media_type="voice",
        declared_mime="audio/ogg; codecs=opus",
    )
    assert mime == "audio/ogg"


def test_accepts_structurally_valid_vorbis(tmp_path):
    assert _validate(tmp_path, "recording.oga", make_ogg_vorbis())[0] == "audio/ogg"


def test_accepts_short_complete_ogg_and_mobile_style_without_eos_flag(tmp_path):
    short = make_ogg_opus(audio_packet=b"\xf8", eos=False)
    assert len(short) < 256
    assert _validate(tmp_path, "short.oga", short)[0] == "audio/ogg"


def test_accepts_opus_packet_split_into_multiple_ogg_segments(tmp_path):
    segmented = make_ogg_opus(audio_packet=b"\xf8" + (b"\x7f" * 599))
    assert _validate(tmp_path, "segmented.ogg", segmented)[0] == "audio/ogg"


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (b"OggS\x00", "media_corrupt"),
        (b"MZ" + b"\x00" * 100, "media_executable"),
        (make_ogg_opus()[:-1], "media_corrupt"),
        (make_ogg_opus() + b"MZpayload", "media_polyglot"),
    ],
)
def test_rejects_truncated_executable_corrupt_and_polyglot_ogg(tmp_path, payload, expected):
    with pytest.raises(TelegramMediaError) as raised:
        _validate(tmp_path, "hostile.oga", payload)
    assert raised.value.code == expected


def test_rejects_crc_corruption(tmp_path):
    payload = bytearray(make_ogg_opus())
    payload[-1] ^= 0x01
    with pytest.raises(TelegramMediaError) as raised:
        _validate(tmp_path, "corrupt.ogg", bytes(payload))
    assert raised.value.code == "media_corrupt"


def test_rejects_false_declared_mime_even_with_valid_ogg(tmp_path):
    with pytest.raises(TelegramMediaError) as raised:
        _validate(
            tmp_path,
            "voice.oga",
            make_ogg_opus(),
            declared_mime="image/png",
        )
    assert raised.value.code == "mime_mismatch"


def test_rejects_ogg_with_unapproved_codec_header(tmp_path):
    with pytest.raises(TelegramMediaError) as raised:
        _validate(tmp_path, "video.ogg", make_ogg_unknown())
    assert raised.value.code == "rejected_type"


def test_other_accepted_audio_signature_does_not_regress(tmp_path):
    path = tmp_path / "sample.wav"
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(b"\x00\x00" * 160)
    assert TelegramMediaValidator().validate(
        path, media_type="audio", max_bytes=4096, declared_mime="audio/wav"
    )[0] == "audio/wav"
