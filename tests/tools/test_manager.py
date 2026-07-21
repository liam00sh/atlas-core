import pytest

from tools.context import ToolContext
from tools.exceptions import ToolDisabledError, ToolPermissionError
from tools.manager import ToolManager
from tools.registry import ToolRegistry
from tools.system_status import SystemStatusTool


def build_manager() -> tuple[ToolManager, SystemStatusTool]:
    registry = ToolRegistry()
    tool = SystemStatusTool()
    registry.register(tool)
    return ToolManager(registry), tool


def test_manager_executes_tool() -> None:
    manager, _ = build_manager()
    context = ToolContext(
        requested_by="Liam",
        permissions={"system.status.read"},
    )

    result = manager.execute(
        "system.status.read",
        context=context,
    )

    assert result.success is True
    assert result.tool_id == "system.status"
    assert result.capability == "system.status.read"
    assert result.audit_id is not None


def test_manager_rejects_missing_permission() -> None:
    manager, _ = build_manager()
    context = ToolContext(requested_by="Liam")

    with pytest.raises(ToolPermissionError):
        manager.execute(
            "system.status.read",
            context=context,
        )


def test_manager_rejects_disabled_tool() -> None:
    manager, tool = build_manager()
    tool.disable()
    context = ToolContext(
        requested_by="Liam",
        permissions={"system.status.read"},
    )

    with pytest.raises(ToolDisabledError):
        manager.execute(
            "system.status.read",
            context=context,
        )
