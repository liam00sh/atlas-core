from ai.models.roles import ModelRole
from ai.routing.router import AIRouter, RoutingRequest


def test_personal_memory_with_context_is_not_sent_to_fast():
    decision = AIRouter().route(RoutingRequest(
        "¿Qué te dije antes sobre mi proyecto?",
        context_messages=2,
        memory_required=True,
    ))
    assert decision.role is ModelRole.REASONING

