"""Pruebas conversacionales de búsqueda interna en Drive."""

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
        self.user = "Liam"
        self.calls: list[
            tuple[str, dict[str, Any]]
        ] = []
        self.queued: list[FakeResult] = []

    def get_user(self) -> str:
        return self.user

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
        return self.queued.pop(0)


def content_result() -> FakeResult:
    return FakeResult(
        True,
        data={
            "matches": [
                {
                    "item": {
                        "item_id": "doc-1",
                        "name": "Decisiones Técnicas",
                        "mime_type": "text/plain",
                        "web_url": "https://example/doc-1",
                        "is_folder": False,
                    },
                    "snippet": (
                        "Atlas utiliza memoria persistente."
                    ),
                    "score": 15.0,
                    "occurrence_count": 1,
                }
            ]
        },
    )


def test_where_we_talk_about_uses_content_search() -> None:
    atlas = FakeAtlas()
    atlas.queued.append(content_result())
    controller = GoogleDriveConversationController()

    response = controller.handle(
        atlas,
        "Dónde hablamos de memoria persistente en Drive",
    )

    assert response.handled is True
    assert atlas.calls[0][0] == "documents.search_content"
    assert (
        atlas.calls[0][1]["query"]
        == "memoria persistente"
    )
    assert "Decisiones Técnicas" in response.message
    assert "[1]" in response.message


def test_search_inside_drive_uses_content_search() -> None:
    atlas = FakeAtlas()
    atlas.queued.append(content_result())
    controller = GoogleDriveConversationController()

    controller.handle(
        atlas,
        "Busca dentro de Drive memoria",
    )

    assert atlas.calls[0][0] == "documents.search_content"


def test_content_results_can_be_opened_by_number() -> None:
    atlas = FakeAtlas()
    atlas.queued.append(content_result())
    atlas.queued.append(
        FakeResult(
            True,
            data={
                "item": {
                    "item_id": "doc-1",
                    "name": "Decisiones Técnicas",
                    "mime_type": "text/plain",
                    "is_folder": False,
                },
                "content": "Contenido completo.",
                "truncated": False,
            },
        )
    )
    controller = GoogleDriveConversationController()

    controller.handle(
        atlas,
        "Dónde hablamos de memoria en Drive",
    )
    response = controller.handle(
        atlas,
        "Abre el primero",
    )

    assert response.handled is True
    assert "Contenido completo" in response.message
    assert atlas.calls[-1][0] == "documents.read"


def test_no_content_matches_returns_clear_message() -> None:
    atlas = FakeAtlas()
    atlas.queued.append(
        FakeResult(
            True,
            data={
                "matches": [],
            },
        )
    )
    controller = GoogleDriveConversationController()

    response = controller.handle(
        atlas,
        "En qué documento hablamos de teleportación en Drive",
    )

    assert response.handled is True
    assert "No he encontrado fragmentos" in response.message


def test_generic_question_is_not_intercepted() -> None:
    atlas = FakeAtlas()
    controller = GoogleDriveConversationController()

    response = controller.handle(
        atlas,
        "Dónde está Murcia",
    )

    assert response.handled is False
    assert atlas.calls == []
