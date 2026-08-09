from pathlib import Path

from voice.models import SynthesisRequest
from voice.providers.kokoro_provider import KokoroProvider
from types import SimpleNamespace


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


def test_official_bridge_can_use_opt_in_persistent_process(monkeypatch) -> None:
    monkeypatch.setenv("ATLAS_KOKORO_PERSISTENT", "true")
    provider = KokoroProvider(command='python "C:\\Atlas\\tools\\kokoro_bridge.py"')
    assert provider._uses_persistent_bridge() is True


def test_persistent_bridge_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ATLAS_KOKORO_PERSISTENT", raising=False)
    provider = KokoroProvider(command='python "C:\\Atlas\\tools\\kokoro_bridge.py"')
    assert provider._uses_persistent_bridge() is False


def test_generic_bridge_keeps_one_shot_compatibility() -> None:
    provider = KokoroProvider(command="python bridge.py")
    assert provider._uses_persistent_bridge() is False


def test_provider_sends_unicode_to_subprocess_as_explicit_utf8(tmp_path, monkeypatch) -> None:
    observed = {}
    output = tmp_path / "unicode.wav"

    def fake_run(_command, **kwargs):
        observed.update(kwargs)
        output.write_bytes(b"RIFF-safe")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("voice.providers.kokoro_provider.subprocess.run", fake_run)
    result = KokoroProvider(command="python bridge.py").synthesize(
        SynthesisRequest(
            text="¡Hola, REDACTED_2c7b6821719d! 😄 Mañana quizá llueva en REDACTED_a77d7bb7adbf.",
            voice_id="daxter_alex", provider_voice_id="em_alex", output_path=output,
        )
    )
    assert result.success is True
    assert observed["encoding"] == "utf-8"
    assert observed["errors"] == "replace"
    assert "😄" in observed["input"]
