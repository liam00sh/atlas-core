"""Herramienta segura de memoria documental unificada."""

from dataclasses import asdict
from typing import Any

from knowledge.service import KnowledgeService
from tools.base_tool import BaseTool, ToolRisk
from tools.capability import Capability
from tools.context import ToolContext
from tools.result import ToolResult


class KnowledgeTool(BaseTool):
    tool_id = "atlas.knowledge"
    name = "Atlas Unified Knowledge"
    capabilities = (Capability("knowledge.retrieve"), Capability("knowledge.answer"))
    required_permissions = frozenset({"knowledge.read"})
    risk = ToolRisk.MEDIUM

    def __init__(self, service: KnowledgeService):
        super().__init__()
        self.service = service

    def validate_arguments(self, arguments: dict[str, Any]) -> None:
        super().validate_arguments(arguments)
        question = arguments.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ValueError("Se necesita una pregunta no vacia.")
        limit = arguments.get("limit", 10)
        if not isinstance(limit, int) or not 1 <= limit <= 20:
            raise ValueError("El limite debe estar entre 1 y 20.")

    def execute(self, capability: Capability, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        explicit_sensitive = bool(arguments.get("allow_sensitive", False))
        sensitive_permission = context.has_permission("knowledge.sensitive.read")
        if explicit_sensitive and not sensitive_permission:
            return ToolResult.fail(
                "La consulta requiere acceso a datos sensibles.",
                error="sensitive_permission_denied",
            )
        if str(capability) == "knowledge.retrieve":
            fragments = self.service.retriever.retrieve(
                arguments["question"],
                user_id=context.requested_by,
                limit=arguments.get("limit", 10),
                allow_sensitive=explicit_sensitive,
                has_sensitive_permission=sensitive_permission,
                drive_scope=arguments.get("drive_scope"),
            )
            return ToolResult.ok(
                "Conocimiento recuperado." if fragments else "No hay informacion suficiente.",
                data={
                    "fragments": [asdict(item) for item in fragments],
                    "conflicts": [
                        {"type": item.conflict_type, "resolution": item.resolution}
                        for item in self.service.retriever.last_conflicts
                    ],
                    "excluded_sensitive": self.service.retriever.last_excluded_sensitive,
                },
            )
        answer = self.service.answer(
            arguments["question"],
            user_id=context.requested_by,
            allow_sensitive=explicit_sensitive,
            has_sensitive_permission=sensitive_permission,
            drive_scope=arguments.get("drive_scope"),
        )
        return ToolResult.ok("Respuesta de conocimiento generada.", data=asdict(answer))
