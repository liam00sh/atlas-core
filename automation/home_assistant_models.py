"""Modelos seguros para la Etapa E de Home Assistant."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class HomeEntityKind(StrEnum):
    LIGHT = "light"
    SWITCH = "switch"
    SENSOR = "sensor"
    BUTTON = "button"
    NUMBER = "number"
    SELECT = "select"
    TEXT = "text"
    DATETIME = "datetime"


class HomeEntityMode(StrEnum):
    VIRTUAL = "virtual"
    PHYSICAL = "physical"
    REAL = "physical"


class HomeEntityRisk(StrEnum):
    READ_ONLY = "read_only"
    LOW = "low"
    MEDIUM = "medium"
    PROHIBITED = "prohibited"


@dataclass(slots=True, frozen=True)
class HomeEntityDefinition:
    entity_id: str
    name: str
    kind: HomeEntityKind
    mode: HomeEntityMode = HomeEntityMode.VIRTUAL
    risk: HomeEntityRisk = HomeEntityRisk.LOW
    enabled: bool = True
    allowed_services: frozenset[str] = frozenset()
    required_permission: str = "home.read"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def domain(self) -> str:
        return self.entity_id.split(".", 1)[0]

    def validate(self) -> None:
        if "." not in self.entity_id:
            raise ValueError("entity_id debe incluir dominio y nombre.")
        if self.domain != self.kind.value:
            raise ValueError(
                f"El dominio '{self.domain}' no coincide con '{self.kind.value}'."
            )
        if self.risk == HomeEntityRisk.PROHIBITED:
            raise ValueError("No se pueden registrar entidades prohibidas.")
        if not self.enabled:
            raise ValueError("La entidad está deshabilitada.")


@dataclass(slots=True)
class HomeEntityState:
    entity_id: str
    state: str
    attributes: dict[str, Any] = field(default_factory=dict)
    last_changed: str | None = None
    last_updated: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class HomeServiceCall:
    domain: str
    service: str
    entity_id: str
    data: dict[str, Any] = field(default_factory=dict)
