from collections.abc import Callable
from time import perf_counter
from typing import Any
from uuid import uuid4

from tools.base_tool import ToolState
from tools.capability import Capability
from tools.context import ToolContext
from tools.exceptions import (
    ToolDisabledError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolPermissionError,
)
from tools.registry import ToolRegistry
from tools.result import ToolResult


AuditSink = Callable[[dict[str, Any]], None]


class ToolManager:
    """Resuelve, valida, ejecuta y audita herramientas."""

    def __init__(
        self,
        registry: ToolRegistry,
        audit_sink: AuditSink | None = None,
    ) -> None:
        self.registry = registry
        self.audit_sink = audit_sink

    def execute(
        self,
        capability: Capability | str,
        *,
        arguments: dict[str, Any] | None = None,
        context: ToolContext,
    ) -> ToolResult:
        requested = (
            capability
            if isinstance(capability, Capability)
            else Capability(capability)
        )
        candidates = self.registry.find_by_capability(requested)

        if not candidates:
            raise ToolNotFoundError(
                f"No hay ninguna herramienta para '{requested}'."
            )

        tool = candidates[0]

        if tool.state is ToolState.DISABLED:
            raise ToolDisabledError(
                f"La herramienta '{tool.tool_id}' está desactivada."
            )

        missing_permissions = {
            permission
            for permission in tool.required_permissions
            if not context.has_permission(permission)
        }
        if missing_permissions:
            raise ToolPermissionError(
                "Faltan permisos: "
                + ", ".join(sorted(missing_permissions))
            )

        safe_arguments = arguments or {}
        tool.validate_arguments(safe_arguments)

        started = perf_counter()
        audit_id = uuid4().hex

        try:
            result = tool.execute(
                requested,
                safe_arguments,
                context,
            )
        except Exception as exc:
            raise ToolExecutionError(
                f"Falló la herramienta '{tool.tool_id}': {exc}"
            ) from exc

        result.tool_id = tool.tool_id
        result.capability = str(requested)
        result.duration_ms = round(
            (perf_counter() - started) * 1000,
            3,
        )
        result.audit_id = audit_id

        if self.audit_sink is not None:
            self.audit_sink(
                {
                    "audit_id": audit_id,
                    "tool_id": tool.tool_id,
                    "capability": str(requested),
                    "requested_by": context.requested_by,
                    "channel": context.channel,
                    "success": result.success,
                    "duration_ms": result.duration_ms,
                }
            )

        return result
