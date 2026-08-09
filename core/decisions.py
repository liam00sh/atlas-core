"""Contrato entre decisiones gobernadas por Atlas y su redacción final."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class DecisionStatus(StrEnum):
    ANSWERED = "answered"
    PENDING = "pending"
    DENIED = "denied"
    EXECUTED = "executed"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AtlasDecision:
    action: str
    status: DecisionStatus
    authorized: bool
    executed: bool = False
    entity: str | None = None
    reason: str | None = None
    data: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.executed and self.status is not DecisionStatus.EXECUTED:
            raise ValueError("Una decisión ejecutada debe tener estado executed.")
        if self.executed and not self.authorized:
            raise ValueError("Una acción no autorizada nunca puede figurar como ejecutada.")


class DecisionResponseComposer:
    """Redacta solo a partir del resultado estructurado ya decidido."""

    @staticmethod
    def compose(decision: AtlasDecision, *, assistant_name: str = "Daxter") -> str:
        if decision.status is DecisionStatus.EXECUTED and decision.executed:
            target = f" {decision.entity}" if decision.entity else ""
            return f"Listo: la acción {decision.action}{target} se ha completado correctamente."
        if decision.status is DecisionStatus.DENIED:
            why = decision.reason or "no tienes el permiso necesario"
            return f"No puedo realizar esa acción: {why}."
        if decision.status is DecisionStatus.PENDING:
            why = decision.reason or "necesito confirmación"
            return f"La acción aún no se ha realizado: {why}."
        if decision.status is DecisionStatus.FAILED:
            why = decision.reason or "el componente responsable ha informado de un error"
            return f"La acción no se ha completado: {why}."
        if decision.status is DecisionStatus.UNKNOWN:
            return "No tengo información suficiente para afirmarlo."
        return str(decision.data.get("answer", "He revisado la información disponible."))
