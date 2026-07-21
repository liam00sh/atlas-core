from pathlib import Path

from tools.capability import Capability
from tools.context import ToolContext
from tools.google_drive import (
    DriveItem,
    InMemoryGoogleDriveClient,
)
from tools.google_drive_index import (
    GoogleDriveDocumentIndex,
    GoogleDriveIndexTool,
)


def build_client() -> InMemoryGoogleDriveClient:
    return InMemoryGoogleDriveClient(
        items=[
            DriveItem(
                item_id="folder",
                name="Documentación",
                mime_type="folder",
                is_folder=True,
            ),
            DriveItem(
                item_id="doc-1",
                name="Decisiones Técnicas",
                mime_type="text/plain",
                modified_time="2026-07-18T10:00:00Z",
                parent_id="folder",
                web_url="https://example/doc-1",
            ),
            DriveItem(
                item_id="doc-2",
                name="Constitución",
                mime_type="text/plain",
                modified_time="2026-07-18T11:00:00Z",
                parent_id="folder",
            ),
        ],
        contents={
            "doc-1": (
                "Atlas utiliza memoria persistente y Ollama "
                "como proveedor local."
            ),
            "doc-2": (
                "La memoria necesita confirmación antes "
                "de guardar información."
            ),
        },
    )


def test_sync_creates_persistent_index(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(
        tmp_path / "index.json"
    )

    stats = index.sync(build_client())

    assert stats["indexed"] == 2
    assert stats["document_count"] == 2
    assert index.path.exists()


def test_incremental_sync_skips_unchanged(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(
        tmp_path / "index.json"
    )
    client = build_client()
    index.sync(client)

    stats = index.sync(client)

    assert stats["unchanged"] == 2
    assert stats["indexed"] == 0
    assert stats["updated"] == 0


def test_search_returns_source_and_fragment(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(
        tmp_path / "index.json"
    )
    index.sync(build_client())

    matches = index.search(
        "memoria persistente"
    )

    assert matches[0].item.name == "Decisiones Técnicas"
    assert "memoria persistente" in matches[0].snippet
    assert matches[0].item.web_url == "https://example/doc-1"


def test_search_is_accent_insensitive(tmp_path: Path) -> None:
    client = InMemoryGoogleDriveClient(
        items=[
            DriveItem(
                item_id="doc",
                name="OAuth",
                mime_type="text/plain",
                modified_time="1",
            )
        ],
        contents={
            "doc": "La autenticación utiliza OAuth."
        },
    )
    index = GoogleDriveDocumentIndex(
        tmp_path / "index.json"
    )
    index.sync(client)

    assert index.search("autenticacion")


def test_status_and_clear(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(
        tmp_path / "index.json"
    )
    index.sync(build_client())

    assert index.status()["document_count"] == 2
    assert index.clear() is True
    assert index.status()["exists"] is False


def test_tool_exposes_index_capabilities(tmp_path: Path) -> None:
    tool = GoogleDriveIndexTool(
        build_client(),
        GoogleDriveDocumentIndex(
            tmp_path / "index.json"
        ),
    )
    context = ToolContext(
        requested_by="Liam",
        permissions={"google.drive.read"},
        channel="test",
    )

    sync = tool.execute(
        Capability("documents.index.sync"),
        {},
        context,
    )
    search = tool.execute(
        Capability("documents.index.search"),
        {"query": "Ollama"},
        context,
    )

    assert sync.success is True
    assert search.success is True
    assert search.data["count"] == 1
