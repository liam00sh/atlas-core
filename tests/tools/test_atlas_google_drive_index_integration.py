from pathlib import Path

from core.atlas import Atlas
from tools.base_tool import ToolState
from tools.google_drive import (
    DriveItem,
    InMemoryGoogleDriveClient,
)
from tools.google_drive_index import GoogleDriveIndexTool
from tools.google_drive_oauth import GoogleDriveOAuthProvider


def test_atlas_registers_disabled_index_tool(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        GoogleDriveOAuthProvider,
        "build_client",
        lambda self, *, interactive=False: None,
    )
    atlas = Atlas(ai_provider=None)

    tool = atlas.framework_tool_registry.get(
        "google.drive.index"
    )

    assert isinstance(tool, GoogleDriveIndexTool)
    assert tool.state is ToolState.DISABLED


def test_configuring_drive_enables_index_tool(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        GoogleDriveOAuthProvider,
        "build_client",
        lambda self, *, interactive=False: None,
    )
    atlas = Atlas(ai_provider=None)
    atlas.google_drive_document_index.path = (
        tmp_path / "index.json"
    )

    atlas.configure_google_drive_client(
        InMemoryGoogleDriveClient(
            items=[
                DriveItem(
                    item_id="doc",
                    name="Documento",
                    mime_type="text/plain",
                    modified_time="1",
                )
            ],
            contents={"doc": "Contenido Atlas"},
        )
    )

    tool = atlas.framework_tool_registry.get(
        "google.drive.index"
    )
    assert tool.state is ToolState.ENABLED

    result = atlas.execute_framework_tool(
        "documents.index.sync"
    )
    assert result.success is True
    assert result.data["document_count"] == 1
