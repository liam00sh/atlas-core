"""
Servicio de ejecución conversacional para Home Assistant.
"""

from __future__ import annotations

import random
import re
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
    """Resuelve peticiones domésticas y devuelve respuestas conversacionales."""

    _GUEST_ABSENT_MESSAGES = (
        "Uy, quieta ahí, bandida: la casa todavía no te detecta dentro. "
        "Cuando conste que estás presente, te cuento hasta lo que cotillea el sensor.",
        "El sensor me hace ojitos, pero la casa dice que sigues fuera. "
        "En cuanto detecte tu presencia, te doy el parte térmico sin hacerme el interesante.",
        "Coco ha puesto una patita sobre el botón de seguridad: primero la casa debe saber "
        "que estás dentro y después ya interrogamos al sensor.",
        "Daxter informa: acceso doméstico bloqueado por ausencia sospechosamente oficial. "
        "Que la casa te detecte y volvemos al ataque.",
        "La casa se ha puesto en modo portera cotilla: no abre el panel doméstico hasta "
        "que conste que estás presente.",
        "Ni Daxter ni Coco se fían de controlar la casa a distancia por accidente. "
        "Cuando aparezcas como presente, el sensor canta enseguida.",
    )

    _PERMISSION_DENIED_MESSAGES = (
        "Ese botón lleva capa de superhéroe y permisos especiales. De momento no puedo pulsarlo por ti.",
        "Coco ha revisado el carnet y dice que para esa maniobra faltan permisos domésticos.",
        "Daxter ha intentado colarse por la ventilación, pero esta acción pide permisos que no tienes.",
        "La casa ha levantado una ceja digital: esa acción no está autorizada para tu perfil.",
    )

    _ALREADY_ON_MESSAGES = {
        "daxter": (
            "Eso ya está encendido, colega. Ni yo puedo encender dos veces lo mismo.",
            "Ya estaba funcionando. He llegado tarde a mi propia misión, qué nivel.",
            "Eso ya está encendido; insistir sería hacerle cosquillas al enchufe.",
            "El dispositivo ya está despierto. Esta vez me ahorro pulsar botones.",
            "Ya brilla como debe. Misión completada antes de empezar, muy de mi estilo.",
            "Eso ya estaba encendido. Por una vez, el trabajo se ha hecho solo.",
        ),
        "coco": (
            "Eso ya está encendido. Confirmación científica: no hace falta tocar nada.",
            "Ya estaba funcionando correctamente. Dejemos al botón tranquilo.",
            "El dispositivo ya está activo. Repetir la orden no mejoraría el resultado.",
            "Todo está encendido y estable. Caso resuelto sin intervención adicional.",
            "Ya estaba encendido. He revisado el estado dos veces, por si acaso.",
            "El dispositivo ya está despierto. No hace falta insistirle.",
        ),
    }

    _ALREADY_OFF_MESSAGES = {
        "daxter": (
            "Eso ya está apagado. He intentado apagar la oscuridad, pero no ha colado.",
            "Ya estaba apagado, jefe. El botón puede seguir de vacaciones.",
            "Ese dispositivo ya duerme más profundamente que yo después de una aventura.",
            "Ya estaba apagado. Pulsarlo otra vez sería puro teatro tecnológico.",
            "Cero luces, cero ruido y cero trabajo pendiente. Perfecto.",
            "Eso ya está apagado; me quedo sin excusa para tocar otro botón.",
        ),
        "coco": (
            "Eso ya está apagado. No es necesario repetir la operación.",
            "El dispositivo ya está inactivo y todo permanece estable.",
            "Ya estaba apagado. He comprobado el estado antes de actuar.",
            "No hay nada más que apagar; el sistema ya está en reposo.",
            "El dispositivo ya está desconectado. Operación innecesaria.",
            "Estado confirmado: apagado. Dejemos el botón tranquilo.",
        ),
    }

    def __init__(
        self,
        environment: StageEEnvironment,
        resolver: HomeIntentResolver | None = None,
        random_source: random.Random | None = None,
        assistant_name_provider=None,
    ) -> None:
        self.environment = environment
        self.resolver = resolver or HomeIntentResolver.from_device_registry(
            environment.device_registry
        )
        self._random = random_source or random.SystemRandom()
        self._assistant_name_provider = assistant_name_provider
        self._last_guest_absent_message: str | None = None
        self._last_permission_denied_message: str | None = None
        self._last_already_on_message: str | None = None
        self._last_already_off_message: str | None = None

    def _pick_non_repeating(
        self,
        messages: tuple[str, ...],
        last_message: str | None,
    ) -> str:
        """Elige una frase evitando repetir la inmediatamente anterior."""

        if len(messages) == 1:
            return messages[0]

        candidates = tuple(
            message
            for message in messages
            if message != last_message
        )
        return self._random.choice(candidates or messages)

    def _guest_absent_message(self) -> str:
        message = self._pick_non_repeating(
            self._GUEST_ABSENT_MESSAGES,
            self._last_guest_absent_message,
        )
        self._last_guest_absent_message = message
        return message

    def _permission_denied_message(self) -> str:
        message = self._pick_non_repeating(
            self._PERMISSION_DENIED_MESSAGES,
            self._last_permission_denied_message,
        )
        self._last_permission_denied_message = message
        return message

    def _guest_presence_is_not_verified(self, user_id: str) -> bool:
        """Aplica denegación segura si la presencia doméstica falla o no consta."""

        try:
            return self.environment.is_guest(
                user_id
            ) and not self.environment.is_guest_present(user_id)
        except Exception:
            return True

    def _assistant_key(self) -> str:
        name = ""
        if callable(self._assistant_name_provider):
            try:
                name = str(self._assistant_name_provider())
            except Exception:
                name = ""
        normalized = name.strip().casefold()
        return "coco" if normalized == "coco" else "daxter"

    def _already_on_message(self) -> str:
        messages = self._ALREADY_ON_MESSAGES[self._assistant_key()]
        message = self._pick_non_repeating(
            messages,
            self._last_already_on_message,
        )
        self._last_already_on_message = message
        return message

    def _already_off_message(self) -> str:
        messages = self._ALREADY_OFF_MESSAGES[self._assistant_key()]
        message = self._pick_non_repeating(
            messages,
            self._last_already_off_message,
        )
        self._last_already_off_message = message
        return message

    def _redundant_state_message(
        self,
        intent_type: HomeIntentType,
        entity_id: str,
    ) -> str | None:
        # Las lecturas previas pueden estar obsoletas: una orden explícita e
        # idempotente se envía siempre y se verifica después en el adaptador.
        if intent_type in (
            HomeIntentType.TURN_OFF_LIGHT,
            HomeIntentType.TURN_OFF_SWITCH,
            HomeIntentType.TURN_ON_LIGHT,
            HomeIntentType.TURN_ON_SWITCH,
        ):
            return None
        return None

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
            clarification = self.resolver.clarification_for(text)
            if clarification:
                return HomeIntentResponse(handled=True, message=clarification)
            return HomeIntentResponse(handled=False)



        if intent.intent_type == HomeIntentType.TURN_ON_FOR_DURATION:
            entity_id = intent.parameters["entity_id"]
            duration_minutes = int(intent.parameters["duration_minutes"])

            try:
                self.environment.adapter.turn_on_for_duration(
                    entity_id=entity_id,
                    duration_minutes=duration_minutes,
                )
            except Exception as exc:
                return HomeIntentResponse(
                    handled=True,
                    message=(
                        "No he podido iniciar el temporizador en Home Assistant. "
                        f"Detalle técnico: {exc}"
                    ),
                )

            target_name = (
                "la luz del acuario pequeño"
                if "acuario_pequeno" in entity_id
                else "la luz del acuario grande"
            )
            return HomeIntentResponse(
                handled=True,
                message=(
                    f"He encendido {target_name} durante "
                    f"{duration_minutes} minutos."
                ),
            )

        if intent.intent_type in (
            HomeIntentType.SCHEDULE_SWITCH,
            HomeIntentType.ENABLE_SCHEDULE,
            HomeIntentType.DISABLE_SCHEDULE,
        ):
            entity_id = intent.parameters["entity_id"]

            try:
                if intent.intent_type == HomeIntentType.SCHEDULE_SWITCH:
                    self.environment.adapter.schedule_switch(
                        entity_id=entity_id,
                        start_time=intent.parameters["start_time"],
                        end_time=intent.parameters["end_time"],
                    )
                    return HomeIntentResponse(
                        handled=True,
                        message=(
                            "He programado la luz "
                            + (
                                "del acuario pequeño"
                                if "acuario_pequeno" in entity_id
                                else "del acuario grande"
                            )
                            + " para encenderse a las "
                            + intent.parameters["start_time"][:5]
                            + " y apagarse a las "
                            + intent.parameters["end_time"][:5]
                            + "."
                        ),
                    )

                if intent.intent_type == HomeIntentType.ENABLE_SCHEDULE:
                    self.environment.adapter.enable_schedule(entity_id=entity_id)
                    return HomeIntentResponse(
                        handled=True,
                        message="He activado el horario del acuario.",
                    )

                self.environment.adapter.disable_schedule(entity_id=entity_id)
                return HomeIntentResponse(
                    handled=True,
                    message="He desactivado la programación de la luz.",
                )
            except Exception as exc:
                return HomeIntentResponse(
                    handled=True,
                    message=(
                        "No he podido guardar el horario en Home Assistant. "
                        f"Detalle técnico: {exc}"
                    ),
                )

        if intent.intent_type in (
            HomeIntentType.TURN_ON_GROUP,
            HomeIntentType.TURN_OFF_GROUP,
        ):
            entity_ids = tuple(
                item
                for item in intent.parameters.get("entity_ids", "").split("|")
                if item
            )
            if not entity_ids:
                return HomeIntentResponse(
                    handled=True,
                    message="No hay dispositivos autorizados en ese grupo.",
                )

            normalized_user_id = self.environment.normalize_user_id(user_id)
            if self._guest_presence_is_not_verified(normalized_user_id):
                return HomeIntentResponse(
                    handled=True,
                    message=self._guest_absent_message(),
                )

            results = []
            changed = 0
            already_in_target_state = 0

            for entity_id in entity_ids:
                redundant_message = self._redundant_state_message(
                    HomeIntentType.TURN_ON_SWITCH
                    if intent.intent_type == HomeIntentType.TURN_ON_GROUP
                    else HomeIntentType.TURN_OFF_SWITCH,
                    entity_id,
                )
                if redundant_message is not None:
                    already_in_target_state += 1
                    continue

                try:
                    automation = self.environment.manager.create(
                        action_id=intent.action_id,
                        owner_user_id=user_id,
                        creator_user_id=user_id,
                        parameters={"entity_id": entity_id},
                    )
                except PermissionError:
                    return HomeIntentResponse(
                        handled=True,
                        message=self._permission_denied_message(),
                    )

                result = self.environment.manager.execute(
                    automation.automation_id,
                    requested_by_user_id=user_id,
                    channel=channel,
                    confirmed=confirmed,
                )
                results.append(result)

                if result.error_code == "confirmation_required":
                    return HomeIntentResponse(
                        handled=True,
                        message=(
                            "Esta acción necesita confirmación. "
                            "Confirma que quieres controlar este dispositivo doméstico."
                        ),
                        requires_confirmation=True,
                        automation_id=automation.automation_id,
                        raw_result=results,
                    )

                if not result.success:
                    return HomeIntentResponse(
                        handled=True,
                        message=(
                            result.error_message
                            or "No he podido completar el control del acuario pequeño."
                        ),
                        automation_id=automation.automation_id,
                        raw_result=results,
                    )

                changed += 1

            verb = (
                "encendido"
                if intent.intent_type == HomeIntentType.TURN_ON_GROUP
                else "apagado"
            )

            if changed == 0 and already_in_target_state:
                message = (
                    self._already_on_message()
                    if intent.intent_type == HomeIntentType.TURN_ON_GROUP
                    else self._already_off_message()
                )
            else:
                message = f"He {verb} el acuario pequeño."

            return HomeIntentResponse(
                handled=True,
                message=message,
                raw_result=results,
            )

        normalized_user_id = self.environment.normalize_user_id(user_id)
        if self._guest_presence_is_not_verified(normalized_user_id):
            return HomeIntentResponse(
                handled=True,
                message=self._guest_absent_message(),
            )

        entity_id = intent.parameters.get("entity_id", "")
        redundant_message = self._redundant_state_message(
            intent.intent_type,
            entity_id,
        )
        if redundant_message is not None:
            return HomeIntentResponse(
                handled=True,
                message=redundant_message,
            )

        try:
            automation = self.environment.manager.create(
                action_id=intent.action_id,
                owner_user_id=user_id,
                creator_user_id=user_id,
                parameters=intent.parameters,
            )
        except PermissionError:
            return HomeIntentResponse(
                handled=True,
                message=self._permission_denied_message(),
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
                    "Confirma que quieres controlar este dispositivo doméstico."
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
    def _friendly_object_phrase(result: dict, fallback: str) -> str:
        friendly_name = str(
            result.get("attributes", {}).get("friendly_name", fallback)
        ).strip()
        if not friendly_name:
            friendly_name = fallback

        normalized = friendly_name[:1].lower() + friendly_name[1:]
        first_word = normalized.split(maxsplit=1)[0].casefold()

        feminine_words = {
            "luz",
            "lampara",
            "lámpara",
            "tira",
            "bombilla",
            "regleta",
        }
        article = "la" if first_word in feminine_words else "el"
        return f"{article} {normalized}"

    @staticmethod
    def _success_message(
        intent_type: HomeIntentType,
        result: dict,
    ) -> str:
        if intent_type == HomeIntentType.TURN_ON_LIGHT:
            return (
                "He encendido "
                f"{HomeIntentService._friendly_object_phrase(result, 'luz')}."
            )

        if intent_type == HomeIntentType.TURN_OFF_LIGHT:
            return (
                "He apagado "
                f"{HomeIntentService._friendly_object_phrase(result, 'luz')}."
            )

        if intent_type == HomeIntentType.READ_TEMPERATURE:
            state = result.get("state", "desconocida")
            unit = result.get("attributes", {}).get(
                "unit_of_measurement",
                "°C",
            )
            return f"El sensor virtual marca {state} {unit}."

        if intent_type == HomeIntentType.TURN_ON_SWITCH:
            phrase = HomeIntentService._friendly_object_phrase(
                result,
                "dispositivo doméstico",
            )
            phrase = re.sub(
                r"^(la luz) (acuario\b)",
                r"\1 del \2",
                phrase,
                flags=re.IGNORECASE,
            )
            return f"He encendido {phrase}."

        if intent_type == HomeIntentType.TURN_OFF_SWITCH:
            phrase = HomeIntentService._friendly_object_phrase(
                result,
                "dispositivo doméstico",
            )
            phrase = re.sub(
                r"^(la luz) (acuario\b)",
                r"\1 del \2",
                phrase,
                flags=re.IGNORECASE,
            )
            return f"He apagado {phrase}."

        return "Acción doméstica completada."
