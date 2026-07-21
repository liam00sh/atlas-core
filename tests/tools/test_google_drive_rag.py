from pathlib import Path

from tools.capability import Capability
from tools.context import ToolContext
from tools.google_drive import (
    DriveItem,
    InMemoryGoogleDriveClient,
)
from tools.google_drive_index import (
    GoogleDriveDocumentIndex,
)
from tools.google_drive_rag import (
    GoogleDriveRagService,
    GoogleDriveRagTool,
)


class FakeProvider:
    def __init__(self) -> None:
        self.prompts = []

    def is_available(self) -> bool:
        return True

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return (
            "La memoria de Atlas requiere confirmación "
            "[FUENTE 1] y utiliza persistencia [FUENTE 2]."
        )

    def get_provider_name(self) -> str:
        return "Fake"

    def get_model_name(self) -> str:
        return "fake-model"


def build_index(tmp_path: Path):
    client = InMemoryGoogleDriveClient(
        items=[
            DriveItem(
                item_id="doc-1",
                name="Constitución de Atlas",
                mime_type="text/plain",
                modified_time="1",
                web_url="https://example/doc-1",
            ),
            DriveItem(
                item_id="doc-2",
                name="Diseño de memoria",
                mime_type="text/plain",
                modified_time="1",
                web_url="https://example/doc-2",
            ),
        ],
        contents={
            "doc-1": (
                "La memoria persistente requiere confirmación "
                "del usuario antes de guardar."
            ),
            "doc-2": (
                "Atlas utiliza persistencia local para conservar "
                "recuerdos autorizados."
            ),
        },
    )
    index = GoogleDriveDocumentIndex(
        tmp_path / "index.json",
        chunk_chars=300,
        overlap_chars=40,
    )
    index.sync(client)
    return index


def test_service_builds_grounded_prompt(tmp_path: Path) -> None:
    index = build_index(tmp_path)
    provider = FakeProvider()
    service = GoogleDriveRagService(
        index,
        provider,
    )

    answer, sources = service.answer(
        "Cómo funciona la memoria persistente"
    )

    assert "[FUENTE 1]" in answer
    assert len(sources) == 2
    assert "FUENTES RECUPERADAS" in provider.prompts[0]
    assert "No inventes" in provider.prompts[0]


def test_tool_returns_answer_and_sources(tmp_path: Path) -> None:
    tool = GoogleDriveRagTool(
        build_index(tmp_path),
        FakeProvider(),
    )
    context = ToolContext(
        requested_by="Liam",
        permissions={"google.drive.read"},
        channel="test",
    )

    result = tool.execute(
        Capability("documents.rag.answer"),
        {
            "question": (
                "Cómo funciona la memoria persistente"
            )
        },
        context,
    )

    assert result.success is True
    assert result.data["source_count"] == 2
    assert result.data["sources"][0]["name"]


def test_service_refuses_empty_index(
    tmp_path: Path,
) -> None:
    service = GoogleDriveRagService(
        GoogleDriveDocumentIndex(
            tmp_path / "index.json"
        ),
        FakeProvider(),
    )

    try:
        service.answer("Pregunta")
    except RuntimeError as exception:
        assert "Actualiza primero" in str(exception)
    else:
        raise AssertionError(
            "La consulta debía rechazar un índice vacío."
        )
