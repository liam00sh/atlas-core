from ai.models.roles import ModelRole
from ai.routing.router import AIRouter, RoutingRequest


def test_previous_message_reference_uses_reasoning():
    decision = AIRouter().route(RoutingRequest(
        "Haz lo mismo con la anterior",
        context_messages=4,
        tools_required=True,
    ))
    assert decision.role is ModelRole.REASONING
    assert "references" in decision.reasons

