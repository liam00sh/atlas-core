"""
Integración de Google Drive con Atlas.
"""

from core.atlas import Atlas
from tools.base_tool import ToolState
from tools.google_drive import (
    DriveItem,
    GoogleDriveReadTool,
    InMemoryGoogleDriveClient,
)
from tools.google_drive_oauth import (
    GoogleDriveOAuthProvider,
)


def test_atlas_registers_disabled_google_drive_tool(
    monkeypatch,
) -> None:
    # Simula un equipo sin sesión OAuth, aunque el desarrollador tenga
    # token.json en su instalación real.
    monkeypatch.setattr(
        GoogleDriveOAuthProvider,
        "build_client",
        lambda self, *, interactive=False: None,
    )

    atlas = Atlas(ai_provider=None)

    tool = atlas.framework_tool_registry.get(
        "google.drive.read"
    )

    assert isinstance(tool, GoogleDriveReadTool)
    assert tool.state is ToolState.DISABLED
    assert atlas.get_framework_tool_count() >= 3


def test_atlas_can_configure_google_drive_client(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        GoogleDriveOAuthProvider,
        "build_client",
        lambda self, *, interactive=False: None,
    )

    atlas = Atlas(ai_provider=None)

    client = InMemoryGoogleDriveClient(
        items=[
            DriveItem(
                item_id="doc-1",
                name="Documento Atlas",
                mime_type="text/plain",
            )
        ],
        contents={
            "doc-1": "Hola desde Google Drive",
        },
    )

    atlas.configure_google_drive_client(
        client
    )

    tool = atlas.framework_tool_registry.get(
        "google.drive.read"
    )
    assert tool.state is ToolState.ENABLED

    result = atlas.execute_framework_tool(
        "documents.read",
        arguments={"file_id": "doc-1"},
        channel="test",
    )

    assert result.success is True
    assert result.data["content"] == "Hola desde Google Drive"
