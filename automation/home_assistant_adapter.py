"""Adaptador seguro entre Atlas y Home Assistant."""

from __future__ import annotations

from typing import Any
import time

from automation.home_assistant_client import HomeAssistantTransport
from automation.home_assistant_models import HomeEntityKind, HomeEntityState
from automation.home_device_registry import HomeDeviceRegistry


class HomeAssistantPolicyError(PermissionError):
    pass


class HomeAssistantAdapter:
    def __init__(
        self,
        transport: HomeAssistantTransport,
        registry: HomeDeviceRegistry,
    ) -> None:
        self.transport = transport
        self.registry = registry

    def health(self) -> dict[str, Any]:
        return {
            "available": bool(self.transport.ping()),
            "registered_entities": self.registry.count,
        }

    def get_state(self, entity_id: str) -> dict[str, Any]:
        entity = self.registry.get(entity_id)
        entity.validate()
        return self.transport.get_state(entity.entity_id).to_dict()

    def turn_on(
        self,
        entity_id: str,
        *,
        service_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._write(entity_id, "turn_on", service_data)

    def turn_off(
        self,
        entity_id: str,
        *,
        service_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._write(entity_id, "turn_off", service_data)

    def _write(
        self,
        entity_id: str,
        service: str,
        service_data: dict[str, Any] | None,
    ) -> dict[str, Any]:
        entity = self.registry.get(entity_id)
        entity.validate()
        if entity.kind == HomeEntityKind.SENSOR:
            raise HomeAssistantPolicyError(
                "Los sensores son entidades de solo lectura."
            )
        if service not in entity.allowed_services:
            raise HomeAssistantPolicyError(
                f"El servicio '{service}' no está autorizado para '{entity_id}'."
            )
        state: HomeEntityState = self.transport.call_service(
            entity.domain,
            service,
            entity_id=entity.entity_id,
            data=service_data,
        )
        expected = "on" if service == "turn_on" else "off"
        last_state = state
        for attempt in range(3):
            try:
                last_state = self.transport.get_state(entity.entity_id)
            except Exception:
                if attempt == 2:
                    raise
            else:
                if str(last_state.state).strip().casefold() == expected:
                    return last_state.to_dict()
            if attempt < 2:
                time.sleep(0.2)
        raise RuntimeError(
            "He enviado la orden, pero el dispositivo sigue apareciendo "
            + ("apagado." if expected == "on" else "encendido.")
        )

    @staticmethod
    def _schedule_id(entity_id: str) -> str:
        return "atlas_" + entity_id.replace(".", "_").replace("-", "_")

    def schedule_switch(
        self,
        *,
        entity_id: str,
        start_time: str,
        end_time: str,
    ) -> dict[str, Any]:
        entity = self.registry.get(entity_id)
        entity.validate()
        return self.transport.create_or_update_time_automation(
            automation_id=self._schedule_id(entity_id),
            alias=f"Atlas · Horario · {entity_id}",
            entity_id=entity_id,
            start_time=start_time,
            end_time=end_time,
            enabled=True,
        )

    def enable_schedule(self, *, entity_id: str) -> dict[str, Any]:
        entity = self.registry.get(entity_id)
        entity.validate()
        return self.transport.set_automation_enabled(
            self._schedule_id(entity_id),
            True,
        ).to_dict()

    def disable_schedule(self, *, entity_id: str) -> dict[str, Any]:
        entity = self.registry.get(entity_id)
        entity.validate()
        return self.transport.set_automation_enabled(
            self._schedule_id(entity_id),
            False,
        ).to_dict()

    def turn_on_for_duration(
        self,
        *,
        entity_id: str,
        duration_minutes: int,
    ) -> dict[str, Any]:
        if duration_minutes <= 0:
            raise ValueError("duration_minutes debe ser mayor que cero.")

        entity = self.registry.get(entity_id)
        entity.validate()

        turned_on = self.turn_on(entity_id)
        timer_id = (
            "atlas_timer_"
            + entity_id.replace(".", "_").replace("-", "_")
        )
        timer_result = self.transport.create_one_shot_turn_off_automation(
            automation_id=timer_id,
            alias=f"Atlas · Temporizador · {entity_id}",
            entity_id=entity_id,
            delay_minutes=duration_minutes,
        )
        return {
            "turned_on": turned_on,
            "timer": timer_result,
        }

