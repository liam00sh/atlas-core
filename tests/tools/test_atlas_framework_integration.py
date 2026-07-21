"""
Pruebas de integración del Sprint 2 del Atlas Tools Framework.

Verifican que el sistema heredado y el nuevo framework conviven
sin sustituirse entre sí.
"""

from core.atlas import Atlas
from tools.context import ToolContext
from tools.system_status import SystemStatusTool
from tools.memory_write import MemoryWorkflowTool


def test_atlas_initializes_both_tool_systems() -> None:
    atlas = Atlas(ai_provider=None)

    assert atlas.tool_registry is not None
    assert atlas.tool_selector is not None
    assert atlas.framework_tool_registry is not None
    assert atlas.tool_manager is not None

    assert (
        atlas.tool_manager.registry
        is atlas.framework_tool_registry
    )


def test_system_status_tool_is_registered() -> None:
    atlas = Atlas(ai_provider=None)

    tool = atlas.framework_tool_registry.get(
        "system.status"
    )

    assert isinstance(tool, SystemStatusTool)
    assert atlas.framework_tool_registry.count >= 1


def test_memory_workflow_tool_is_registered_without_replacing_legacy_tools() -> None:
    atlas = Atlas(ai_provider=None)

    tool = atlas.framework_tool_registry.get("atlas.memory.workflow")

    assert isinstance(tool, MemoryWorkflowTool)
    assert atlas.tool_registry is not None
    assert atlas.tool_selector is not None


def test_registered_system_status_tool_can_execute() -> None:
    atlas = Atlas(ai_provider=None)

    context = ToolContext(
        requested_by=atlas.get_user(),
        channel="test",
        permissions={"system.status.read"},
    )

    result = atlas.tool_manager.execute(
        "system.status.read",
        context=context,
    )

    assert result.success is True
    assert result.tool_id == "system.status"
    assert result.capability == "system.status.read"
    assert result.data["requested_by"] == atlas.get_user()
    assert result.data["channel"] == "test"
    assert result.audit_id
