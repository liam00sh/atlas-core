from dataclasses import dataclass, field
from typing import Any

from tools.google_drive_conversation import (
    GoogleDriveConversationController,
)


@dataclass
class FakeResult:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    error: str | None = None


class FakeAtlas:
    def __init__(self) -> None:
        self.calls = []
        self.queued = []

    def get_user(self) -> str:
        return "Liam"

    def execute_framework_tool(
        self,
        capability,
        *,
        arguments=None,
        channel="cli",
        metadata=None,
    ):
        self.calls.append((capability, arguments or {}))
        return self.queued.pop(0)


def test_sync_index_command() -> None:
    atlas = FakeAtlas()
    atlas.queued.append(
        FakeResult(
            True,
            data={
                "discovered": 3,
                "indexed": 2,
                "updated": 0,
                "unchanged": 0,
                "removed": 0,
                "skipped": 0,
                "document_count": 2,
                "chunk_count": 2,
            },
        )
    )
    response = GoogleDriveConversationController().handle(
        atlas,
        "Actualiza el índice de Drive",
    )

    assert response.handled is True
    assert atlas.calls[0][0] == "documents.index.sync"
    assert "Documentos indexados: 2" in response.message


def test_search_index_command() -> None:
    atlas = FakeAtlas()
    atlas.queued.append(
        FakeResult(
            True,
            data={
                "matches": [
                    {
                        "item": {
                            "item_id": "doc",
                            "name": "Decisiones Técnicas",
                            "mime_type": "text/plain",
                            "is_folder": False,
                        },
                        "snippet": "Atlas utiliza Ollama.",
                        "score": 15.0,
                        "chunk_index": 0,
                    }
                ]
            },
        )
    )

    response = GoogleDriveConversationController().handle(
        atlas,
        "Busca Ollama en el índice de Drive",
    )

    assert response.handled is True
    assert atlas.calls[0][0] == "documents.index.search"
    assert "Decisiones Técnicas" in response.message


def test_index_status_command() -> None:
    atlas = FakeAtlas()
    atlas.queued.append(
        FakeResult(
            True,
            data={
                "exists": True,
                "document_count": 8,
                "chunk_count": 20,
                "updated_at": "2026-07-18",
                "path": "index.json",
            },
        )
    )

    response = GoogleDriveConversationController().handle(
        atlas,
        "Estado del índice de Drive",
    )

    assert atlas.calls[0][0] == "documents.index.status"
    assert "Documentos: 8" in response.message


def test_clear_index_command() -> None:
    atlas = FakeAtlas()
    atlas.queued.append(
        FakeResult(
            True,
            data={"deleted": True},
            message="Índice local eliminado.",
        )
    )

    response = GoogleDriveConversationController().handle(
        atlas,
        "Borra el índice de Drive",
    )

    assert atlas.calls[0][0] == "documents.index.clear"
    assert response.message == "Índice local eliminado."
