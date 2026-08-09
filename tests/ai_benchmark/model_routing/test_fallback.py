from ai.models.roles import ModelRole, ModelRoleRegistry
from ai.routing.router import AIRouter, RoutingRequest
from ai.routing.runtime import AIModelRuntime
from ai.routing.validator import ValidationContext

from tests.ai_benchmark.conftest import FakeProvider


def runtime(answers):
    providers = {
        ModelRole.FAST: FakeProvider("fast-test", list(answers[0])),
        ModelRole.REASONING: FakeProvider("reasoning-test", list(answers[1])),
        ModelRole.DEEP: FakeProvider("deep-test", list(answers[2])),
    }
    return AIModelRuntime(providers=providers, registry=ModelRoleRegistry(), router=AIRouter())


def test_empty_fast_response_escalates_only_to_reasoning():
    result, _ = runtime((("",), ("Respuesta suficiente",), ("no usado",))).generate(
        "prompt",
        RoutingRequest("Explícame esto"),
        ValidationContext("Explícame esto"),
    )
    assert result.initial_role is ModelRole.FAST
    assert result.final_role is ModelRole.REASONING
    assert result.fallback is True
    assert result.attempts == ("fast", "reasoning")


def test_missing_information_does_not_authorize_bigger_model_to_invent():
    result, _ = runtime((("REDACTED_2c7b6821719d está en Madrid",), ("inventado",), ("inventado",))).generate(
        "prompt",
        RoutingRequest("¿Dónde está REDACTED_2c7b6821719d?"),
        ValidationContext("¿Dónde está REDACTED_2c7b6821719d?", missing_required_data=True),
    )
    assert result.attempts == ("fast",)
    assert result.validation == "missing_information"
    assert "información suficiente" in result.response


def test_complex_request_starts_deep_without_running_all_models():
    result, _ = runtime((("fast",), ("reasoning",), ("deep",))).generate(
        "prompt",
        RoutingRequest("contradicciones", has_contradictions=True),
        ValidationContext("contradicciones"),
    )
    assert result.attempts == ("deep",)
    assert result.response == "deep"

