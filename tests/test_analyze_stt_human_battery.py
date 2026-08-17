from tools.analyze_stt_human_battery import classify_row, semantic_tokens
from tools.run_stt_human_battery import inspect_router_only, plain


def _row(expected, raw, expected_intent, observed_intent, *, entity=""):
    return {
        "id": "1", "category": "test", "expected_text": expected,
        "raw_transcript": raw, "normalized_transcript": raw,
        "expected_intent": expected_intent, "observed_intent": observed_intent,
        "expected_entity": entity, "observed_entity": entity if expected_intent == observed_intent else "",
    }


def test_semantic_numbers_and_token_boundaries_are_innocuous():
    assert semantic_tokens("Persona conocida dos") == semantic_tokens("PersonaConocida2")
    assert semantic_tokens("a las veinte") == semantic_tokens("a las 20")


def test_lexical_error_can_preserve_intent():
    result = classify_row(_row("comprar pan por favor", "comprar pan por sabor", "reminder.create", "reminder.create"))
    assert result["stt_class"] == "lexical_error_intent_preserved"


def test_joint_error_is_not_blured_into_router_only():
    result = classify_row(_row("Cancela la operación", "Cierra la operación", "cancel", "conversation", entity="operación"))
    assert result["functional_class"] == "joint_stt_router_error"


def test_router_accepts_general_suffixes_punctuation_and_numeric_identifiers():
    assert inspect_router_only("Sí, es correcto por favor").intent == "confirmation.accept"
    assert inspect_router_only("¿Qué has entendido? ahora").intent == "repeat.transcript"
    assert inspect_router_only("Presenta a PersonaConocida2 por favor").entity == "persona_conocida_2"
    assert plain("PersonaConocida2") == "persona conocida 2"
