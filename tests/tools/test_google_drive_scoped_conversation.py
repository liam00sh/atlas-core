from dataclasses import dataclass, field
from typing import Any

import pytest

from tools.google_drive_conversation import GoogleDriveConversationController


@dataclass
class Result:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    message: str = ""
    error: str | None = None


class AtlasDouble:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        self.results: list[Result] = []

    def get_user(self) -> str:
        return "Liam"

    def execute_framework_tool(self, capability, *, arguments=None, channel="cli", metadata=None):
        self.calls.append((capability, arguments or {}, metadata or {}))
        return self.results.pop(0)


def _folder(file_id: str, path: str) -> dict[str, Any]:
    return {
        "file_id": file_id,
        "name": path.rsplit("/", 1)[-1],
        "relative_path": path,
        "root_id": "root",
        "is_folder": True,
    }


def test_navigates_to_folder_with_session_context() -> None:
    atlas = AtlasDouble()
    atlas.results.append(Result(True, {"entry": _folder("python", "Atlas Project/04 - Python")}))
    response = GoogleDriveConversationController().handle(
        atlas, "Ve a 04 - Python", session_id="telegram-7"
    )
    assert response.handled is True
    assert atlas.calls[0][0] == "drive.cd"
    assert atlas.calls[0][2]["session_id"] == "telegram-7"


def test_moves_to_parent_and_root() -> None:
    controller = GoogleDriveConversationController()
    atlas = AtlasDouble()
    atlas.results.extend([
        Result(True, {"entry": _folder("python", "Atlas Project/04 - Python")}),
        Result(True, {"entry": _folder("root", "Atlas Project")}),
    ])
    assert controller.handle(atlas, "Sube una carpeta").handled
    assert atlas.calls[0][1]["path"] == ".."
    assert controller.handle(atlas, "Vuelve a Atlas Project").handled
    assert atlas.calls[1][1]["path"] == "/"


def test_updates_named_folder_recursively() -> None:
    atlas = AtlasDouble()
    atlas.results.extend([
        Result(True, {"entry": _folder("python", "Atlas Project/04 - Python")}),
        Result(True, {"document_count": 5, "chunk_count": 10}),
    ])
    response = GoogleDriveConversationController().handle(
        atlas, "Actualiza el índice de 04 - Python y sus subcarpetas"
    )
    assert response.handled
    assert [call[0] for call in atlas.calls] == ["drive.resolve_path", "documents.index.sync_scope"]
    assert atlas.calls[1][1]["target_folder_id"] == "python"
    assert atlas.calls[1][1]["recursive"] is True


def test_updates_current_folder_without_changing_location() -> None:
    atlas = AtlasDouble()
    atlas.results.extend([
        Result(True, {"entry": _folder("core", "Atlas Project/04 - Python/atlas_core")}),
        Result(True, {"document_count": 2, "chunk_count": 3}),
    ])
    response = GoogleDriveConversationController().handle(atlas, "Actualiza el índice de esta carpeta")
    assert response.handled
    assert atlas.calls[0][0] == "drive.pwd"
    assert atlas.calls[1][0] == "documents.index.sync_scope"
    assert atlas.calls[1][1]["target_folder_id"] == "core"
    assert atlas.calls[1][1]["recursive"] is False


def test_updates_single_file() -> None:
    atlas = AtlasDouble()
    file_entry = {**_folder("file", "Atlas Project/semantic_index.py"), "is_folder": False}
    atlas.results.extend([
        Result(True, {"entry": file_entry}),
        Result(True, {"document_count": 1, "chunk_count": 2}),
    ])
    response = GoogleDriveConversationController().handle(
        atlas, "Actualiza el índice de semantic_index.py"
    )
    assert response.handled
    assert atlas.calls[1][1]["target_file_id"] == "file"


def test_updates_only_named_target() -> None:
    atlas = AtlasDouble()
    atlas.results.extend([
        Result(True, {"entry": _folder("memory", "Atlas Project/04 - Python/atlas_core/memory")}),
        Result(True, {"document_count": 1, "chunk_count": 1}),
    ])
    response = GoogleDriveConversationController().handle(atlas, "Actualiza solo memory")
    assert response.handled
    assert atlas.calls[1][1]["target_folder_id"] == "memory"
    assert atlas.calls[1][1]["recursive"] is False


def test_local_search_passes_current_scope_before_retrieval() -> None:
    atlas = AtlasDouble()
    atlas.results.extend([
        Result(True, {"entry": _folder("core", "Atlas Project/04 - Python/atlas_core")}),
        Result(True, {"matches": []}),
    ])
    response = GoogleDriveConversationController().handle(
        atlas, "Busca OAuth solo en la carpeta actual"
    )
    assert response.handled
    assert atlas.calls[1][1]["scope"] == {
        "type": "current", "target_id": "core", "root_folder_id": "root"
    }


def test_global_search_does_not_change_current_folder() -> None:
    atlas = AtlasDouble()
    atlas.results.append(Result(True, {"matches": []}))
    response = GoogleDriveConversationController().handle(atlas, "Busca OAuth en todo Drive")
    assert response.handled
    assert [call[0] for call in atlas.calls] == ["documents.index.search"]
    assert atlas.calls[0][1]["scope"] == {"type": "global"}


def test_ambiguous_path_can_be_selected_by_number() -> None:
    controller = GoogleDriveConversationController()
    atlas = AtlasDouble()
    candidates = [
        _folder("a", "Atlas Project/A/duplicada"),
        _folder("b", "Atlas Project/B/duplicada"),
    ]
    atlas.results.extend([
        Result(False, {"candidates": candidates}, "Ruta ambigua", "ambiguous"),
        Result(True, {"entry": candidates[1]}),
    ])
    first = controller.handle(atlas, "Ve a duplicada", session_id="s")
    second = controller.handle(atlas, "El segundo", session_id="s")
    assert "ambigua" in first.message
    assert second.handled
    assert atlas.calls[1][1] == {"folder_id": "b"}


def test_updates_arbitrary_branch_and_all_subfolders_without_index_word() -> None:
    atlas = AtlasDouble()
    atlas.results.extend([
        Result(True, {"entry": _folder("pc", "Atlas Project/02 - PC")}),
        Result(True, {"document_count": 3, "chunk_count": 4}),
    ])
    response = GoogleDriveConversationController().handle(
        atlas, "Actualiza 02 - PC y todas sus subcarpetas"
    )
    assert response.handled
    assert atlas.calls[1][1]["target_folder_id"] == "pc"
    assert atlas.calls[1][1]["recursive"] is True


def test_tree_of_named_branch_does_not_navigate_into_it() -> None:
    atlas = AtlasDouble()
    atlas.results.extend([
        Result(True, {"entry": _folder("backups", "Atlas Project/11 - Backups")}),
        Result(True, {"items": []}),
    ])
    response = GoogleDriveConversationController().handle(
        atlas, "Muéstrame el árbol de 11 - Backups"
    )
    assert response.handled
    assert [call[0] for call in atlas.calls] == ["drive.resolve_path", "drive.tree"]
    assert atlas.calls[1][1]["folder_id"] == "backups"
    assert all(call[0] != "drive.cd" for call in atlas.calls)


@pytest.mark.parametrize(
    "phrase",
    [
        "Actualiza solo esta carpeta",
        "Actualiza esta carpeta sin entrar en sus subcarpetas",
    ],
)
def test_current_folder_variants_are_non_recursive(phrase: str) -> None:
    atlas = AtlasDouble()
    atlas.results.extend([
        Result(True, {"entry": _folder("current", "Atlas Project/Carpeta cualquiera")}),
        Result(True, {"document_count": 1, "chunk_count": 1}),
    ])
    response = GoogleDriveConversationController().handle(atlas, phrase)
    assert response.handled
    assert atlas.calls[1][1]["target_folder_id"] == "current"
    assert atlas.calls[1][1]["recursive"] is False


@pytest.mark.parametrize(
    "phrase,scope_type",
    [
        ("Busca este término solo desde aquí", "current"),
        ("Busca este término en todo Atlas Project", "global"),
    ],
)
def test_search_scope_variants(phrase: str, scope_type: str) -> None:
    atlas = AtlasDouble()
    if scope_type == "current":
        atlas.results.append(Result(True, {"entry": _folder("current", "Atlas Project/02 - PC")}))
    atlas.results.append(Result(True, {"matches": []}))
    response = GoogleDriveConversationController().handle(atlas, phrase)
    assert response.handled
    search_call = atlas.calls[-1]
    assert search_call[0] == "documents.index.search"
    assert search_call[1]["scope"]["type"] == scope_type
