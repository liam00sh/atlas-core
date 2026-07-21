"""Herramienta del ciclo de vida controlado de memoria."""

from typing import Any

from memory.workflow.service import MemoryWorkflowService
from tools.base_tool import BaseTool, ToolRisk
from tools.capability import Capability
from tools.context import ToolContext
from tools.result import ToolResult


class MemoryWorkflowTool(BaseTool):
    """Expone operaciones estructuradas; ninguna detección escribe directamente."""

    tool_id = "atlas.memory.workflow"
    name = "Atlas Controlled Memory Workflow"
    capabilities = tuple(
        Capability(name) for name in (
            "memory.propose", "memory.confirm", "memory.reject",
            "memory.update_proposal", "memory.propose_update",
            "memory.confirm_update", "memory.propose_delete",
            "memory.select_delete", "memory.confirm_delete",
            "memory.read", "memory.audit.read",
        )
    )
    required_permissions = frozenset()
    risk = ToolRisk.HIGH
    capability_risks = {
        "memory.read": ToolRisk.LOW,
        "memory.propose": ToolRisk.LOW,
        "memory.reject": ToolRisk.LOW,
        "memory.update_proposal": ToolRisk.LOW,
        "memory.confirm": ToolRisk.MEDIUM,
        "memory.propose_update": ToolRisk.MEDIUM,
        "memory.confirm_update": ToolRisk.MEDIUM,
        "memory.propose_delete": ToolRisk.HIGH,
        "memory.select_delete": ToolRisk.HIGH,
        "memory.confirm_delete": ToolRisk.HIGH,
        "memory.audit.read": ToolRisk.HIGH,
    }

    def __init__(self, service: MemoryWorkflowService) -> None:
        super().__init__()
        self.service = service

    def validate_arguments(self, arguments: dict[str, Any]) -> None:
        super().validate_arguments(arguments)
        for key in ("text", "proposal_id", "query", "content", "memory_id"):
            if key in arguments and not isinstance(arguments[key], str):
                raise ValueError(f"El argumento {key} debe ser texto.")
        if "selection" in arguments and not isinstance(arguments["selection"], int):
            raise ValueError("El argumento selection debe ser un número entero.")

    def execute(self, capability: Capability, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        name = str(capability)
        permissions = context.permissions
        common = {"user_id": context.requested_by, "permissions": permissions}
        try:
            if name == "memory.propose":
                data = self.service.propose(
                    **common,
                    source_text=arguments.get("text", ""),
                    session_id=arguments.get("session_id"),
                    channel=context.channel,
                )
            elif name in {"memory.confirm", "memory.confirm_update", "memory.confirm_delete"}:
                data = self.service.confirm(
                    **common,
                    proposal_id=arguments.get("proposal_id", ""),
                    reinforced=bool(arguments.get("reinforced", False)),
                    session_id=arguments.get("session_id"),
                )
            elif name == "memory.reject":
                data = self.service.reject(
                    **common,
                    proposal_id=arguments.get("proposal_id", ""),
                    session_id=arguments.get("session_id"),
                )
            elif name == "memory.update_proposal":
                data = self.service.update_proposal(
                    **common,
                    proposal_id=arguments.get("proposal_id", ""),
                    content=arguments.get("content", ""),
                    session_id=arguments.get("session_id"),
                )
            elif name == "memory.propose_update":
                data = self.service.propose_update(
                    **common,
                    memory_id=arguments.get("memory_id", ""),
                    new_content=arguments.get("content", ""),
                    source_text=arguments.get("text", arguments.get("content", "")),
                    session_id=arguments.get("session_id"),
                )
            elif name == "memory.propose_delete":
                data = self.service.propose_delete(
                    **common,
                    query=arguments.get("query", ""),
                    session_id=arguments.get("session_id"),
                )
            elif name == "memory.select_delete":
                data = self.service.select_delete_candidate(
                    **common,
                    proposal_id=arguments.get("proposal_id", ""),
                    selection=arguments.get("selection", 0),
                    session_id=arguments.get("session_id"),
                )
            elif name == "memory.read":
                data = self.service.read(
                    **common,
                    query=arguments.get("query", ""),
                    allow_sensitive=bool(arguments.get("allow_sensitive", False)),
                )
            elif name == "memory.audit.read":
                self.service._require(permissions, "memory.audit.read")
                data = {"status": "ok", "entries": self.service.audit.list_for_user(context.requested_by)}
            else:
                return ToolResult.fail("Capacidad de memoria no implementada.", error="unsupported_capability")
        except PermissionError:
            return ToolResult.fail("No tienes permiso para realizar esa operación.", error="permission_denied")
        except (LookupError, RuntimeError, ValueError):
            # El detalle interno no incluye contenido ni se expone a conversación.
            return ToolResult.fail("No se pudo completar la operación de memoria.", error="memory_operation_failed")
        return ToolResult.ok(data.get("message", "Operación de memoria procesada."), data=data)
