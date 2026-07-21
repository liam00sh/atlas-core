"""
Pruebas del controlador conversacional de Google Drive.
"""

from dataclasses import dataclass, field
from typing import Any

from tools.google_drive_conversation import (
    GoogleDriveConversationController,
)


@dataclass
class FakeResult:
    success: bool
    data: dict[str, Any] = field(
        default_factory=dict
    )
    message: str = ""
    error: str | None = None


class FakeAtlas:
    def __init__(self) -> None:
        self.calls: list[
            tuple[str, dict[str, Any]]
        ] = []
        self.results: dict[
            str,
            list[FakeResult],
        ] = {}
        self.user = "Liam"

    def get_user(self) -> str:
        return self.user

    def queue(
        self,
        capability: str,
        result: FakeResult,
    ) -> None:
        self.results.setdefault(
            capability,
            [],
        ).append(result)

    def execute_framework_tool(
        self,
        capability: str,
        *,
        arguments: dict | None = None,
        channel: str = "cli",
        metadata: dict | None = None,
    ) -> FakeResult:
        self.calls.append(
            (
                capability,
                arguments or {},
            )
        )
        return self.results[
            capability
        ].pop(0)


def drive_item(
    item_id: str,
    name: str,
    *,
    is_folder: bool = False,
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "name": name,
        "mime_type": (
            "application/vnd.google-apps.folder"
            if is_folder
            else "text/plain"
        ),
        "is_folder": is_folder,
    }


def test_generic_search_is_not_intercepted() -> None:
    controller = (
        GoogleDriveConversationController()
    )
    atlas = FakeAtlas()

    response = controller.handle(
        atlas,
        "Busca información sobre Python",
    )

    assert response.handled is False
    assert atlas.calls == []


def test_searches_drive_explicitly() -> None:
    controller = (
        GoogleDriveConversationController()
    )
    atlas = FakeAtlas()
    atlas.queue(
        "documents.search",
        FakeResult(
            True,
            data={
                "items": [
                    drive_item(
                        "doc-1",
                        "Constitución de Atlas",
                    )
                ]
            },
        ),
    )

    response = controller.handle(
        atlas,
        "Busca en Drive Constitución de Atlas",
    )

    assert response.handled is True
    assert "Constitución de Atlas" in response.message
    assert atlas.calls[0][0] == "documents.search"
    assert (
        atlas.calls[0][1]["query"]
        == "constitución de atlas"
    )


def test_opens_first_search_result() -> None:
    controller = (
        GoogleDriveConversationController()
    )
    atlas = FakeAtlas()
    atlas.queue(
        "documents.search",
        FakeResult(
            True,
            data={
                "items": [
                    drive_item(
                        "doc-1",
                        "Manual Atlas",
                    ),
                    drive_item(
                        "doc-2",
                        "Manual de pruebas",
                    ),
                ]
            },
        ),
    )
    atlas.queue(
        "documents.read",
        FakeResult(
            True,
            data={
                "item": drive_item(
                    "doc-1",
                    "Manual Atlas",
                ),
                "content": "Contenido real",
                "truncated": False,
            },
        ),
    )

    controller.handle(
        atlas,
        "Busca en Drive Manual",
    )
    response = controller.handle(
        atlas,
        "Abre el primero",
    )

    assert response.handled is True
    assert "Contenido real" in response.message
    assert atlas.calls[-1][0] == "documents.read"
    assert atlas.calls[-1][1]["file_id"] == "doc-1"


def test_rejects_invalid_result_number() -> None:
    controller = (
        GoogleDriveConversationController()
    )
    atlas = FakeAtlas()
    atlas.queue(
        "documents.search",
        FakeResult(
            True,
            data={
                "items": [
                    drive_item(
                        "doc-1",
                        "Documento",
                    )
                ]
            },
        ),
    )

    controller.handle(
        atlas,
        "Busca en Drive Documento",
    )
    response = controller.handle(
        atlas,
        "Abre el 4",
    )

    assert response.handled is True
    assert "Solo hay 1 resultado" in response.message


def test_reads_unique_document_by_name() -> None:
    controller = (
        GoogleDriveConversationController()
    )
    atlas = FakeAtlas()
    atlas.queue(
        "documents.search",
        FakeResult(
            True,
            data={
                "items": [
                    drive_item(
                        "doc-1",
                        "Constitución de Atlas",
                    )
                ]
            },
        ),
    )
    atlas.queue(
        "documents.read",
        FakeResult(
            True,
            data={
                "item": drive_item(
                    "doc-1",
                    "Constitución de Atlas",
                ),
                "content": "Principios del proyecto",
                "truncated": False,
            },
        ),
    )

    response = controller.handle(
        atlas,
        "Lee el documento Constitución de Atlas",
    )

    assert response.handled is True
    assert "Principios del proyecto" in response.message


def test_lists_root_and_opens_folder() -> None:
    controller = (
        GoogleDriveConversationController()
    )
    atlas = FakeAtlas()
    atlas.queue(
        "folders.list",
        FakeResult(
            True,
            data={
                "items": [
                    drive_item(
                        "folder-1",
                        "Documentación",
                        is_folder=True,
                    )
                ]
            },
        ),
    )
    atlas.queue(
        "folders.list",
        FakeResult(
            True,
            data={
                "items": [
                    drive_item(
                        "doc-1",
                        "Arquitectura",
                    )
                ]
            },
        ),
    )

    first = controller.handle(
        atlas,
        "Lista Google Drive",
    )
    second = controller.handle(
        atlas,
        "Abre el primero",
    )

    assert first.handled is True
    assert second.handled is True
    assert "Arquitectura" in second.message


def test_disabled_tool_returns_clear_message() -> None:
    controller = (
        GoogleDriveConversationController()
    )
    atlas = FakeAtlas()
    atlas.queue(
        "documents.search",
        FakeResult(
            False,
            error="tool_disabled",
        ),
    )

    response = controller.handle(
        atlas,
        "Busca en Drive Atlas",
    )

    assert response.handled is True
    assert "no está activa" in response.message


def test_state_is_separated_by_user() -> None:
    controller = (
        GoogleDriveConversationController()
    )
    atlas = FakeAtlas()
    atlas.queue(
        "documents.search",
        FakeResult(
            True,
            data={
                "items": [
                    drive_item(
                        "doc-1",
                        "Documento de Liam",
                    )
                ]
            },
        ),
    )

    controller.handle(
        atlas,
        "Busca en Drive Documento",
    )

    atlas.user = "Saray"
    response = controller.handle(
        atlas,
        "Abre el primero",
    )

    assert response.handled is False
