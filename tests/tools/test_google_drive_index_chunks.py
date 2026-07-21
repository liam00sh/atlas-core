from pathlib import Path

from tools.google_drive import (
    DriveItem,
    InMemoryGoogleDriveClient,
)
from tools.google_drive_index import (
    GoogleDriveDocumentIndex,
)


def test_search_chunks_can_return_multiple_chunks_per_document(
    tmp_path: Path,
) -> None:
    repeated = "memoria persistente " * 80
    client = InMemoryGoogleDriveClient(
        items=[
            DriveItem(
                item_id="doc",
                name="Memoria",
                mime_type="text/plain",
                modified_time="1",
            )
        ],
        contents={"doc": repeated},
    )
    index = GoogleDriveDocumentIndex(
        tmp_path / "index.json",
        chunk_chars=250,
        overlap_chars=30,
    )
    index.sync(client)

    matches = index.search_chunks(
        "memoria persistente",
        limit=4,
        max_per_document=3,
    )

    assert len(matches) == 3
    assert {
        match.item.item_id
        for match in matches
    } == {"doc"}
