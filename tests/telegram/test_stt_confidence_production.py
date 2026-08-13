from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import voice.stt as stt_module
from telegram_interface.multimedia import TelegramMultimediaProcessor
from voice.stt import (
    FasterWhisperSTTProvider,
    STTConfidence,
    STTConfig,
    STTResult,
    classify_stt_confidence,
    find_local_faster_whisper_model,
    resolve_stt_backend,
)
from voice.stt_policy import STTDecisionKind, STTInputPolicy, process_stt_result


def _local_model(path: Path) -> Path:
    path.mkdir(parents=True)
    for name in ("config.json", "model.bin", "tokenizer.json"):
        (path / name).write_bytes(b"local-test-model")
    return path


def test_config_accepts_documented_timeout_and_legacy_alias():
    assert STTConfig.from_env({"ATLAS_STT_TIMEOUT": "12"}).timeout_seconds == 12
    assert STTConfig.from_env({"ATLAS_STT_TIMEOUT_SECONDS": "13"}).timeout_seconds == 13
    assert STTConfig.from_env({}).device == "auto"


def test_complete_cached_model_is_detected_without_download(tmp_path, monkeypatch):
    cache = tmp_path / "hub"
    repo = cache / "models--Systran--faster-whisper-small"
    revision = "local-revision"
    (repo / "refs").mkdir(parents=True)
    (repo / "refs" / "main").write_text(revision, encoding="utf-8")
    expected = _local_model(repo / "snapshots" / revision)
    monkeypatch.setenv("HUGGINGFACE_HUB_CACHE", str(cache))

    config = STTConfig(model="small", allow_model_download=False)
    assert find_local_faster_whisper_model(config) == expected
    assert FasterWhisperSTTProvider(config).is_available()


def test_incomplete_cache_is_not_reported_as_ready(tmp_path, monkeypatch):
    cache = tmp_path / "hub"
    repo = cache / "models--Systran--faster-whisper-small"
    (repo / "refs").mkdir(parents=True)
    (repo / "refs" / "main").write_text("missing", encoding="utf-8")
    monkeypatch.setenv("HUGGINGFACE_HUB_CACHE", str(cache))
    assert find_local_faster_whisper_model(STTConfig()) is None


def test_auto_backend_falls_back_to_cpu_when_cuda_dll_is_missing(monkeypatch):
    import ctranslate2

    monkeypatch.setattr(ctranslate2, "get_cuda_device_count", lambda: 1)
    monkeypatch.setattr(stt_module, "_windows_dll_available", lambda _name: False)
    backend = resolve_stt_backend(STTConfig(device="auto", compute_type="auto"))
    assert backend.device == "cpu"
    assert backend.compute_type == "int8"
    assert "cublas64_12.dll" in (backend.fallback_reason or "")


@pytest.mark.parametrize(
    ("logprob", "no_speech", "language", "expected"),
    [
        (-0.2, 0.05, 0.95, STTConfidence.HIGH),
        (-0.8, 0.25, 0.70, STTConfidence.MEDIUM),
        (-1.4, 0.90, 0.20, STTConfidence.LOW),
    ],
)
def test_confidence_uses_model_evidence(logprob, no_speech, language, expected):
    level, score = classify_stt_confidence(
        avg_logprob=logprob,
        no_speech_probability=no_speech,
        language_probability=language,
        config=STTConfig(),
    )
    assert level is expected
    assert score is not None and 0 <= score <= 1


def test_provider_collects_segment_and_language_metrics(tmp_path, monkeypatch):
    model_path = _local_model(tmp_path / "model")

    class Model:
        def __init__(self, *_args, **_kwargs):
            pass

        def transcribe(self, *_args, **_kwargs):
            segments = [SimpleNamespace(text=" Hola", start=0.0, end=1.0, avg_logprob=-0.2, no_speech_prob=0.05)]
            return iter(segments), SimpleNamespace(language="es", language_probability=0.95, duration=1.0)

    import faster_whisper

    monkeypatch.setattr(faster_whisper, "WhisperModel", Model)
    provider = FasterWhisperSTTProvider(STTConfig(model_path=model_path, device="cpu"))
    result = provider.transcribe(tmp_path / "audio.wav")
    assert result.text == "Hola"
    assert result.confidence is STTConfidence.HIGH
    assert result.avg_logprob == pytest.approx(-0.2)
    assert result.no_speech_probability == pytest.approx(0.05)


def test_runtime_cuda_failure_retries_once_on_cpu(tmp_path, monkeypatch):
    model_path = _local_model(tmp_path / "model")
    devices = []

    class Model:
        def __init__(self, *_args, device, **_kwargs):
            self.device = device
            devices.append(device)

        def transcribe(self, *_args, **_kwargs):
            if self.device == "cuda":
                raise OSError("missing runtime library")
            segment = SimpleNamespace(text=" consulta", start=0.0, end=1.0, avg_logprob=-0.2, no_speech_prob=0.05)
            return iter([segment]), SimpleNamespace(language="es", language_probability=0.95, duration=1.0)

    import faster_whisper

    monkeypatch.setattr(faster_whisper, "WhisperModel", Model)
    provider = FasterWhisperSTTProvider(STTConfig(model_path=model_path, device="cpu"))
    provider._backend = stt_module.STTBackend("cuda", "float16")
    result = provider.transcribe(tmp_path / "audio.wav")
    assert result.text == "consulta"
    assert devices == ["cuda", "cpu"]
    assert provider.health()["device"] == "cpu"


@pytest.mark.parametrize("language", ["es", "ca", "en"])
def test_high_confidence_language_is_processed_once(language):
    calls = []
    result = STTResult("consulta factual", language, confidence=STTConfidence.HIGH)
    assert process_stt_result(result, lambda text: calls.append(text) or "ok") == "ok"
    assert calls == ["consulta factual"]


def test_medium_sensitive_command_never_reaches_core_or_memory():
    calls = []
    result = STTResult("Recuerda que la clave es azul", confidence=STTConfidence.MEDIUM)
    response = process_stt_result(result, lambda text: calls.append(text))
    assert calls == []
    assert "no la ejecutaré" in response
    assert "¿Es correcto?" in response


def test_low_confidence_noise_never_reaches_core():
    calls = []
    result = STTResult("enciende algo", confidence=STTConfidence.LOW)
    decision = STTInputPolicy().evaluate(result)
    assert decision.kind is STTDecisionKind.REPEAT
    assert process_stt_result(result, lambda text: calls.append(text))
    assert calls == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Enciende la...", "Qué elemento"),
        ("Pon la...", "Qué elemento"),
        ("Recuérdame...", "qué quieres que te recuerde"),
    ],
)
def test_incomplete_high_confidence_command_asks_for_missing_slot(text, expected):
    decision = STTInputPolicy().evaluate(STTResult(text, confidence=STTConfidence.HIGH))
    assert decision.kind is STTDecisionKind.CLARIFY
    assert expected.casefold() in (decision.response or "").casefold()


def test_telegram_medium_confidence_does_not_call_atlas(tmp_path):
    class Service:
        def transcribe(self, *_args, **_kwargs):
            return STTResult("apaga la luz", "es", confidence=STTConfidence.MEDIUM), {"stt.transcribe": 4.0}

    calls = []
    processor = TelegramMultimediaProcessor(stt=Service())
    message = SimpleNamespace(media_type="voice", media_status="quarantined", local_path=str(tmp_path / "audio.ogg"))
    context = SimpleNamespace(atlas_user_id="user-test")
    core = SimpleNamespace(process=lambda text, ctx: calls.append((text, ctx)))
    response = processor.process(message, context, core)
    assert response is not None and "no la ejecutaré" in response.text
    assert calls == []


def test_telegram_high_confidence_calls_atlas_exactly_once(tmp_path):
    class Service:
        def transcribe(self, *_args, **_kwargs):
            return STTResult("qué tiempo hace", "es", confidence=STTConfidence.HIGH), {}

    calls = []
    processor = TelegramMultimediaProcessor(stt=Service())
    message = SimpleNamespace(media_type="voice", media_status="quarantined", local_path=str(tmp_path / "audio.ogg"))
    context = SimpleNamespace(atlas_user_id="user-test")
    core = SimpleNamespace(process=lambda text, ctx: calls.append((text, ctx)) or "respuesta")
    response = processor.process(message, context, core)
    assert response is not None and response.text == "respuesta"
    assert [item[0] for item in calls] == ["qué tiempo hace"]
