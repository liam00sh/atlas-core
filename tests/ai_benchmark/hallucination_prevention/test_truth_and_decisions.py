import pytest

from core.decisions import AtlasDecision, DecisionResponseComposer, DecisionStatus
from knowledge.truth import TruthClaim, TruthResolver, TruthSource


def test_verified_relationship_beats_model_inference():
    result = TruthResolver().resolve([
        TruthClaim("Vega", "relationship:Alex", "cousin", TruthSource.MODEL_INFERENCE),
        TruthClaim("Vega", "relationship:Alex", "partner", TruthSource.VERIFIED_PERSONAL, verified=True),
    ])
    assert result.sufficient is True
    assert result.claim.value == "partner"


def test_inference_alone_is_not_sufficient_truth():
    result = TruthResolver().resolve([
        TruthClaim("Alex", "location", "Madrid", TruthSource.MODEL_INFERENCE),
    ])
    assert result.sufficient is False
    assert result.reason == "inference_only"


def test_action_cannot_be_executed_without_authorization():
    with pytest.raises(ValueError):
        AtlasDecision("home.light.turn_off", DecisionStatus.EXECUTED, authorized=False, executed=True)


def test_personality_cannot_turn_pending_action_into_success():
    decision = AtlasDecision(
        "home.light.turn_off",
        DecisionStatus.PENDING,
        authorized=True,
        executed=False,
        reason="falta confirmación",
    )
    response = DecisionResponseComposer.compose(decision, assistant_name="Daxter")
    assert "aún no se ha realizado" in response
    assert "falta confirmación" in response

