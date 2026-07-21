from pathlib import Path

from tools.google_drive import (
    DriveItem,
    InMemoryGoogleDriveClient,
)
from tools.google_drive_index import (
    GoogleDriveDocumentIndex,
)
from tools.google_drive_rag import (
    GoogleDriveRagService,
)
from tools.google_drive_semantic import (
    GoogleDriveSemanticIndex,
)


class FakeProvider:
    def is_available(self):
        return True

    def generate(self, prompt):
        return "Respuesta fundamentada [FUENTE 1]."

    def get_provider_name(self):
        return "Fake"

    def get_model_name(self):
        return "fake"


class FakeEmbedder:
    model_name = "fake"

    def is_available(self):
        return True

    def embed_many(self, texts):
        return [
            [
                float("recuerdo" in text.casefold()),
                float("identidad" in text.casefold()),
            ]
            for text in texts
        ]


def test_rag_prefers_semantic_results(
    tmp_path: Path,
) -> None:
    client = InMemoryGoogleDriveClient(
        items=[
            DriveItem(
                item_id="doc",
                name="Memoria conceptual",
                mime_type="text/plain",
                modified_time="1",
            )
        ],
        contents={
            "doc": (
                "Los recuerdos autorizados forman parte "
                "de la identidad persistente de Atlas."
            )
        },
    )
    document_index = GoogleDriveDocumentIndex(
        tmp_path / "document.json",
        chunk_chars=300,
        overlap_chars=40,
    )
    document_index.sync(client)

    semantic_index = GoogleDriveSemanticIndex(
        tmp_path / "semantic.json",
        document_index,
        FakeEmbedder(),
    )
    semantic_index.sync()

    service = GoogleDriveRagService(
        document_index,
        FakeProvider(),
        semantic_index,
    )

    answer, sources = service.answer(
        "Cómo conserva Atlas sus recuerdos"
    )

    assert "[FUENTE 1]" in answer
    assert sources[0].name == "Memoria conceptual"
