from collections.abc import Iterable

from tools.base_tool import BaseTool
from tools.capability import Capability
from tools.exceptions import ToolNotFoundError, ToolRegistrationError


class ToolRegistry:
    """Registro central de herramientas disponibles."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.tool_id in self._tools:
            raise ToolRegistrationError(
                f"La herramienta '{tool.tool_id}' ya está registrada."
            )
        self._tools[tool.tool_id] = tool

    def register_many(self, tools: Iterable[BaseTool]) -> None:
        for tool in tools:
            self.register(tool)

    def unregister(self, tool_id: str) -> BaseTool:
        try:
            return self._tools.pop(tool_id)
        except KeyError as exc:
            raise ToolNotFoundError(
                f"No existe la herramienta '{tool_id}'."
            ) from exc

    def get(self, tool_id: str) -> BaseTool:
        try:
            return self._tools[tool_id]
        except KeyError as exc:
            raise ToolNotFoundError(
                f"No existe la herramienta '{tool_id}'."
            ) from exc

    def find_by_capability(
        self,
        capability: Capability | str,
    ) -> list[BaseTool]:
        requested = (
            capability
            if isinstance(capability, Capability)
            else Capability(capability)
        )
        return [
            tool
            for tool in self._tools.values()
            if tool.supports(requested)
        ]

    @property
    def count(self) -> int:
        return len(self._tools)
