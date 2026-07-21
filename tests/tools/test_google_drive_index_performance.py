from pathlib import Path

from tools.google_drive import (
    DriveItem,
    InMemoryGoogleDriveClient,
)
from tools.google_drive_index import (
    GoogleDriveDocumentIndex,
)


class CountingClient(InMemoryGoogleDriveClient):
    def __init__(self, items, contents):
        super().__init__(items, contents)
        self.read_count = 0

    def read_document(self, file_id, *, max_chars):
        self.read_count += 1
        return super().read_document(
            file_id,
            max_chars=max_chars,
        )


def test_index_excludes_technical_folders_and_binary_files(
    tmp_path: Path,
) -> None:
    items = [
        DriveItem(
            item_id="git",
            name=".git",
            mime_type="application/vnd.google-apps.folder",
            is_folder=True,
        ),
        DriveItem(
            item_id="git-object",
            name="object.bin",
            mime_type="application/octet-stream",
            parent_id="git",
        ),
        DriveItem(
            item_id="doc",
            name="Arquitectura.md",
            mime_type="text/markdown",
        ),
        DriveItem(
            item_id="zip",
            name="release.zip",
            mime_type="application/zip",
        ),
    ]
    client = CountingClient(
        items,
        {"doc": "Arquitectura de Atlas"},
    )
    index = GoogleDriveDocumentIndex(
        tmp_path / "index.json"
    )

    stats = index.sync(client)

    assert stats["document_count"] == 1
    assert stats["excluded"] >= 2
    assert client.read_count == 1


def test_second_sync_does_not_redownload_unchanged_text(
    tmp_path: Path,
) -> None:
    items = [
        DriveItem(
            item_id="doc",
            name="Documento.md",
            mime_type="text/markdown",
            modified_time="2026-07-18T20:00:00Z",
        )
    ]
    client = CountingClient(
        items,
        {"doc": "Contenido"},
    )
    index = GoogleDriveDocumentIndex(
        tmp_path / "index.json"
    )

    index.sync(client)
    index.sync(client)

    assert client.read_count == 1
