from ai.models.roles import ModelRole
from ai.routing.router import AIRouter, RoutingRequest


def test_direct_resolved_command_uses_fast_for_natural_wording():
    decision = AIRouter().route(RoutingRequest(
        "Confirma que está listo",
        intent="confirmation",
        deterministic_possible=True,
    ))
    assert decision.role is ModelRole.FAST
