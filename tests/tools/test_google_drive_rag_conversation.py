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
        self.calls = []

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
        self.calls.append(
            (capability, arguments or {})
        )
        return FakeResult(
            True,
            data={
                "answer": (
                    "Atlas usa memoria persistente "
                    "[FUENTE 1]."
                ),
                "sources": [
                    {
                        "number": 1,
                        "item_id": "doc",
                        "name": "Diseño de Atlas",
                        "web_url": "https://example/doc",
                        "chunk_index": 0,
                        "score": 10.0,
                        "excerpt": "memoria persistente",
                    }
                ],
            },
        )


def test_explicit_rag_question_is_routed() -> None:
    atlas = FakeAtlas()
    controller = GoogleDriveConversationController()

    response = controller.handle(
        atlas,
        (
            "Responde usando la documentación de Drive: "
            "cómo funciona la memoria"
        ),
    )

    assert response.handled is True
    assert atlas.calls[0][0] == (
        "documents.rag.answer"
    )
    assert "Fuentes utilizadas" in response.message
    assert "Diseño de Atlas" in response.message


def test_documentation_question_is_routed() -> None:
    atlas = FakeAtlas()
    response = GoogleDriveConversationController().handle(
        atlas,
        (
            "Qué dice la documentación de Atlas "
            "sobre la memoria persistente"
        ),
    )

    assert response.handled is True
    assert atlas.calls[0][0] == (
        "documents.rag.answer"
    )
