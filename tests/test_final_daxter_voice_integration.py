from __future__ import annotations

import json
from pathlib import Path
import sys
import wave

from conversation.daxter_personality import PersonalityAdapter, PersonalityStrength, ResponseStyleContext
from conversation.response_models import BaseResponse, FactPreservationValidator
from voice.end_to_end import ManualVoiceSession
from voice.models import SynthesisRequest, SynthesisResult
from voice.providers.chatterbox_daxter_provider import ChatterboxDaxterProvider
from voice.style import VoiceStyleSelector
from voice.stt import STTConfidence, STTError, STTResult
from voice.text_normalizer import ContextualTranscriptNormalizer, SpeechTextNormalizer


ROOT = Path(__file__).resolve().parents[1]


def _write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * 160)


def test_final_catalog_has_an_explicit_human_decision_for_every_emotion():
    payload = json.loads((ROOT / "voice_profiles" / "DAXTER_EMOTION_CATALOG_FINAL.json").read_text(encoding="utf-8"))
    decisions = {item["id"]: item["human_validation"]["status"] for item in payload["emotions"]}
    assert len(decisions) == 15
    assert list(decisions.values()).count("approved") == 7
    assert list(decisions.values()).count("needs_adjustment") == 7
    assert list(decisions.values()).count("fallback") == 1
    assert payload["active_reference_strategy"] == "winner_jak2_diverse_identity_first"


def test_nonapproved_emotions_use_the_safe_neutral_runtime_fallback():
    selector = VoiceStyleSelector(ROOT / "voice_profiles" / "DAXTER_EMOTION_CATALOG_FINAL.json")
    assert selector.resolve("curioso", "alta").emotion == "neutral"
    assert selector.resolve("sonoliento", "baja").emotion == "neutral"
    assert selector.resolve("picaro", "media").emotion == "picaro"


def test_fact_contract_covers_numbers_names_results_permissions_errors_and_uncertainty():
    base = BaseResponse(
        text="REDACTED_f73137d930c3: la luz 2 no se encendió.",
        facts=("REDACTED_f73137d930c3", "2"),
        action_result="no se encendió",
        permissions=("sin permiso",),
        errors=("E42",),
        uncertainty="no sé si hay corriente",
    )
    styled = "Vaya, REDACTED_f73137d930c3: la luz 2 no se encendió; E42, sin permiso y no sé si hay corriente."
    assert FactPreservationValidator().validate(base, styled) == (True, ())
    valid, issues = FactPreservationValidator().validate(base, "Hecho, la luz está encendida.")
    assert valid is False
    assert {item.split(":", 1)[0] for item in issues} >= {"fact", "action_result", "permission", "error", "uncertainty"}


def test_personality_levels_preserve_facts_and_sensitive_context_is_plain():
    adapter = PersonalityAdapter()
    base = BaseResponse.from_text("REDACTED_f73137d930c3 completó 3 tareas correctamente.")
    outputs = [
        adapter.adapt(base, ResponseStyleContext(request_type="success", personality_strength=strength), seed=8)
        for strength in PersonalityStrength
    ]
    assert all(result.facts_preserved for result in outputs)
    assert all("REDACTED_f73137d930c3" in result.styled_text and "3" in result.styled_text for result in outputs)
    assert len(outputs[2].styled_text) > len(outputs[1].styled_text)
    sensitive = adapter.adapt(base, ResponseStyleContext(request_type="security", personality_strength=PersonalityStrength.HIGH))
    assert sensitive.styled_text == base.text


class _FakeChatterbox(ChatterboxDaxterProvider):
    calls = 0

    def _request_worker(self, payload: dict) -> dict:
        self.calls += 1
        _write_wav(Path(payload["output_path"]))
        return {"success": True}


def test_chatterbox_cache_key_and_reuse_include_emotion_and_profile(tmp_path):
    reference = tmp_path / "reference.wav"
    _write_wav(reference)
    provider = _FakeChatterbox(
        reference_path=reference,
        worker_command=[sys.executable, str(ROOT / "tools" / "chatterbox_worker.py")],
        cache_dir=tmp_path / "cache",
    )
    def request(name: str, emotion: str = "neutral") -> SynthesisRequest:
        return SynthesisRequest(
            text="Prueba local.", voice_id="daxter_official", provider_voice_id="daxter_es_jak2",
            output_path=tmp_path / name, emotion=emotion, intensity="media",
            voice_profile_id="daxter_es_jak2", profile_version="1.0.0",
        )
    first = provider.synthesize(request("first.wav"))
    second = provider.synthesize(request("second.wav"))
    third = provider.synthesize(request("third.wav", "picaro"))
    assert first.success and not first.cache_hit
    assert second.success and second.cache_hit
    assert third.success and not third.cache_hit
    assert provider.calls == 2


class _Atlas:
    def process(self, text):
        print("La luz 2 se encendió correctamente.")
        return True

    def get_user(self):
        return "REDACTED_f73137d930c3"


class _STT:
    def transcribe(self, source, language_hint=None):
        from voice.stt import STTResult
        return STTResult("Enciende la luz 2", language="es"), {"stt.transcribe": 12.0}


class _Voice:
    def __init__(self):
        self.request = None

    def speak(self, text, **kwargs):
        self.request = (text, kwargs)
        return SynthesisResult(True, Path("answer.wav"), "daxter_official", "fake")

    def stop_current_audio(self): pass
    def clear_queue(self): return 0
    def close(self): pass


class _Recorder:
    def stop(self): pass
    def close(self): pass


def test_manual_turn_reuses_common_stt_personality_and_tts_without_continuous_listening(tmp_path):
    voice = _Voice()
    session = ManualVoiceSession(
        atlas=_Atlas(), recorder=_Recorder(), stt=_STT(), voice_service=voice, work_dir=tmp_path
    )
    result = session.process_recording(tmp_path / "input.wav", recording_ms=25)
    assert result.transcript == "Enciende la luz 2"
    assert "2" in result.response
    assert result.synthesis and result.synthesis.success
    assert result.spoken_response == result.response
    assert set(result.timings_ms) >= {"recording", "stt.transcribe", "atlas", "personality", "tts_and_playback", "total"}
    assert voice.request[1]["emotion"] in {"emocionado", "neutral"}


def test_manual_turn_keeps_session_alive_after_empty_audio(tmp_path):
    class EmptySTT:
        def transcribe(self, *_args, **_kwargs):
            raise STTError("audio_empty", "empty")

    session = ManualVoiceSession(
        atlas=_Atlas(), recorder=_Recorder(), stt=EmptySTT(),
        voice_service=_Voice(), work_dir=tmp_path,
    )
    result = session.process_recording(tmp_path / "empty.wav")
    assert result.continue_running is True
    assert result.recoverable_error == "audio_empty"
    assert "vuelve a intentarlo" in result.response


def test_spoken_text_is_complete_and_removes_visual_only_content():
    visible = "\U0001f680 Resultado completo. Segundo dato. Tercer dato. Cuarto dato. `codigo` C:\\privado\\dato.txt"
    spoken = SpeechTextNormalizer.normalize(visible)
    assert "\U0001f680" not in spoken
    assert "C:\\" not in spoken
    assert "Cuarto" in spoken
    assert "consola" not in spoken.casefold()
    assert visible.startswith("\U0001f680")


def test_contextual_transcript_correction_never_invents_home_action():
    safe = ContextualTranscriptNormalizer.normalize(
        STTResult("Daxter, cuentame un ciste", confidence=STTConfidence.HIGH)
    )
    ambiguous = ContextualTranscriptNormalizer.normalize(
        STTResult("tiene la luz del acuario pequeno", confidence=STTConfidence.HIGH)
    )
    assert safe.text == "cuentame un chiste"
    assert ambiguous.text == "tiene la luz del acuario pequeno"
