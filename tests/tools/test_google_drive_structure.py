from pathlib import Path

from tools.google_drive import DriveItem, InMemoryGoogleDriveClient
from tools.google_drive_structure import (
    DriveNavigationService,
    GoogleDriveStructureIndex,
)


ROOT = "root-atlas"


def _client() -> InMemoryGoogleDriveClient:
    client = InMemoryGoogleDriveClient(
        [
            DriveItem("python", "04 - Python", "folder", parent_id=ROOT, is_folder=True),
            DriveItem("docs", "00 - Documentación", "folder", parent_id=ROOT, is_folder=True),
            DriveItem("core", "atlas_core", "folder", parent_id="python", is_folder=True),
            DriveItem("memory-a", "memory", "folder", parent_id="core", is_folder=True),
            DriveItem("dup-a", "duplicada", "folder", parent_id="core", is_folder=True),
            DriveItem("dup-b", "duplicada", "folder", parent_id="core", is_folder=True),
            DriveItem("file-a", "semantic_index.py", "text/plain", parent_id="memory-a", size_bytes=20),
            DriveItem("outside", "Fuera", "folder", parent_id="other-root", is_folder=True),
        ],
        {"file-a": "contenido"},
    )
    client.root_folder_id = ROOT
    return client


def _services(tmp_path: Path, user: str = "liam"):
    index = GoogleDriveStructureIndex(tmp_path / "structure.json", ttl_seconds=60)
    index.sync(
        _client(), user_id=user, drive_account_id="account-a",
        root_folder_id=ROOT, root_folder_name="Atlas Project",
    )
    return index, DriveNavigationService(index)


def _identity(user: str = "liam", session: str = "s1") -> dict[str, str]:
    return {
        "user_id": user,
        "session_id": session,
        "drive_account_id": "account-a",
        "root_folder_id": ROOT,
        "root_folder_name": "Atlas Project",
    }


def test_resolves_absolute_and_relative_paths(tmp_path: Path) -> None:
    _, navigation = _services(tmp_path)
    absolute = navigation.resolve_path("Atlas Project/04 - Python/atlas_core", **_identity())
    assert absolute.status == "resolved"
    assert absolute.entry.file_id == "core"
    navigation.cd("04 - Python", **_identity())
    relative = navigation.resolve_path("atlas_core/memory", **_identity())
    assert relative.entry.file_id == "memory-a"


def test_parent_and_root_never_escape_authorized_root(tmp_path: Path) -> None:
    _, navigation = _services(tmp_path)
    assert navigation.cd("..", **_identity()).entry.file_id == ROOT
    assert navigation.cd("../../../../", **_identity()).entry.file_id == ROOT
    assert navigation.resolve_path("Fuera", **_identity()).status == "not_found"


def test_duplicate_names_are_reported_as_ambiguous(tmp_path: Path) -> None:
    _, navigation = _services(tmp_path)
    navigation.cd("/04 - Python/atlas_core", **_identity())
    result = navigation.resolve_path("duplicada", **_identity())
    assert result.status == "ambiguous"
    assert {item.file_id for item in result.candidates} == {"dup-a", "dup-b"}


def test_breadcrumbs_follow_stable_folder_ids(tmp_path: Path) -> None:
    _, navigation = _services(tmp_path)
    navigation.cd("/04 - Python/atlas_core/memory", **_identity())
    state = navigation.state(**_identity())
    assert [name for _, name in state.breadcrumbs] == [
        "Atlas Project", "04 - Python", "atlas_core", "memory"
    ]


def test_location_is_isolated_between_sessions(tmp_path: Path) -> None:
    _, navigation = _services(tmp_path)
    navigation.cd("04 - Python", **_identity(session="s1"))
    assert navigation.state(**_identity(session="s1")).current_folder_id == "python"
    assert navigation.state(**_identity(session="s2")).current_folder_id == ROOT


def test_structure_is_isolated_between_users(tmp_path: Path) -> None:
    index, navigation = _services(tmp_path, user="liam")
    assert navigation.resolve_path("04 - Python", **_identity(user="saray")).status == "missing_index"
    assert index.entries(user_id="saray", drive_account_id="account-a", root_folder_id=ROOT) == {}


def test_tree_honours_depth_and_file_filter(tmp_path: Path) -> None:
    _, navigation = _services(tmp_path)
    shallow = navigation.tree(depth=1, include_files=False, **_identity())
    assert {item["file_id"] for item in shallow} == {"python", "docs"}
    navigation.cd("/04 - Python/atlas_core/memory", **_identity())
    files = navigation.tree(depth=1, include_files=True, **_identity())
    assert [item["file_id"] for item in files] == ["file-a"]


def test_structure_cache_can_be_forced_and_invalidated(tmp_path: Path) -> None:
    client = _client()
    index = GoogleDriveStructureIndex(tmp_path / "structure.json", ttl_seconds=60)
    first = index.sync(client, user_id="liam", drive_account_id="a", root_folder_id=ROOT)
    cached = index.sync(client, user_id="liam", drive_account_id="a", root_folder_id=ROOT)
    assert first["cached"] is False
    assert cached["cached"] is True
    index.invalidate(user_id="liam", drive_account_id="a", root_folder_id=ROOT)
    refreshed = index.sync(client, user_id="liam", drive_account_id="a", root_folder_id=ROOT)
    assert refreshed["cached"] is False
