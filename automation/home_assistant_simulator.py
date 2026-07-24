"""Simulador local y determinista de Home Assistant para la Etapa E."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from automation.home_assistant_client import BaseHomeAssistantClient
from automation.home_assistant_models import HomeEntityState, HomeServiceCall


class HomeAssistantSimulationError(RuntimeError):
    pass


class HomeAssistantSimulator(BaseHomeAssistantClient):
    """Imita el subconjunto seguro de la API que utilizará Atlas."""

    def __init__(
        self,
        initial_states: dict[str, HomeEntityState] | None = None,
    ) -> None:
        self._states = initial_states or {}
        self.calls: list[HomeServiceCall] = []

    def is_available(self) -> bool:
        return True

    def register_state(self, state: HomeEntityState) -> None:
        self._states[state.entity_id] = deepcopy(state)

    def get_state(self, entity_id: str) -> HomeEntityState:
        try:
            return deepcopy(self._states[entity_id])
        except KeyError as exc:
            raise HomeAssistantSimulationError(
                f"La entidad simulada '{entity_id}' no existe."
            ) from exc

    def call_service(
        self,
        domain: str,
        service: str,
        *,
        entity_id: str,
        data: dict[str, Any] | None = None,
    ) -> HomeEntityState:
        payload = dict(data or {})
        self.calls.append(
            HomeServiceCall(
                domain=domain,
                service=service,
                entity_id=entity_id,
                data=payload,
            )
        )
        state = self.get_state(entity_id)
        if domain not in {"light", "switch"}:
            raise HomeAssistantSimulationError(
                f"El dominio '{domain}' no admite escritura en el laboratorio."
            )
        if service not in {"turn_on", "turn_off"}:
            raise HomeAssistantSimulationError(
                f"El servicio '{service}' no está permitido."
            )
        if entity_id.split(".", 1)[0] != domain:
            raise HomeAssistantSimulationError(
                "El dominio del servicio no coincide con la entidad."
            )
        state.state = "on" if service == "turn_on" else "off"
        state.attributes.update(payload)
        self._states[entity_id] = deepcopy(state)
        return deepcopy(state)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {
            entity_id: state.to_dict()
            for entity_id, state in sorted(self._states.items())
        }
