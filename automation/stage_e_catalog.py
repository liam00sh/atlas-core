"""Catálogo cerrado de acciones de la Etapa E."""

from __future__ import annotations

from automation.home_assistant_adapter import HomeAssistantAdapter
from automation.models import (
    ActionDefinition,
    AutomationRisk,
    ConfirmationLevel,
)


def build_stage_e_actions(
    adapter: HomeAssistantAdapter,
) -> list[ActionDefinition]:
    def health(_: dict):
        return adapter.health()

    def read_state(parameters: dict):
        return adapter.get_state(parameters["entity_id"])

    def turn_on(parameters: dict):
        return adapter.turn_on(
            parameters["entity_id"],
            service_data=parameters.get("service_data"),
        )

    def turn_off(parameters: dict):
        return adapter.turn_off(
            parameters["entity_id"],
            service_data=parameters.get("service_data"),
        )

    return [
        ActionDefinition(
            action_id="home.health",
            name="Comprobar Home Assistant",
            description="Comprueba la disponibilidad del laboratorio.",
            handler=health,
            required_permission="home.read",
            allowed_parameters=frozenset(),
        ),
        ActionDefinition(
            action_id="home.state.read",
            name="Leer entidad doméstica",
            description="Lee una entidad registrada en el catálogo cerrado.",
            handler=read_state,
            required_permission="home.read",
            allowed_parameters=frozenset({"entity_id"}),
        ),
        ActionDefinition(
            action_id="home.light.turn_on",
            name="Encender luz",
            description="Enciende una luz autorizada.",
            handler=turn_on,
            required_permission="home.control.light",
            risk=AutomationRisk.SAFE,
            confirmation=ConfirmationLevel.NONE,
            allowed_parameters=frozenset({"entity_id", "service_data"}),
        ),
        ActionDefinition(
            action_id="home.light.turn_off",
            name="Apagar luz",
            description="Apaga una luz autorizada.",
            handler=turn_off,
            required_permission="home.control.light",
            risk=AutomationRisk.SAFE,
            confirmation=ConfirmationLevel.NONE,
            allowed_parameters=frozenset({"entity_id", "service_data"}),
        ),
        ActionDefinition(
            action_id="home.switch.turn_on",
            name="Encender enchufe",
            description="Enciende un enchufe autorizado.",
            handler=turn_on,
            required_permission="home.control.switch",
            risk=AutomationRisk.SENSITIVE,
            confirmation=ConfirmationLevel.NONE,
            allowed_parameters=frozenset({"entity_id", "service_data"}),
        ),
        ActionDefinition(
            action_id="home.switch.turn_off",
            name="Apagar enchufe",
            description="Apaga un enchufe autorizado.",
            handler=turn_off,
            required_permission="home.control.switch",
            risk=AutomationRisk.SENSITIVE,
            confirmation=ConfirmationLevel.NONE,
            allowed_parameters=frozenset({"entity_id", "service_data"}),
        ),
    ]
