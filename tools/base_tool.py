from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from tools.capability import Capability
from tools.context import ToolContext
from tools.result import ToolResult


class ToolRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolState(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"


class BaseTool(ABC):
    """Contrato común de todas las herramientas de Atlas."""

    tool_id: str
    name: str
    capabilities: tuple[Capability, ...]
    required_permissions: frozenset[str] = frozenset()
    risk: ToolRisk = ToolRisk.LOW

    def __init__(self) -> None:
        self.state = ToolState.ENABLED

    def enable(self) -> None:
        self.state = ToolState.ENABLED

    def disable(self) -> None:
        self.state = ToolState.DISABLED

    def supports(self, capability: Capability | str) -> bool:
        requested = (
            capability
            if isinstance(capability, Capability)
            else Capability(capability)
        )
        return requested in self.capabilities

    def validate_arguments(self, arguments: dict[str, Any]) -> None:
        if not isinstance(arguments, dict):
            raise TypeError("Los argumentos de una herramienta deben ser un diccionario.")

    @abstractmethod
    def execute(
        self,
        capability: Capability,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        """Ejecuta una capacidad concreta."""
        raise NotImplementedError
