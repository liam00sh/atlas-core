import platform
import sys
from typing import Any

from tools.base_tool import BaseTool, ToolRisk
from tools.capability import Capability
from tools.context import ToolContext
from tools.result import ToolResult


class SystemStatusTool(BaseTool):
    """Primera herramienta real de prueba del framework."""

    tool_id = "system.status"
    name = "Estado del sistema"
    capabilities = (Capability("system.status.read"),)
    required_permissions = frozenset({"system.status.read"})
    risk = ToolRisk.LOW

    def execute(
        self,
        capability: Capability,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        return ToolResult.ok(
            "Estado del sistema obtenido correctamente.",
            data={
                "python": sys.version.split()[0],
                "platform": platform.platform(),
                "machine": platform.machine(),
                "requested_by": context.requested_by,
                "channel": context.channel,
            },
        )
