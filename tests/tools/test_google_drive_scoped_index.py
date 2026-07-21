from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.google_drive import DriveItem, InMemoryGoogleDriveClient
from tools.google_drive_index import GoogleDriveDocumentIndex


ROOT = "root"
DOCS = "docs"
PYTHON = "python"


class RecordingClient(InMemoryGoogleDriveClient):
    def __init__(self, items, contents):
        super().__init__(items, contents)
        self.root_folder_id = ROOT
        self.read_ids: list[str] = []
        self.list_ids: list[str | None] = []
        self.fail_folder: str | None = None

    def list_folder(self, folder_id, *, limit):
        effective = ROOT if folder_id is None else folder_id
        self.list_ids.append(effective)
        if effective == self.fail_folder:
            raise RuntimeError("temporary remote failure")
        return super().list_folder(effective, limit=limit)

    def read_document(self, file_id, *, max_chars):
        self.read_ids.append(file_id)
        return super().read_document(file_id, max_chars=max_chars)


def _client() -> RecordingClient:
    return RecordingClient(
        [
            DriveItem(DOCS, "00 - Documentación", "folder", parent_id=ROOT, is_folder=True),
            DriveItem(PYTHON, "04 - Python", "folder", parent_id=ROOT, is_folder=True),
            DriveItem("sub", "atlas_core", "folder", parent_id=PYTHON, is_folder=True),
            DriveItem("d1", "privacy.md", "text/plain", modified_time="1", parent_id=DOCS, size_bytes=10),
            DriveItem("p1", "README.md", "text/plain", modified_time="1", parent_id=PYTHON, size_bytes=10),
            DriveItem("p2", "semantic_index.py", "text/plain", modified_time="1", parent_id="sub", size_bytes=10),
        ],
        {
            "d1": "privacidad local y controlada " * 20,
            "p1": "arquitectura general de Atlas " * 20,
            "p2": "indice semantico y embeddings " * 20,
        },
    )


def _sync_global(index: GoogleDriveDocumentIndex, client: RecordingClient):
    return index.sync_scope(client, root_folder_id=ROOT, target_folder_id=ROOT, recursive=True, max_items=100)


def test_global_update_keeps_historical_contract(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(tmp_path / "index.json")
    stats = index.sync(client := _client(), max_items=100)
    assert stats["global_scope"] is True
    assert stats["document_count"] == 3
    assert set(client.read_ids) == {"d1", "p1", "p2"}


def test_recursive_folder_update_preserves_other_scopes(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(tmp_path / "index.json")
    client = _client()
    _sync_global(index, client)
    client._contents["d1"] = "privacidad modificada " * 20
    client._items["d1"] = DriveItem("d1", "privacy.md", "text/plain", modified_time="2", parent_id=DOCS, size_bytes=11)
    client.read_ids.clear()
    stats = index.sync_scope(client, root_folder_id=ROOT, target_folder_id=DOCS, recursive=True)
    assert stats["updated"] == 1
    assert client.read_ids == ["d1"]
    assert set(index.load()["documents"]) == {"d1", "p1", "p2"}


def test_non_recursive_update_only_checks_direct_files(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(tmp_path / "index.json")
    client = _client()
    stats = index.sync_scope(client, root_folder_id=ROOT, target_folder_id=PYTHON, recursive=False)
    assert stats["discovered"] == 1
    assert set(index.load()["documents"]) == {"p1"}


def test_single_file_update_downloads_only_that_document(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(tmp_path / "index.json")
    client = _client()
    stats = index.sync_scope(client, root_folder_id=ROOT, target_file_id="p2")
    assert stats["target_file_id"] == "p2"
    assert client.read_ids == ["p2"]
    assert set(index.load()["documents"]) == {"p2"}


def test_unchanged_file_is_not_downloaded(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(tmp_path / "index.json")
    client = _client()
    _sync_global(index, client)
    client.read_ids.clear()
    stats = index.sync_scope(client, root_folder_id=ROOT, target_folder_id=DOCS)
    assert stats["unchanged"] == 1
    assert stats["downloaded"] == 0
    assert client.read_ids == []


def test_empty_file_state_prevents_repeated_download(tmp_path: Path) -> None:
    client = RecordingClient(
        [DriveItem("empty", "empty.txt", "text/plain", modified_time="1", parent_id=ROOT, size_bytes=0)],
        {"empty": "   "},
    )
    index = GoogleDriveDocumentIndex(tmp_path / "index.json")
    _sync_global(index, client)
    client.read_ids.clear()
    stats = _sync_global(index, client)
    assert stats["skipped"] == 1
    assert client.read_ids == []


def test_non_recursive_parent_sync_preserves_nested_empty_state(tmp_path: Path) -> None:
    client = RecordingClient(
        [
            DriveItem("sub-empty", "Sub", "folder", parent_id=ROOT, is_folder=True),
            DriveItem("nested-empty", "empty.txt", "text/plain", modified_time="1", parent_id="sub-empty", size_bytes=0),
        ],
        {"nested-empty": "   "},
    )
    structure = {
        "nested-empty": SimpleNamespace(
            relative_path="Atlas Project/Sub/empty.txt",
            ancestor_ids=(ROOT, "sub-empty"),
            ancestor_names=("Atlas Project", "Sub"),
        )
    }
    index = GoogleDriveDocumentIndex(tmp_path / "index.json")
    index.sync_scope(
        client, root_folder_id=ROOT, target_folder_id=ROOT,
        recursive=True, structure_entries=structure,
    )
    index.sync_scope(
        client, root_folder_id=ROOT, target_folder_id=ROOT,
        recursive=False, structure_entries=structure,
    )
    client.read_ids.clear()
    stats = index.sync_scope(
        client, root_folder_id=ROOT, target_folder_id="sub-empty",
        recursive=True, structure_entries=structure,
    )
    assert stats["unchanged"] == 1
    assert client.read_ids == []


def test_rename_and_move_reuse_existing_chunks(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(tmp_path / "index.json")
    client = _client()
    _sync_global(index, client)
    client._items["d1"] = DriveItem(
        "d1", "privacy-renamed.md", "text/plain", modified_time="1", parent_id=PYTHON, size_bytes=10
    )
    client.read_ids.clear()
    stats = index.sync_scope(client, root_folder_id=ROOT, target_folder_id=PYTHON, recursive=False)
    document = index.load()["documents"]["d1"]
    assert stats["renamed"] == 1
    assert stats["moved"] == 1
    assert stats["downloaded"] == 0
    assert document["item"]["name"] == "privacy-renamed.md"
    assert document["item"]["parent_id"] == PYTHON


def test_deleted_file_is_removed_only_from_updated_scope(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(tmp_path / "index.json")
    client = _client()
    _sync_global(index, client)
    del client._items["d1"]
    del client._contents["d1"]
    stats = index.sync_scope(client, root_folder_id=ROOT, target_folder_id=DOCS)
    assert stats["removed"] == 1
    assert set(index.load()["documents"]) == {"p1", "p2"}


def test_move_detected_from_structure_is_preserved_when_old_scope_updates(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(tmp_path / "index.json")
    client = _client()
    _sync_global(index, client)
    del client._items["d1"]
    structure = {
        "d1": SimpleNamespace(
            file_id="d1", name="privacy.md", mime_type="text/plain",
            modified_time="1", parent_id=PYTHON, size=10,
            relative_path="Atlas Project/04 - Python/privacy.md",
            ancestor_ids=(ROOT, PYTHON), ancestor_names=("Atlas Project", "04 - Python"),
        )
    }
    stats = index.sync_scope(
        client, root_folder_id=ROOT, target_folder_id=DOCS,
        structure_entries=structure,
    )
    document = index.load()["documents"]["d1"]
    assert stats["removed"] == 0
    assert stats["moved"] == 1
    assert document["item"]["parent_id"] == PYTHON


def test_temporary_listing_error_preserves_previous_index(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(tmp_path / "index.json")
    client = _client()
    _sync_global(index, client)
    before = index.load()
    client.fail_folder = DOCS
    with pytest.raises(RuntimeError):
        index.sync_scope(client, root_folder_id=ROOT, target_folder_id=DOCS)
    assert index.load() == before


def test_truncated_remote_listing_never_deletes_unseen_documents(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(tmp_path / "index.json")
    client = _client()
    _sync_global(index, client)
    before_ids = set(index.load()["documents"])
    stats = index.sync_scope(
        client, root_folder_id=ROOT, target_folder_id=ROOT,
        recursive=True, folder_limit=1,
    )
    assert stats["discovery_complete"] is False
    assert stats["removed"] == 0
    assert set(index.load()["documents"]) == before_ids


def test_lexical_search_filters_before_ranking(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(tmp_path / "index.json")
    client = _client()
    _sync_global(index, client)
    global_matches = index.search_chunks("Atlas semantico privacidad", limit=10)
    docs_matches = index.search_chunks(
        "Atlas semantico privacidad", limit=10,
        scope={"type": "subtree", "target_id": DOCS, "root_folder_id": ROOT},
    )
    assert {match.item.item_id for match in global_matches} >= {"d1", "p2"}
    assert {match.item.item_id for match in docs_matches} == {"d1"}


def test_document_scope_isolated_by_owner_and_account(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(tmp_path / "index.json")
    client = _client()
    index.sync_scope(
        client,
        root_folder_id=ROOT,
        target_folder_id=DOCS,
        owner_user_id="Liam",
        drive_account_id="liam-drive",
    )
    allowed = index.search_chunks(
        "privacidad",
        scope={"type": "global", "user_id": "Liam", "drive_account_id": "liam-drive"},
    )
    wrong_user = index.search_chunks(
        "privacidad",
        scope={"type": "global", "user_id": "Saray", "drive_account_id": "liam-drive"},
    )
    wrong_account = index.search_chunks(
        "privacidad",
        scope={"type": "global", "user_id": "Liam", "drive_account_id": "other-drive"},
    )
    assert allowed
    assert wrong_user == []
    assert wrong_account == []
