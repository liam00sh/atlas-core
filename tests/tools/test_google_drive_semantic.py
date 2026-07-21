from pathlib import Path

from tools.google_drive import (
    DriveItem,
    InMemoryGoogleDriveClient,
)
from tools.google_drive_index import (
    GoogleDriveDocumentIndex,
)
from tools.google_drive_semantic import (
    GoogleDriveSemanticIndex,
)


class FakeEmbedder:
    model_name = "fake-embed"

    def is_available(self):
        return True

    def embed_many(self, texts):
        vectors = []
        for text in texts:
            lowered = text.casefold()
            vectors.append(
                [
                    float("memoria" in lowered),
                    float("oauth" in lowered),
                    float("herramientas" in lowered),
                ]
            )
        return vectors


def build_indexes(tmp_path: Path):
    client = InMemoryGoogleDriveClient(
        items=[
            DriveItem(
                item_id="memory",
                name="Memoria",
                mime_type="text/plain",
                modified_time="1",
            ),
            DriveItem(
                item_id="oauth",
                name="OAuth",
                mime_type="text/plain",
                modified_time="1",
            ),
        ],
        contents={
            "memory": (
                "Atlas conserva recuerdos autorizados "
                "mediante memoria persistente."
            ),
            "oauth": (
                "La autenticación de Drive utiliza OAuth."
            ),
        },
    )
    document_index = GoogleDriveDocumentIndex(
        tmp_path / "document_index.json",
        chunk_chars=300,
        overlap_chars=40,
    )
    document_index.sync(client)
    semantic = GoogleDriveSemanticIndex(
        tmp_path / "semantic_index.json",
        document_index,
        FakeEmbedder(),
    )
    return document_index, semantic


def test_semantic_sync_is_incremental(
    tmp_path: Path,
) -> None:
    _, semantic = build_indexes(tmp_path)

    first = semantic.sync()
    second = semantic.sync()

    assert first["embedded"] == 2
    assert second["embedded"] == 0
    assert second["unchanged"] == 2


def test_semantic_search_returns_related_chunk(
    tmp_path: Path,
) -> None:
    _, semantic = build_indexes(tmp_path)
    semantic.sync()

    matches = semantic.search(
        "cómo guarda memoria Atlas"
    )

    assert matches
    assert matches[0].item.name == "Memoria"


def test_semantic_clear(tmp_path: Path) -> None:
    _, semantic = build_indexes(tmp_path)
    semantic.sync()

    assert semantic.clear() is True
    assert semantic.status()["exists"] is False


def test_semantic_search_can_be_limited_to_one_file(tmp_path: Path) -> None:
    _, semantic = build_indexes(tmp_path)
    semantic.sync()

    matches = semantic.search(
        "oauth memoria",
        scope={"type": "file", "target_id": "oauth"},
    )

    assert matches
    assert {match.item.item_id for match in matches} == {"oauth"}


def test_metadata_change_does_not_regenerate_embeddings(tmp_path: Path) -> None:
    document_index, semantic = build_indexes(tmp_path)
    semantic.sync()
    payload = document_index.load()
    payload["documents"]["oauth"]["item"]["name"] = "OAuth renombrado"
    document_index.save(payload)

    stats = semantic.sync()
    matches = semantic.search("oauth", scope={"type": "file", "target_id": "oauth"})

    assert stats["embedded"] == 0
    assert stats["unchanged"] == 2
    assert matches[0].item.name == "OAuth renombrado"


def test_scoped_semantic_sync_preserves_other_documents(tmp_path: Path) -> None:
    document_index, semantic = build_indexes(tmp_path)
    semantic.sync()
    payload = document_index.load()
    del payload["documents"]["oauth"]
    document_index.save(payload)

    stats = semantic.sync(scope={"type": "file", "target_id": "oauth"})

    assert stats["removed"] == 1
    assert semantic.status()["document_count"] == 1
    assert semantic.search("memoria", scope={"type": "file", "target_id": "memory"})
