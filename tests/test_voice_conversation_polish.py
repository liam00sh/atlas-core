from voice.conversation_state import VoiceConfirmationState, VoiceConversationMemory
from voice.segmentation import split_for_speech
from voice.stt import STTConfidence, STTResult
from voice.stt_policy import STTDecisionKind, STTInputPolicy
from voice.text_normalizer import ContextualTranscriptNormalizer, SpeechTextNormalizer


def test_normal_speech_keeps_complete_response():
    text = "Primera frase. Segunda frase. Tercera frase con el final importante."
    assert SpeechTextNormalizer.normalize(text) == text
    assert "consola" not in SpeechTextNormalizer.normalize(text).casefold()


def test_medium_innocuous_conversation_is_processed():
    decision = STTInputPolicy().evaluate(
        STTResult("qué tiempo hace", confidence=STTConfidence.MEDIUM)
    )
    assert decision.kind is STTDecisionKind.PROCESS


def test_medium_sensitive_command_requires_transcript_confirmation():
    decision = STTInputPolicy().evaluate(
        STTResult("apaga la luz", confidence=STTConfidence.MEDIUM)
    )
    assert decision.kind is STTDecisionKind.CONFIRM


def test_long_speech_splits_at_natural_boundaries():
    text = "Uno es breve. " + "Dos tiene contenido suficiente, pero conserva la coma; " * 8 + "y termina."
    segments = split_for_speech(text, max_chars=100)
    assert len(segments) > 1
    assert " ".join(segments) == " ".join(text.split())
    assert all(len(segment) <= 100 for segment in segments)


def test_confirmation_states_and_repeat_memory_are_separate():
    assert VoiceConfirmationState.NONE != VoiceConfirmationState.TRANSCRIPT_CONFIRMATION
    assert VoiceConfirmationState.ACTION_CONFIRMATION != VoiceConfirmationState.DANGEROUS_ACTION_CONFIRMATION
    memory = VoiceConversationMemory(last_spoken_response="Respuesta completa.")
    assert memory.public_trace()["last_spoken_response"] == "Respuesta completa."


def test_known_name_is_corrected_only_in_explicit_social_context():
    contextual = ContextualTranscriptNormalizer.normalize(
        STTResult("saluda a Nubia"), known_names=("Nuria",)
    )
    unrelated = ContextualTranscriptNormalizer.normalize(
        STTResult("Nubia aparece en el mapa"), known_names=("Nuria",)
    )
    assert contextual.text == "saluda a Nuria"
    assert unrelated.text == "Nubia aparece en el mapa"


def test_repeat_user_uses_previous_turn_not_repeat_command():
    from voice.end_to_end import ManualVoiceSession

    session = object.__new__(ManualVoiceSession)
    session.memory = VoiceConversationMemory(last_spoken_response="Respuesta anterior.")
    repeated = session._repeat_response(
        "repite lo que he dicho",
        previous_raw="saluda a Nubia",
        previous_normalized="saluda a Nuria",
    )
    assert repeated == "He oído: saluda a Nubia. He interpretado: saluda a Nuria."
