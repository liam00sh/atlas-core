from pathlib import Path

from voice.models import SynthesisRequest
from voice.providers.kokoro_provider import KokoroProvider


def test_provider_rejects_logical_id_as_engine_voice(tmp_path) -> None:
    provider = KokoroProvider(command="python bridge.py")

    result = provider.synthesize(
        SynthesisRequest(
            text="Hola.",
            voice_id="daxter_alex",
            provider_voice_id="daxter_alex",
            output_path=tmp_path / "test.wav",
        )
    )

    assert result.success is False
    assert "no admite" in (result.error or "")


def test_provider_accepts_kokoro_engine_voice() -> None:
    provider = KokoroProvider(command="python bridge.py")

    assert provider.supports_voice("em_alex") is True
    assert provider.supports_voice("ef_dora") is True
