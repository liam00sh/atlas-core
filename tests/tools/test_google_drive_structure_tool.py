from pathlib import Path

import pytest

from tools.context import ToolContext
from tools.exceptions import ToolPermissionError
from tools.google_drive import DriveItem, InMemoryGoogleDriveClient
from tools.google_drive_structure import (
    DriveNavigationService,
    GoogleDriveStructureIndex,
    GoogleDriveStructureTool,
)
from tools.manager import ToolManager
from tools.registry import ToolRegistry


def _manager(tmp_path: Path) -> ToolManager:
    client = InMemoryGoogleDriveClient([
        DriveItem("folder", "Carpeta", "folder", parent_id="root", is_folder=True),
        DriveItem("file", "doc.md", "text/plain", parent_id="folder"),
    ], {"file": "texto"})
    client.root_folder_id = "root"
    index = GoogleDriveStructureIndex(tmp_path / "structure.json")
    registry = ToolRegistry()
    registry.register(GoogleDriveStructureTool(client, index, DriveNavigationService(index)))
    return ToolManager(registry)


def _context(user="Liam", session="one", permission=True) -> ToolContext:
    return ToolContext(
        requested_by=user,
        permissions={"google.drive.read"} if permission else set(),
        metadata={"session_id": session, "drive_account_id": "account"},
    )


def test_structure_tool_requires_drive_permission(tmp_path: Path) -> None:
    with pytest.raises(ToolPermissionError):
        _manager(tmp_path).execute("drive.pwd", arguments={}, context=_context(permission=False))


def test_structure_tool_sync_cd_pwd_and_list(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    context = _context()
    assert manager.execute("drive.structure.sync", arguments={}, context=context).success
    assert manager.execute("drive.cd", arguments={"path": "Carpeta"}, context=context).success
    pwd = manager.execute("drive.pwd", arguments={}, context=context)
    listing = manager.execute("drive.list", arguments={}, context=context)
    assert pwd.data["entry"]["file_id"] == "folder"
    assert [item["file_id"] for item in listing.data["items"]] == ["file"]


def test_structure_tool_keeps_sessions_independent(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    manager.execute("drive.structure.sync", arguments={}, context=_context(session="a"))
    manager.execute("drive.cd", arguments={"path": "Carpeta"}, context=_context(session="a"))
    first = manager.execute("drive.pwd", arguments={}, context=_context(session="a"))
    second = manager.execute("drive.pwd", arguments={}, context=_context(session="b"))
    assert first.data["entry"]["file_id"] == "folder"
    assert second.data["entry"]["file_id"] == "root"


def test_resolve_file_does_not_change_location(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    context = _context()
    manager.execute("drive.structure.sync", arguments={}, context=context)
    resolved = manager.execute(
        "drive.resolve_path", arguments={"path": "Carpeta/doc.md", "allow_file": True}, context=context
    )
    pwd = manager.execute("drive.pwd", arguments={}, context=context)
    assert resolved.data["entry"]["file_id"] == "file"
    assert pwd.data["entry"]["file_id"] == "root"
