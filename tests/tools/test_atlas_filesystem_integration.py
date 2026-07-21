"""
Integración de filesystem.read con Atlas.
"""

from pathlib import Path

from core.atlas import Atlas
from tools.filesystem_read import FilesystemReadTool
from tools.system_status import SystemStatusTool


def test_atlas_registers_filesystem_read_tool() -> None:
    atlas = Atlas(ai_provider=None)

    tool = atlas.framework_tool_registry.get(
        "filesystem.read"
    )

    system_tool = atlas.framework_tool_registry.get(
        "system.status"
    )

    assert isinstance(tool, FilesystemReadTool)
    assert isinstance(system_tool, SystemStatusTool)
    assert atlas.get_framework_tool_count() >= 2


def test_atlas_can_read_project_file_through_adapter() -> None:
    atlas = Atlas(ai_provider=None)

    result = atlas.execute_framework_tool(
        "filesystem.read",
        arguments={
            "path": "README.md",
            "max_chars": 200,
        },
        channel="test",
    )

    assert result.success is True
    assert result.tool_id == "filesystem.read"
    assert result.data["path"] == "README.md"
    assert result.data["content"]
