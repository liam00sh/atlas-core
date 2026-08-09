import pytest

from ai.models.roles import ModelRole
from ai.routing.router import AIRouter, RoutingRequest


def test_simple_greeting_uses_fast():
    decision = AIRouter().route(RoutingRequest("Hola", intent="greeting"))
    assert decision.role is ModelRole.FAST


def test_spanish_article_el_is_not_treated_as_a_pronoun_reference():
    decision = AIRouter().route(RoutingRequest("Explica el resultado", intent="conversation"))
    assert decision.role is ModelRole.FAST


def test_context_memory_ambiguity_uses_reasoning():
    decision = AIRouter().route(RoutingRequest(
        "¿Y ella dónde estaba antes?",
        context_messages=4,
        memory_required=True,
        temporal_reasoning=True,
    ))
    assert decision.role is ModelRole.REASONING
    assert {"context", "memory", "temporal"}.issubset(decision.reasons)


def test_contradiction_or_large_context_starts_deep():
    decision = AIRouter().route(RoutingRequest(
        "Analiza estas fuentes contradictorias",
        context_messages=10,
        retrieved_items=12,
        has_contradictions=True,
    ))
    assert decision.role is ModelRole.DEEP


@pytest.mark.parametrize("role", ["fast", "reasoning", "deep"])
def test_manual_override(role):
    decision = AIRouter(override=role).route(RoutingRequest("cualquier texto"))
    assert decision.role.value == role
    assert decision.overridden is True
