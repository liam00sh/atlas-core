from tools.run_stt_human_battery import inspect_router_only
from tools.evaluate_stt_conversation_battery import evaluate


def test_router_only_classifies_without_executor():
    observed = inspect_router_only("Enciende la luz del acuario pequeño")
    assert observed.intent == "home.turn_on"
    assert observed.safe_action is True
    assert not hasattr(observed, "execute")


def test_evaluator_separates_raw_and_normalized_wer():
    row = {
        "category": "people", "expected_text": "Saluda a persona conocida", "raw_transcript": "Saluda a persona conicida",
        "normalized_transcript": "Saluda a persona conocida", "expected_intent": "people.greet", "observed_intent": "people.greet",
        "expected_entity": "persona conocida", "observed_entity": "persona conocida", "command_expected": "False",
        "command_observed": "False", "safe_action_expected": "False", "safe_action_observed": "False",
    }
    report = evaluate([row])
    assert report["wer"] > 0
    assert report["normalized_wer"] == 0
