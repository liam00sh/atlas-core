from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolResult:
    """Resultado uniforme de la ejecución de una herramienta."""

    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    warnings: list[str] = field(default_factory=list)
    tool_id: str | None = None
    capability: str | None = None
    duration_ms: float | None = None
    audit_id: str | None = None

    @classmethod
    def ok(
        cls,
        message: str,
        *,
        data: dict[str, Any] | None = None,
    ) -> "ToolResult":
        return cls(
            success=True,
            message=message,
            data=data or {},
        )

    @classmethod
    def fail(
        cls,
        message: str,
        *,
        error: str | None = None,
    ) -> "ToolResult":
        return cls(
            success=False,
            message=message,
            error=error,
        )
