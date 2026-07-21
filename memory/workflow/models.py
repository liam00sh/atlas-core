"""Modelos inmutables del ciclo de vida conversacional de la memoria."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class MemoryProposal:
    """Cambio de memoria pendiente de una decisión explícita del usuario."""

    proposal_id: str
    user_id: str
    content: str
    category: str
    source_text: str
    confidence: float
    sensitivity: str
    temporal_scope: str
    created_at: str
    expires_at: str
    metadata: dict[str, Any] = field(default_factory=dict)
    operation: str = "create"
    status: str = "pending"
    session_id: str | None = None
    target_memory_id: str | None = None
    result_id: str | None = None
    version: int = 1
    reinforced_confirmation: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryProposal":
        fields = cls.__dataclass_fields__
        return cls(**{key: value for key, value in data.items() if key in fields})


@dataclass(frozen=True, slots=True)
class MemoryAuditEntry:
    """Evento mínimo y trazable de una operación de memoria."""

    event_id: str
    memory_id: str | None
    user_id: str
    action: str
    timestamp: str
    source: str
    previous_value: str | None = None
    new_value: str | None = None
    proposal_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CandidateResult:
    """Resultado validado del detector, todavía sin persistencia."""

    content: str
    category: str
    confidence: float
    sensitivity: str = "normal"
    temporal_scope: str = "permanent"
    metadata: dict[str, Any] = field(default_factory=dict)
    reinforced_confirmation: bool = False

