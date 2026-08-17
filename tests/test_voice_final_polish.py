from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import json
import sys

from ai.prompts.system_prompt import BASE_SYSTEM_PROMPT
from automation.home_intent_resolver import HomeIntentResolver
from automation.home_intent_service import HomeIntentService
from conversation.daxter_personality import PersonalityStrength
from conversation.response_pipeline import DaxterResponsePipeline
from tools.chatterbox_worker import _split_tts_units, generation_controls
from voice.models import AssistantIdentity, SynthesisRequest, SynthesisResult
from voice.providers.chatterbox_daxter_provider import ChatterboxDaxterProvider
from voice.providers.chatterbox_style_adapter import ChatterboxStyleAdapter
from voice.stt import STTConfidence, STTResult, contextual_hotwords
from voice.stt_policy import STTDecisionKind, STTInputPolicy, STTIntentContext
from voice.text_normalizer import ContextualTranscriptNormalizer, SpeechTextNormalizer
from voice.service import VoiceService


def test_spoken_summary_uses_complete_content_sentence_and_explicit_closure():
    visible = (
        "Primera idea completa. Segunda idea completa. "
        "Tercera idea completa. Cuarta idea completa."
    )
    spoken = SpeechTextNormalizer.normalize(visible, max_sentences=2)
    assert spoken == "Primera idea completa. Te muestro el resto en la consola."
    assert spoken.endswith(".")
    assert "Segunda" not in spoken


def test_excessive_single_sentence_is_not_cut_at_an_arbitrary_character():
    visible = "Una " + ("explicación muy extensa " * 30)
    spoken = SpeechTextNormalizer.normalize(visible, max_chars=180)
    assert spoken == "La respuesta completa es extensa. Te muestro los detalles en la consola."


def test_confirmation_context_repairs_phonetic_cancel_only_inside_pending_gate():
    raw = STTResult("Cancillerum", confidence=STTConfidence.LOW)
    outside = ContextualTranscriptNormalizer.normalize(raw)
    inside = ContextualTranscriptNormalizer.normalize(raw, pending_confirmation=True)
    assert outside.text == "Cancillerum"
    assert outside.confidence is STTConfidence.LOW
    assert inside.text == "cancelar"
    assert inside.confidence is STTConfidence.HIGH
    decision = STTInputPolicy().evaluate(
        inside,
        STTIntentContext(pending_confirmation=True),
    )
    assert decision.kind is STTDecisionKind.PROCESS


def test_context_hotwords_are_narrow_and_do_not_mix_unrelated_domains():
    confirmation = contextual_hotwords("confirmation")
    home = contextual_hotwords("home_assistant")
    reminder = contextual_hotwords("reminder")
    assert "cancelar" in confirmation and "acuario" not in confirmation
    assert "acuario" in home and "cancelado" not in home
    assert "recuérdame" in reminder and "Docker" not in reminder


def test_home_entity_without_action_requests_clarification_and_never_invents_verb():
    resolver = HomeIntentResolver()
    assert resolver.resolve("La luz del acuario pequeño") is None
    assert resolver.resolve("Haga la luz del acuario pequeño") is None
    assert resolver.clarification_for("La luz del acuario pequeño") == (
        "¿Quieres que la encienda o la apague?"
    )


def test_home_service_returns_ambiguity_before_any_environment_action():
    class Resolver:
        def resolve(self, _text):
            return None

        def clarification_for(self, _text):
            return "¿Quieres que la encienda o la apague?"

    service = HomeIntentService(SimpleNamespace(), resolver=Resolver())
    result = service.handle(
        "La luz del acuario pequeño",
        user_id="owner",
        channel="pc_voice",
    )
    assert result.handled is True
    assert result.message == "¿Quieres que la encienda o la apague?"


def test_pc_voice_personality_is_present_but_reduced():
    result = DaxterResponsePipeline().adapt(
        "La operación ha terminado correctamente.",
        channel="pc_voice",
        request_text="Comprueba el estado.",
    )
    assert result.personality_strength == PersonalityStrength.LOW.value
    assert len(result.styled_text) <= 320


def test_prompt_explicitly_forbids_shared_fictional_past():
    assert '"cuando hicimos"' in BASE_SYSTEM_PROMPT
    assert "No atribuyas al usuario" in BASE_SYSTEM_PROMPT


def test_spanish_accents_are_preserved_and_clock_seconds_are_not_spoken():
    value = ChatterboxStyleAdapter.normalize_text(
        "La función está activa mañana a las 22:12."
    )
    assert "función" in value
    assert "está" in value
    assert "mañana" in value
    assert "veintidós y doce" in value
    assert "22:12" not in value


def test_worker_splits_long_text_into_bounded_ordered_units():
    text = (
        "Primera frase completa. "
        "Segunda frase con una explicación, un detalle adicional, y un cierre completo. "
        "Tercera frase completa."
    )
    units = _split_tts_units(text, max_chars=55)
    assert len(units) >= 3
    assert all(len(item) <= 55 for item in units)
    assert units[0] == "Primera frase completa."
    assert units[-1] == "Tercera frase completa."


def test_es_es_worker_uses_frozen_human_winner_controls():
    controls = {
        "language_id": "other", "exaggeration": 0.9, "cfg_weight": 0.9,
        "temperature": 0.2, "repetition_penalty": 2.0, "min_p": 0.05, "top_p": 1.0,
    }
    selected = generation_controls(controls, "reference.wav", candidate="es_es")
    assert selected == {
        "language_id": "es", "audio_prompt_path": "reference.wav",
        "exaggeration": 0.45, "cfg_weight": 0.35, "temperature": 0.8,
    }


def test_generation_seed_is_independent_from_trim_and_fade(tmp_path):
    request = SynthesisRequest(
        text="Hola, usuario.",
        voice_id="daxter_official",
        provider_voice_id="daxter_es_jak2",
        output_path=tmp_path / "one.wav",
        voice_profile_id="daxter_es_jak2",
        profile_version="1.0.0",
    )
    seed = ChatterboxDaxterProvider._generation_seed(request)
    changed_output = SynthesisRequest(
        text=request.text,
        voice_id=request.voice_id,
        provider_voice_id=request.provider_voice_id,
        output_path=tmp_path / "two.wav",
        voice_profile_id=request.voice_profile_id,
        profile_version=request.profile_version,
    )
    assert ChatterboxDaxterProvider._generation_seed(changed_output) == seed


def test_es_es_provider_requires_local_source_and_model_and_separates_cache(tmp_path):
    reference = tmp_path / "reference.wav"
    reference.write_bytes(b"RIFF")
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps({"profile_id": "daxter_es_jak2", "version": "1.0.0", "reference_file": "private.wav"}), encoding="utf-8")
    catalog = tmp_path / "catalog.json"; catalog.write_text("{}", encoding="utf-8")
    worker = [sys.executable, str(Path(__file__).resolve().parents[1] / "tools" / "chatterbox_worker.py")]
    missing = ChatterboxDaxterProvider(
        candidate="es_es", profile_path=profile, catalog_path=catalog,
        reference_path=reference, worker_command=worker,
        cache_dir=tmp_path / "cache",
    )
    assert missing.is_available() is False
    source, model = tmp_path / "source", tmp_path / "model"
    source.mkdir(); model.mkdir()
    selected = ChatterboxDaxterProvider(
        candidate="es_es", source_path=source, model_dir=model,
        profile_path=profile, catalog_path=catalog, reference_path=reference,
        worker_command=worker, cache_dir=tmp_path / "cache",
    )
    request = SynthesisRequest(
        text="Prueba local.", voice_id="daxter_official", provider_voice_id="daxter_es_jak2",
        output_path=tmp_path / "output.wav", voice_profile_id="daxter_es_jak2",
        profile_version="1.0.0",
    )
    general = ChatterboxDaxterProvider(
        profile_path=profile, catalog_path=catalog, reference_path=reference,
        worker_command=worker, cache_dir=tmp_path / "cache",
    )
    assert selected.is_available() is True
    assert selected.health()["candidate"] == "es_es"
    assert selected._cache_key(request) != general._cache_key(request)


def test_final_lab_definition_is_capped_at_forty_and_has_every_required_folder():
    from tools.generate_voice_final_polish_lab import _samples

    samples = _samples()
    assert len(samples) == 40
    assert {str(item["folder"]) for item in samples} == {
        "pronunciation_es", "english_terms", "trim_fade", "long_sentences", "names",
    }


def test_voice_service_exposes_synthesis_and_blocking_playback_completion(tmp_path):
    class Provider:
        provider_id = "kokoro"

        def is_available(self):
            return True

        def supports_voice(self, voice_id):
            return voice_id == "em_alex"

        def synthesize(self, request):
            request.output_path.parent.mkdir(parents=True, exist_ok=True)
            request.output_path.write_bytes(b"placeholder")
            return SynthesisResult(
                True,
                request.output_path,
                request.voice_id,
                self.provider_id,
                chars_sent_to_tts=len(request.text),
                chars_synthesized=len(request.text),
                synthesized_samples=24000,
                wav_duration_ms=1000.0,
            )

    class Player:
        last_playback_duration_ms = 1004.0
        last_playback_completed = True
        last_playback_interrupted = False

        def is_available(self):
            return True

        def play(self, _path):
            return True

    timings = {}
    result = VoiceService(
        provider=Provider(), player=Player(), output_dir=tmp_path
    ).speak(
        "Respuesta completa.",
        identity=AssistantIdentity.DAXTER,
        requested_voice_id="daxter_alex",
        timings=timings,
    )
    assert result.chars_synthesized == len("Respuesta completa.")
    assert result.synthesized_samples == 24000
    assert result.wav_duration_ms == 1000.0
    assert result.playback_completed is True
    assert result.playback_interrupted is False
    assert timings["playback_completed"] is True
