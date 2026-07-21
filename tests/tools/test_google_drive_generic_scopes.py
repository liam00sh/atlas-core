from pathlib import Path

import pytest

from tools.google_drive import DriveItem, InMemoryGoogleDriveClient
from tools.google_drive_index import GoogleDriveDocumentIndex
from tools.google_drive_structure import DriveNavigationService, GoogleDriveStructureIndex


ROOT = "atlas-root"


class RootClient(InMemoryGoogleDriveClient):
    def __init__(self):
        items = [
            DriveItem("pc", "02 - PC", "folder", parent_id=ROOT, is_folder=True),
            DriveItem("backups", "11 - Backups", "folder", parent_id=ROOT, is_folder=True),
            DriveItem("any", "Carpeta cualquiera", "folder", parent_id=ROOT, is_folder=True),
            DriveItem("release", "Releases", "folder", parent_id=ROOT, is_folder=True),
            DriveItem("backup", "Backup", "folder", parent_id=ROOT, is_folder=True),
            DriveItem("empty", "Vacía", "folder", parent_id=ROOT, is_folder=True),
            DriveItem("unsupported", "Solo binarios", "folder", parent_id=ROOT, is_folder=True),
            DriveItem("l1", "Nivel 1", "folder", parent_id="any", is_folder=True),
            DriveItem("l2", "Nivel 2", "folder", parent_id="l1", is_folder=True),
            DriveItem("l3", "Nivel 3", "folder", parent_id="l2", is_folder=True),
            DriveItem("dup-a", "Duplicada", "folder", parent_id="pc", is_folder=True),
            DriveItem("dup-b", "Duplicada", "folder", parent_id="backups", is_folder=True),
            DriveItem("pc-file", "pc.md", "text/markdown", modified_time="1", parent_id="pc"),
            DriveItem("backup-file", "backup.txt", "text/plain", modified_time="1", parent_id="backup"),
            DriveItem("deep-file", "deep.txt", "text/plain", modified_time="1", parent_id="l3"),
            DriveItem("release-file", "release.txt", "text/plain", modified_time="1", parent_id="release"),
            DriveItem("image", "photo.png", "image/png", modified_time="1", parent_id="unsupported"),
            DriveItem("zip", "archive.zip", "application/zip", modified_time="1", parent_id="unsupported"),
        ]
        super().__init__(items, {
            "pc-file": "Atlas PC " * 50,
            "backup-file": "Atlas backup " * 50,
            "deep-file": "Atlas profundo " * 50,
            "release-file": "Atlas release " * 50,
            "image": "binary",
            "zip": "binary",
        })
        self.root_folder_id = ROOT

    def list_folder(self, folder_id, *, limit):
        return super().list_folder(ROOT if folder_id is None else folder_id, limit=limit)


def _structure(tmp_path: Path):
    index = GoogleDriveStructureIndex(tmp_path / "structure.json")
    index.sync(
        RootClient(), user_id="Liam", drive_account_id="account",
        root_folder_id=ROOT, root_folder_name="Atlas Project",
    )
    return index, DriveNavigationService(index)


def _identity():
    return {
        "user_id": "Liam", "session_id": "session", "drive_account_id": "account",
        "root_folder_id": ROOT, "root_folder_name": "Atlas Project",
    }


@pytest.mark.parametrize(
    "folder_name,folder_id",
    [
        ("02 - PC", "pc"),
        ("11 - Backups", "backups"),
        ("Carpeta cualquiera", "any"),
        ("Backup", "backup"),
        ("Releases", "release"),
    ],
)
def test_arbitrary_root_names_resolve_by_parent_and_id(tmp_path: Path, folder_name: str, folder_id: str) -> None:
    _, navigation = _structure(tmp_path)
    result = navigation.resolve_path(folder_name, **_identity())
    assert result.status == "resolved"
    assert result.entry.file_id == folder_id


@pytest.mark.parametrize(
    "recursive,expected",
    [(False, set()), (True, {"deep-file"})],
)
def test_arbitrary_folder_sync_respects_recursion(tmp_path: Path, recursive: bool, expected: set[str]) -> None:
    index = GoogleDriveDocumentIndex(tmp_path / "documents.json")
    index.sync_scope(
        RootClient(), root_folder_id=ROOT, target_folder_id="any", recursive=recursive,
    )
    assert set(index.load()["documents"]) == expected


def test_backup_and_releases_are_not_default_exclusions(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(tmp_path / "documents.json")
    assert "backup" not in index.excluded_folder_names
    assert "backups" not in index.excluded_folder_names
    assert "releases" not in index.excluded_folder_names
    index.sync(RootClient(), max_items=100)
    assert {"backup-file", "release-file"} <= set(index.load()["documents"])


def test_default_technical_exclusions_are_exact_and_configurable(tmp_path: Path) -> None:
    index = GoogleDriveDocumentIndex(tmp_path / "documents.json")
    assert index.excluded_folder_names == frozenset({
        ".git", ".agents", ".pytest_cache", "__pycache__", ".mypy_cache",
        ".ruff_cache", ".venv", "venv", "node_modules", "logs",
    })
    custom = GoogleDriveDocumentIndex(
        tmp_path / "custom.json", excluded_folder_names={"Technical only"}
    )
    assert custom.excluded_folder_names == frozenset({"technical only"})


def test_configured_technical_folder_stays_visible_but_is_not_traversed(tmp_path: Path) -> None:
    structure = GoogleDriveStructureIndex(
        tmp_path / "structure.json", pruned_folder_names={"Carpeta cualquiera"}
    )
    structure.sync(
        RootClient(), user_id="Liam", drive_account_id="account",
        root_folder_id=ROOT, root_folder_name="Atlas Project",
    )
    entries = structure.entries(user_id="Liam", drive_account_id="account", root_folder_id=ROOT)
    assert entries["any"].traversal_status == "excluded_by_policy"
    assert entries["any"].exclusion_reason == "technical_folder_name"
    assert "l1" not in entries


def test_folder_with_only_unsupported_files_is_visible_and_navigable(tmp_path: Path) -> None:
    structure, navigation = _structure(tmp_path)
    assert navigation.cd("Solo binarios", **_identity()).status == "resolved"
    assert {entry.file_id for entry in navigation.list_current(**_identity())} == {"image", "zip"}
    documents = GoogleDriveDocumentIndex(tmp_path / "documents.json")
    stats = documents.sync_scope(
        RootClient(), root_folder_id=ROOT, target_folder_id="unsupported", recursive=True
    )
    assert stats["discovered"] == 0
    assert stats["excluded"] == 2


def test_deep_scope_preserves_sibling_branches(tmp_path: Path) -> None:
    client = RootClient()
    index = GoogleDriveDocumentIndex(tmp_path / "documents.json")
    index.sync(client, max_items=100)
    before = {
        file_id: document["content_hash"]
        for file_id, document in index.load()["documents"].items()
        if file_id != "deep-file"
    }
    index.sync_scope(client, root_folder_id=ROOT, target_folder_id="l3", recursive=True)
    after = {
        file_id: document["content_hash"]
        for file_id, document in index.load()["documents"].items()
        if file_id != "deep-file"
    }
    assert before == after


def test_duplicate_names_in_different_branches_resolve_without_special_cases(tmp_path: Path) -> None:
    _, navigation = _structure(tmp_path)
    left = navigation.resolve_path("02 - PC/Duplicada", **_identity())
    right = navigation.resolve_path("11 - Backups/Duplicada", **_identity())
    assert left.entry.file_id == "dup-a"
    assert right.entry.file_id == "dup-b"


def test_syncing_another_scope_does_not_change_current_folder(tmp_path: Path) -> None:
    structure, navigation = _structure(tmp_path)
    navigation.cd("02 - PC", **_identity())
    index = GoogleDriveDocumentIndex(tmp_path / "documents.json")
    index.sync_scope(RootClient(), root_folder_id=ROOT, target_folder_id="backups")
    assert navigation.state(**_identity()).current_folder_id == "pc"
    assert structure.entries(user_id="Liam", drive_account_id="account", root_folder_id=ROOT)


def test_deep_parent_navigation_cannot_escape_root(tmp_path: Path) -> None:
    _, navigation = _structure(tmp_path)
    navigation.cd("Carpeta cualquiera/Nivel 1/Nivel 2/Nivel 3", **_identity())
    result = navigation.resolve_path("../../../../../../..", **_identity())
    assert result.entry.file_id == ROOT
