"""
Servicio de ejecución conversacional para Home Assistant.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from automation.home_intent_resolver import (
    HomeIntentResolver,
    HomeIntentType,
)
from automation.stage_e_runtime import StageEEnvironment


@dataclass(slots=True)
class HomeIntentResponse:
    handled: bool
    message: str = ""
    requires_confirmation: bool = False
    automation_id: str | None = None
    raw_result: Any = None


class HomeIntentService:
    def __init__(
        self,
        environment: StageEEnvironment,
        resolver: HomeIntentResolver | None = None,
    ) -> None:
        self.environment = environment
        self.resolver = resolver or HomeIntentResolver()

    def handle(
        self,
        text: str,
        *,
        user_id: str,
        channel: str,
        confirmed: bool = False,
    ) -> HomeIntentResponse:
        intent = self.resolver.resolve(text)

        if intent is None:
            return HomeIntentResponse(handled=False)

        automation = self.environment.manager.create(
            action_id=intent.action_id,
            owner_user_id=user_id,
            creator_user_id=user_id,
            parameters=intent.parameters,
        )

        result = self.environment.manager.execute(
            automation.automation_id,
            requested_by_user_id=user_id,
            channel=channel,
            confirmed=confirmed,
        )

        if result.error_code == "confirmation_required":
            return HomeIntentResponse(
                handled=True,
                message=(
                    "Esta acción necesita confirmación. "
                    "Confirma que quieres controlar el enchufe virtual."
                ),
                requires_confirmation=True,
                automation_id=automation.automation_id,
                raw_result=result,
            )

        if not result.success:
            return HomeIntentResponse(
                handled=True,
                message=(
                    result.error_message
                    or "No he podido completar la acción doméstica."
                ),
                automation_id=automation.automation_id,
                raw_result=result,
            )

        message = self._success_message(
            intent.intent_type,
            result.result,
        )

        return HomeIntentResponse(
            handled=True,
            message=message,
            automation_id=automation.automation_id,
            raw_result=result,
        )

    @staticmethod
    def _success_message(
        intent_type: HomeIntentType,
        result: dict,
    ) -> str:
        if intent_type == HomeIntentType.TURN_ON_LIGHT:
            return "He encendido la luz virtual."

        if intent_type == HomeIntentType.TURN_OFF_LIGHT:
            return "He apagado la luz virtual."

        if intent_type == HomeIntentType.READ_TEMPERATURE:
            state = result.get("state", "desconocida")
            unit = result.get("attributes", {}).get(
                "unit_of_measurement",
                "°C",
            )
            return f"El sensor virtual marca {state} {unit}."

        if intent_type == HomeIntentType.TURN_ON_SWITCH:
            return "He encendido el enchufe virtual."

        if intent_type == HomeIntentType.TURN_OFF_SWITCH:
            return "He apagado el enchufe virtual."

        return "Acción doméstica completada."