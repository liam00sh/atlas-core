"""
Pruebas de la herramienta Google Drive en modo solo lectura.
"""

import pytest

from tools.base_tool import ToolState
from tools.context import ToolContext
from tools.exceptions import (
    ToolDisabledError,
    ToolExecutionError,
)
from tools.google_drive import (
    DriveItem,
    GoogleDriveReadTool,
    InMemoryGoogleDriveClient,
    UnavailableGoogleDriveClient,
)
from tools.manager import ToolManager
from tools.registry import ToolRegistry


def build_items() -> tuple[list[DriveItem], dict[str, str]]:
    items = [
        DriveItem(
            item_id="folder-1",
            name="Documentación",
            mime_type="application/vnd.google-apps.folder",
            parent_id=None,
            is_folder=True,
        ),
        DriveItem(
            item_id="doc-1",
            name="Arquitectura Atlas",
            mime_type="application/vnd.google-apps.document",
            parent_id="folder-1",
        ),
        DriveItem(
            item_id="doc-2",
            name="Roadmap Atlas",
            mime_type="text/plain",
            parent_id="folder-1",
        ),
    ]
    contents = {
        "doc-1": "Contenido de arquitectura",
        "doc-2": "Contenido del roadmap",
    }
    return items, contents


def build_manager() -> ToolManager:
    items, contents = build_items()
    client = InMemoryGoogleDriveClient(
        items,
        contents,
    )
    registry = ToolRegistry()
    registry.register(
        GoogleDriveReadTool(client)
    )
    return ToolManager(registry)


def build_context() -> ToolContext:
    return ToolContext(
        requested_by="Liam",
        channel="test",
        permissions={"google.drive.read"},
    )


def test_unavailable_client_disables_tool() -> None:
    tool = GoogleDriveReadTool(
        UnavailableGoogleDriveClient()
    )

    assert tool.state is ToolState.DISABLED


def test_disabled_drive_tool_cannot_execute() -> None:
    registry = ToolRegistry()
    registry.register(
        GoogleDriveReadTool(
            UnavailableGoogleDriveClient()
        )
    )

    with pytest.raises(ToolDisabledError):
        ToolManager(registry).execute(
            "documents.search",
            arguments={"query": "Atlas"},
            context=build_context(),
        )


def test_searches_documents() -> None:
    result = build_manager().execute(
        "documents.search",
        arguments={
            "query": "Atlas",
            "parent_id": "folder-1",
        },
        context=build_context(),
    )

    assert result.success is True
    assert result.data["count"] == 2
    assert result.data["items"][0]["item_id"] == "doc-1"


def test_reads_document() -> None:
    result = build_manager().execute(
        "documents.read",
        arguments={"file_id": "doc-1"},
        context=build_context(),
    )

    assert result.success is True
    assert result.data["content"] == "Contenido de arquitectura"
    assert result.data["item"]["name"] == "Arquitectura Atlas"


def test_truncates_document() -> None:
    result = build_manager().execute(
        "documents.read",
        arguments={
            "file_id": "doc-1",
            "max_chars": 9,
        },
        context=build_context(),
    )

    assert result.data["content"] == "Contenido"
    assert result.data["truncated"] is True
    assert result.warnings


def test_lists_folder() -> None:
    result = build_manager().execute(
        "folders.list",
        arguments={"folder_id": "folder-1"},
        context=build_context(),
    )

    assert result.success is True
    assert result.data["count"] == 2


def test_validates_required_search_query() -> None:
    with pytest.raises(ToolExecutionError):
        build_manager().execute(
            "documents.search",
            arguments={},
            context=build_context(),
        )


def test_validates_required_file_id() -> None:
    with pytest.raises(ToolExecutionError):
        build_manager().execute(
            "documents.read",
            arguments={},
            context=build_context(),
        )
