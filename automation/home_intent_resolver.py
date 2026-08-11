"""Resolución determinista de intenciones domésticas de la Etapa E."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

from automation.home_assistant_models import HomeEntityKind
from automation.home_device_registry import HomeDeviceRegistry


class HomeIntentType(StrEnum):
    TURN_ON_LIGHT = "turn_on_light"
    TURN_OFF_LIGHT = "turn_off_light"
    READ_TEMPERATURE = "read_temperature"
    TURN_ON_SWITCH = "turn_on_switch"
    TURN_OFF_SWITCH = "turn_off_switch"
    TURN_ON_GROUP = "turn_on_group"
    TURN_OFF_GROUP = "turn_off_group"
    SCHEDULE_SWITCH = "schedule_switch"
    ENABLE_SCHEDULE = "enable_schedule"
    DISABLE_SCHEDULE = "disable_schedule"
    TURN_ON_FOR_DURATION = "turn_on_for_duration"


@dataclass(frozen=True, slots=True)
class ResolvedHomeIntent:
    intent_type: HomeIntentType
    action_id: str
    parameters: dict[str, str]


def normalize_text(text: str) -> str:
    value = unicodedata.normalize("NFD", str(text).strip().casefold())
    value = "".join(c for c in value if unicodedata.category(c) != "Mn")
    value = re.sub(r"[^\w\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


REAL_HOME_ENTITIES = {
    "luz_acuario_grande": "switch.salon_acuario_grande_luz_acuario_grande",
    "luz_acuario_pequeno": "switch.despacho_acuario_pequeno_luz_acuario_pequeno",
    "oxigeno_acuario_pequeno": "switch.despacho_acuario_pequeno_oxigeno_acuario_pequeno",
}
AQUARIUM_SMALL_GROUP = (
    REAL_HOME_ENTITIES["luz_acuario_pequeno"],
    REAL_HOME_ENTITIES["oxigeno_acuario_pequeno"],
)


class HomeIntentResolver:
    def __init__(
        self,
        *,
        light_entity_id: str = "light.atlas_virtual",
        switch_entity_id: str = "switch.atlas_virtual",
        temperature_entity_id: str = "sensor.atlas_temperature",
    ) -> None:
        self.light_entity_id = light_entity_id
        self.switch_entity_id = switch_entity_id
        self.temperature_entity_id = temperature_entity_id

    @classmethod
    def from_device_registry(cls, registry: HomeDeviceRegistry) -> "HomeIntentResolver":
        by_kind: dict[HomeEntityKind, str] = {}
        for entity in registry.list_entities():
            by_kind.setdefault(entity.kind, entity.entity_id)
        return cls(
            light_entity_id=by_kind.get(HomeEntityKind.LIGHT, "light.atlas_virtual"),
            switch_entity_id=by_kind.get(HomeEntityKind.SWITCH, "switch.atlas_virtual"),
            temperature_entity_id=by_kind.get(
                HomeEntityKind.SENSOR,
                "sensor.atlas_temperature",
            ),
        )

    def resolve(self, text: str) -> ResolvedHomeIntent | None:
        normalized = normalize_text(text)

        duration = self._resolve_duration(normalized)
        if duration is not None:
            return duration

        schedule = self._resolve_schedule(normalized)
        if schedule is not None:
            return schedule

        grouped = self._resolve_group(normalized)
        if grouped is not None:
            return grouped

        real = self._resolve_real_switch(normalized)
        if real is not None:
            return real

        if self._matches(normalized, "enciende la luz", "encender la luz", "activa la luz"):
            return ResolvedHomeIntent(HomeIntentType.TURN_ON_LIGHT, "home.light.turn_on", {"entity_id": self.light_entity_id})
        if self._matches(normalized, "apaga la luz", "apagar la luz", "desactiva la luz"):
            return ResolvedHomeIntent(HomeIntentType.TURN_OFF_LIGHT, "home.light.turn_off", {"entity_id": self.light_entity_id})
        if "temperatura" in normalized and any(word in normalized for word in ("sensor", "marca", "hace")):
            return ResolvedHomeIntent(HomeIntentType.READ_TEMPERATURE, "home.state.read", {"entity_id": self.temperature_entity_id})
        if self._matches(normalized, "enciende el enchufe", "encender el enchufe", "activa el enchufe"):
            return ResolvedHomeIntent(HomeIntentType.TURN_ON_SWITCH, "home.switch.turn_on", {"entity_id": self.switch_entity_id})
        if self._matches(normalized, "apaga el enchufe", "apagar el enchufe", "desactiva el enchufe"):
            return ResolvedHomeIntent(HomeIntentType.TURN_OFF_SWITCH, "home.switch.turn_off", {"entity_id": self.switch_entity_id})
        return None

    @staticmethod
    def clarification_for(text: str) -> str | None:
        normalized = normalize_text(text)
        has_action = any(
            word in normalized.split()
            for word in (
                "enciende", "encender", "activa", "activar",
                "apaga", "apagar", "desactiva", "desactivar",
            )
        )
        if has_action:
            return None
        if "luz" in normalized and "acuario" in normalized:
            return "¿Quieres que la encienda o la apague?"
        if "oxigeno" in normalized and "acuario" in normalized:
            return "¿Quieres que active o desactive el oxígeno del acuario?"
        return None



    @staticmethod
    def _resolve_duration(text: str) -> ResolvedHomeIntent | None:
        match = re.search(
            r"(?:enciende|encender|activa|activar)\s+"
            r"(?:la\s+)?(?P<target>.+?)\s+durante\s+"
            r"(?P<amount>\d+)\s*(?P<unit>minuto|minutos|hora|horas)$",
            text,
        )
        if match is None:
            return None

        entity_id = HomeIntentResolver._resolve_schedule_entity(
            match.group("target")
        )
        if entity_id is None:
            return None

        amount = int(match.group("amount"))
        if amount <= 0:
            return None

        unit = match.group("unit")
        duration_minutes = amount * 60 if unit in ("hora", "horas") else amount

        return ResolvedHomeIntent(
            HomeIntentType.TURN_ON_FOR_DURATION,
            "home.timer.turn_on_for_duration",
            {
                "entity_id": entity_id,
                "duration_minutes": str(duration_minutes),
            },
        )

    @staticmethod
    def _resolve_schedule(text: str) -> ResolvedHomeIntent | None:
        match = re.search(
            r"(?:programa|programar|configura|configurar)\s+"
            r"(?:la\s+)?(?P<target>.+?)\s+de\s+"
            r"(?P<start_h>\d{1,2})[\s:]?(?P<start_m>\d{2})\s+a\s+"
            r"(?P<end_h>\d{1,2})[\s:]?(?P<end_m>\d{2})$",
            text,
        )
        if match:
            entity_id = HomeIntentResolver._resolve_schedule_entity(
                match.group("target")
            )
            if entity_id is None:
                return None
            return ResolvedHomeIntent(
                HomeIntentType.SCHEDULE_SWITCH,
                "home.schedule.switch",
                {
                    "entity_id": entity_id,
                    "start_time": HomeIntentResolver._format_time(
                        match.group("start_h"),
                        match.group("start_m"),
                    ),
                    "end_time": HomeIntentResolver._format_time(
                        match.group("end_h"),
                        match.group("end_m"),
                    ),
                },
            )

        if any(
            phrase in text
            for phrase in (
                "desactiva el horario",
                "desactivar el horario",
                "desactiva la programacion",
                "desactivar la programacion",
            )
        ):
            entity_id = HomeIntentResolver._resolve_schedule_entity(text)
            if entity_id is None:
                entity_id = REAL_HOME_ENTITIES["luz_acuario_grande"]
            return ResolvedHomeIntent(
                HomeIntentType.DISABLE_SCHEDULE,
                "home.schedule.disable",
                {"entity_id": entity_id},
            )

        if any(
            phrase in text
            for phrase in (
                "activa el horario",
                "activar el horario",
                "activa la programacion",
                "activar la programacion",
            )
        ):
            entity_id = HomeIntentResolver._resolve_schedule_entity(text)
            if entity_id is None:
                entity_id = REAL_HOME_ENTITIES["luz_acuario_grande"]
            return ResolvedHomeIntent(
                HomeIntentType.ENABLE_SCHEDULE,
                "home.schedule.enable",
                {"entity_id": entity_id},
            )

        return None


    @staticmethod
    def _format_time(hour: str, minute: str) -> str:
        hour_value = int(hour)
        minute_value = int(minute)
        if not 0 <= hour_value <= 23:
            raise ValueError("La hora debe estar entre 00 y 23.")
        if not 0 <= minute_value <= 59:
            raise ValueError("Los minutos deben estar entre 00 y 59.")
        return f"{hour_value:02d}:{minute_value:02d}:00"

    @staticmethod
    def _resolve_schedule_entity(text: str) -> str | None:
        if "luz" in text and "acuario" in text:
            if "pequeno" in text or "despacho" in text:
                return REAL_HOME_ENTITIES["luz_acuario_pequeno"]
            if "grande" in text or "salon" in text:
                return REAL_HOME_ENTITIES["luz_acuario_grande"]
        return None

    @staticmethod
    def _resolve_group(text: str) -> ResolvedHomeIntent | None:
        if "acuario pequeno" not in text:
            return None
        if any(word in text for word in ("luz", "oxigeno")):
            return None
        turn_on = any(word in text for word in ("enciende", "encender", "eniende", "activa", "activar"))
        turn_off = any(word in text for word in ("apaga", "apagar", "desactiva", "desactivar"))
        if not (turn_on or turn_off):
            return None
        intent_type = (
            HomeIntentType.TURN_ON_GROUP
            if turn_on
            else HomeIntentType.TURN_OFF_GROUP
        )
        return ResolvedHomeIntent(
            intent_type,
            "home.switch.turn_on" if turn_on else "home.switch.turn_off",
            {"entity_ids": "|".join(AQUARIUM_SMALL_GROUP)},
        )

    @staticmethod
    def _resolve_real_switch(text: str) -> ResolvedHomeIntent | None:
        turn_on = any(word in text for word in ("enciende", "encender", "eniende", "activa", "activar"))
        turn_off = any(word in text for word in ("apaga", "apagar", "desactiva", "desactivar"))
        if not (turn_on or turn_off):
            return None

        entity_id: str | None = None
        if "oxigeno" in text and "acuario" in text:
            entity_id = REAL_HOME_ENTITIES["oxigeno_acuario_pequeno"]
        elif "luz" in text and "acuario" in text:
            if "grande" in text or "salon" in text:
                entity_id = REAL_HOME_ENTITIES["luz_acuario_grande"]
            elif "pequeno" in text or "despacho" in text:
                entity_id = REAL_HOME_ENTITIES["luz_acuario_pequeno"]

        if entity_id is None:
            return None

        return ResolvedHomeIntent(
            HomeIntentType.TURN_ON_SWITCH if turn_on else HomeIntentType.TURN_OFF_SWITCH,
            "home.switch.turn_on" if turn_on else "home.switch.turn_off",
            {"entity_id": entity_id},
        )

    @staticmethod
    def _matches(text: str, *phrases: str) -> bool:
        return any(phrase in text for phrase in phrases)
