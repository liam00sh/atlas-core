from __future__ import annotations

from array import array
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import wave

import pytest

from scripts.check_stt_config import _safe_config, transcribe_local_audio
from telegram_interface.multimedia import TelegramMultimediaProcessor
from tests.telegram.conftest import link_user, make_message
from voice.stt import BaseSTTProvider, STTConfidence, STTConfig, STTError, STTResult
from voice.stt_policy import (
    AtlasIntentConfidenceResolver,
    IntentConfidence,
    STTDecisionKind,
    STTInputPolicy,
    STTIntentContext,
    process_stt_result,
)


class LiveProvider(BaseSTTProvider):
    def __init__(self, text="Enciende la luz"):
        self.text = text
        self.calls = 0

    def is_available(self):
        return True

    def transcribe(self, path, language_hint=None):
        self.calls += 1
        return STTResult(
            self.text,
            "es",
            1.0,
            confidence=STTConfidence.HIGH,
            avg_logprob=-0.2,
            no_speech_probability=0.04,
            language_probability=0.96,
            mean_word_probability=0.91,
            min_word_probability=0.86,
            compression_ratio=1.1,
            vad_speech_seconds=0.8,
        )

    def health(self):
        return {"provider": "fake-local", "device": "cpu", "compute_type": "int8"}

    def supported_languages(self):
        return ("es",)


class LiveConverter:
    def to_mono_16khz(self, source, destination, *, max_seconds):
        samples = array("h", (2200 if index % 2 else -2200 for index in range(16000)))
        with wave.open(str(destination), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(16000)
            output.writeframes(samples.tobytes())
        return 1.0


def _ogg(path: Path) -> Path:
    path.write_bytes(b"OggS" + b"\x00" * 128)
    return path


def test_safe_cli_config_disables_download_even_if_environment_allows_it(monkeypatch):
    monkeypatch.setenv("ATLAS_STT_ALLOW_MODEL_DOWNLOAD", "true")
    assert _safe_config().allow_model_download is False


def test_live_transcribes_with_real_service_policy_and_cleans_wav(tmp_path):
    provider = LiveProvider()
    report = transcribe_local_audio(
        _ogg(tmp_path / "voice.oga"),
        config=STTConfig(allow_model_download=True),
        provider=provider,
        converter=LiveConverter(),
        work_dir=tmp_path / "work",
    )
    assert provider.calls == 1
    assert report.result.text == "Enciende la luz"
    assert report.result.confidence is STTConfidence.HIGH
    assert report.decision.intent_confidence is IntentConfidence.HIGH
    assert report.decision.kind is STTDecisionKind.PROCESS
    assert report.detected_mime == "audio/ogg"
    assert not list((tmp_path / "work").glob("*.wav"))


def test_live_rejects_fake_audio_before_provider_and_leaves_no_wav(tmp_path):
    provider = LiveProvider()
    source = tmp_path / "not-audio.oga"
    source.write_text("contenido que no es audio", encoding="utf-8")
    with pytest.raises(STTError) as raised:
        transcribe_local_audio(
            source,
            provider=provider,
            converter=LiveConverter(),
            work_dir=tmp_path / "work",
        )
    assert raised.value.code == "audio_invalid_format"
    assert provider.calls == 0
    assert not list(tmp_path.rglob("*.wav"))


@pytest.mark.parametrize(
    ("speech", "expected"),
    [
        (STTConfidence.HIGH, STTDecisionKind.PROCESS),
        (STTConfidence.MEDIUM, STTDecisionKind.CONFIRM),
        (STTConfidence.LOW, STTDecisionKind.REPEAT),
    ],
)
def test_speech_confidence_is_independent_from_high_intent(speech, expected):
    decision = STTInputPolicy().evaluate(STTResult("Enciende la luz", confidence=speech))
    assert decision.intent_confidence is IntentConfidence.HIGH
    assert decision.kind is expected


def test_intent_high_for_resolved_home_action():
    resolution = AtlasIntentConfidenceResolver().resolve("Enciende la luz")
    assert resolution.confidence is IntentConfidence.HIGH
    assert resolution.entities


def test_intent_medium_when_reminder_has_no_time():
    decision = STTInputPolicy().evaluate(
        STTResult("Recuérdame comprar pan", confidence=STTConfidence.HIGH)
    )
    assert decision.intent_confidence is IntentConfidence.MEDIUM
    assert decision.kind is STTDecisionKind.CLARIFY
    assert "Cuándo" in (decision.response or "")


@pytest.mark.parametrize(
    ("text", "question"),
    [
        ("Enciende la", "encienda"),
        ("Pon la", "televisión"),
        ("Recuérdame", "recuerde"),
        ("Abre", "abra"),
    ],
)
def test_intent_low_asks_specific_question_for_missing_slot(text, question):
    decision = STTInputPolicy().evaluate(STTResult(text, confidence=STTConfidence.HIGH))
    assert decision.intent_confidence is IntentConfidence.LOW
    assert decision.kind is STTDecisionKind.CLARIFY
    assert question.casefold() in (decision.response or "").casefold()


def test_pending_slot_and_immediate_context_are_considered():
    resolver = AtlasIntentConfidenceResolver()
    with_pending = resolver.resolve("hazlo", STTIntentContext(pending_slots=("confirmation",)))
    with_history = resolver.resolve("hazlo", STTIntentContext(immediate_history=("abre la calculadora",)))
    without_context = resolver.resolve("hazlo")
    assert with_pending.confidence is IntentConfidence.HIGH
    assert with_history.confidence is IntentConfidence.MEDIUM
    assert without_context.confidence is IntentConfidence.LOW


def test_ambiguous_intent_never_calls_atlas_or_memory_writer():
    atlas_calls = []
    memory_writes = []

    def process(text):
        atlas_calls.append(text)
        memory_writes.append(text)
        return "incorrecto"

    response = process_stt_result(
        STTResult("Abre", confidence=STTConfidence.HIGH),
        process,
    )
    assert "abra" in response
    assert atlas_calls == []
    assert memory_writes == []


@pytest.mark.parametrize(
    "text",
    [
        "Borra la memoria de ayer",
        "Apaga Atlas",
        "Abre la puerta principal",
        "Envía un mensaje de prueba",
        "Modifica el usuario de prueba",
        "Elimina los datos temporales",
    ],
)
def test_sensitive_action_requires_high_speech_confidence(text):
    calls = []
    decision = STTInputPolicy().evaluate(STTResult(text, confidence=STTConfidence.MEDIUM))
    process_stt_result(
        STTResult(text, confidence=STTConfidence.MEDIUM),
        lambda value: calls.append(value),
    )
    assert decision.sensitive
    assert decision.kind is STTDecisionKind.CONFIRM
    assert calls == []


def test_audio_quality_can_downgrade_good_decoder_metrics(tmp_path):
    class SilentConverter:
        def to_mono_16khz(self, source, destination, *, max_seconds):
            with wave.open(str(destination), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(16000)
                output.writeframes(b"\x00\x00" * 16000)
            return 1.0

    report = transcribe_local_audio(
        _ogg(tmp_path / "silent.oga"),
        provider=LiveProvider("consulta factual"),
        converter=SilentConverter(),
        work_dir=tmp_path / "work",
    )
    assert report.result.confidence is STTConfidence.LOW
    assert report.decision.kind is STTDecisionKind.REPEAT


def _media_context(session="telegram:test:chat"):
    return SimpleNamespace(atlas_user_id="user-test", session_id=session)


def _voice_message(tmp_path):
    return SimpleNamespace(
        media_type="voice",
        media_status="quarantined",
        local_path=str(tmp_path / "voice.oga"),
    )


def test_medium_transcript_waits_for_typed_confirmation_then_processes_once(tmp_path):
    class Service:
        def transcribe(self, *_args, **_kwargs):
            return STTResult("qué tiempo hace", "es", confidence=STTConfidence.MEDIUM), {}

    calls = []
    core = SimpleNamespace(process=lambda text, context: calls.append(text) or "respuesta")
    processor = TelegramMultimediaProcessor(stt=Service())
    context = _media_context()
    first = processor.process(_voice_message(tmp_path), context, core)
    confirmed = processor.process_text_followup("Sí", context, core)
    assert first is not None and first.text
    assert confirmed is not None and confirmed.text == "respuesta"
    assert calls == ["qué tiempo hace"]


def test_sensitive_medium_transcript_cannot_be_elevated_by_yes(tmp_path):
    class Service:
        def transcribe(self, *_args, **_kwargs):
            return STTResult("borra la memoria", "es", confidence=STTConfidence.MEDIUM), {}

    calls = []
    core = SimpleNamespace(process=lambda text, context: calls.append(text))
    processor = TelegramMultimediaProcessor(stt=Service())
    context = _media_context()
    processor.process(_voice_message(tmp_path), context, core)
    result = processor.process_text_followup("sí", context, core)
    assert result is not None and "repite la orden sensible completa" in result.text
    assert calls == []


def test_incomplete_command_combines_only_confirmed_slot(tmp_path):
    class Service:
        def transcribe(self, *_args, **_kwargs):
            return STTResult("enciende la", "es", confidence=STTConfidence.HIGH), {}

    calls = []
    core = SimpleNamespace(process=lambda text, context: calls.append(text) or "hecho")
    processor = TelegramMultimediaProcessor(stt=Service())
    context = _media_context()
    first = processor.process(_voice_message(tmp_path), context, core)
    completed = processor.process_text_followup("la luz", context, core)
    assert first is not None and "encienda" in first.text
    assert completed is not None and completed.text == "hecho"
    assert calls == ["enciende la luz"]


def test_pending_stt_state_is_isolated_by_session_and_expires(tmp_path):
    now = [10.0]

    class Service:
        def transcribe(self, *_args, **_kwargs):
            return STTResult("qué tiempo hace", "es", confidence=STTConfidence.MEDIUM), {}

    calls = []
    core = SimpleNamespace(process=lambda text, context: calls.append((text, context.session_id)))
    processor = TelegramMultimediaProcessor(
        stt=Service(), clarification_ttl_seconds=2, clock=lambda: now[0]
    )
    first_context = _media_context("session:a")
    other_context = _media_context("session:b")
    processor.process(_voice_message(tmp_path), first_context, core)
    assert processor.process_text_followup("sí", other_context, core) is None
    now[0] = 13.0
    assert processor.process_text_followup("sí", first_context, core) is None
    assert calls == []


def test_gateway_routes_typed_stt_confirmation_to_same_core_once(tmp_path, gateway, linker):
    link_user(linker, atlas_user="REDACTED_bc04a68d9192")

    class Service:
        def transcribe(self, *_args, **_kwargs):
            return STTResult("qué tiempo hace", "es", confidence=STTConfidence.MEDIUM), {}

    gateway.media_processor = TelegramMultimediaProcessor(stt=Service())
    voice = replace(
        make_message(""),
        media_type="voice",
        media_status="quarantined",
        local_path=str(tmp_path / "voice.oga"),
    )
    first = gateway.handle(voice)
    confirmed = gateway.handle(make_message("sí", update_id=2, message_id=11))
    assert "He entendido" in first.text
    assert confirmed.text == "REDACTED_bc04a68d9192:qué tiempo hace"
