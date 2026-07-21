from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class ToolContext:
    """Contexto mínimo y seguro entregado a una herramienta."""

    requested_by: str
    channel: str = "cli"
    permissions: set[str] = field(default_factory=set)
    correlation_id: str = field(default_factory=lambda: uuid4().hex)
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_permission(self, permission: str) -> bool:
        return permission.strip().lower() in {
            item.strip().lower() for item in self.permissions
        }
