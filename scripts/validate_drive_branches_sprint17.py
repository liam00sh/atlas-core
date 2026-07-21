"""Validación real, anónima y de solo lectura de todos los ámbitos de Drive."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.atlas_tools import ATLAS_PROJECT_GOOGLE_DRIVE_FOLDER_ID
from tools.google_drive import DriveDocument, DriveItem, GoogleDriveClient
from tools.google_drive_index import GoogleDriveDocumentIndex
from tools.google_drive_oauth import GoogleDriveOAuthConfig, GoogleDriveOAuthProvider
from tools.google_drive_semantic import GoogleDriveSemanticIndex, OllamaEmbeddingClient
from tools.google_drive_structure import DriveNavigationService, DriveStructureEntry, GoogleDriveStructureIndex


SAFE_BRANCHES = (
    "Atlas Project",
    "01 - Raspberry",
    "02 - PC",
    "04 - Python",
    "11 - Backups",
    "Releases",
)


def _token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _safe_path(entry: DriveStructureEntry) -> str:
    parts = entry.relative_path.split("/")
    safe = []
    for position, part in enumerate(parts):
        if position == 0 or part in SAFE_BRANCHES:
            safe.append(part)
        else:
            safe.append(f"[folder-{_token(entry.ancestor_ids[position - 1] if position - 1 < len(entry.ancestor_ids) else entry.file_id)}]")
    return "/".join(safe)


class MeasuredClient:
    def __init__(self, client: GoogleDriveClient) -> None:
        self.client = client
        self.root_folder_id = getattr(client, "root_folder_id", None)
        self.reset()

    def reset(self) -> None:
        self.list_calls = 0
        self.read_calls = 0
        self.metadata_calls = 0

    def is_available(self) -> bool:
        return self.client.is_available()

    def list_folder(self, folder_id: str | None, *, limit: int) -> list[DriveItem]:
        self.list_calls += 1
        return self.client.list_folder(folder_id, limit=limit)

    def read_document(self, file_id: str, *, max_chars: int) -> DriveDocument:
        self.read_calls += 1
        return self.client.read_document(file_id, max_chars=max_chars)

    def get_item(self, file_id: str) -> DriveItem:
        self.metadata_calls += 1
        return self.client.get_item(file_id)

    def search_documents(self, query: str, *, limit: int, parent_id: str | None = None):
        return self.client.search_documents(query, limit=limit, parent_id=parent_id)

    def search_content(self, query: str, *, limit: int, max_documents: int, context_chars: int):
        return self.client.search_content(query, limit=limit, max_documents=max_documents, context_chars=context_chars)


def _descendants(entries: dict[str, DriveStructureEntry], folder_id: str, recursive: bool) -> list[DriveStructureEntry]:
    if not recursive:
        return [entry for entry in entries.values() if entry.parent_id == folder_id]
    return [
        entry for entry in entries.values()
        if entry.parent_id == folder_id or folder_id in entry.ancestor_ids
    ]


def _scope_signature(index: GoogleDriveDocumentIndex, entries: dict[str, DriveStructureEntry], folder_id: str) -> dict[str, str]:
    payload = index.load()
    return {
        file_id: str(document.get("content_hash", ""))
        for file_id, document in payload["documents"].items()
        if file_id in entries and (
            entries[file_id].parent_id == folder_id or folder_id in entries[file_id].ancestor_ids
        )
    }


def _scope_chunk_count(index: GoogleDriveDocumentIndex, entries: dict[str, DriveStructureEntry], folder_id: str) -> int:
    ids = set(_scope_signature(index, entries, folder_id))
    return sum(
        len(document.get("chunks", []))
        for file_id, document in index.load()["documents"].items()
        if file_id in ids
    )


def _branch_metrics(
    name: str,
    folder: DriveStructureEntry,
    *,
    client: MeasuredClient,
    entries: dict[str, DriveStructureEntry],
    navigation: DriveNavigationService,
    index: GoogleDriveDocumentIndex,
    semantic: GoogleDriveSemanticIndex,
    identity: dict[str, str],
) -> dict[str, Any]:
    started = perf_counter()
    resolved = navigation.resolve_path(folder.relative_path, **identity)
    cd = navigation.cd(folder.relative_path, **identity)
    state = navigation.state(**identity)
    pwd_matches = state.current_folder_id == folder.file_id
    listed = navigation.list_current(**identity)
    tree = navigation.tree(depth=3, include_files=True, **identity)
    navigation.cd("/", **identity)

    descendants = _descendants(entries, folder.file_id, True)
    files = [entry for entry in descendants if not entry.is_folder]
    indexable = [entry for entry in files if index._is_indexable_file(DriveItem(
        entry.file_id, entry.name, entry.mime_type, entry.modified_time,
        entry.parent_id, size_bytes=entry.size, is_folder=False,
    ))]

    client.reset()
    recursive_stats = index.sync_scope(
        client,
        root_folder_id=identity["root_folder_id"],
        target_folder_id=folder.file_id,
        recursive=True,
        drive_account_id=identity["drive_account_id"],
        owner_user_id=identity["user_id"],
        structure_entries=entries,
        max_items=5000,
        folder_limit=1000,
    )
    recursive_calls = client.list_calls
    recursive_downloads = client.read_calls

    client.reset()
    direct_stats = index.sync_scope(
        client,
        root_folder_id=identity["root_folder_id"],
        target_folder_id=folder.file_id,
        recursive=False,
        drive_account_id=identity["drive_account_id"],
        owner_user_id=identity["user_id"],
        structure_entries=entries,
        max_items=5000,
        folder_limit=1000,
    )

    scope = {
        "type": "subtree",
        "target_id": folder.file_id,
        "root_folder_id": identity["root_folder_id"],
        "drive_account_id": identity["drive_account_id"],
        "user_id": identity["user_id"],
    }
    lexical = index.search_chunks("Atlas", limit=5, scope=scope)
    semantic_stats = semantic.sync(scope=scope)
    semantic_matches = semantic.search("Atlas", limit=5, scope=scope)
    current_scope = {**scope, "type": "current"}
    current_matches = index.search_chunks("Atlas", limit=5, scope=current_scope)

    return {
        "label": name,
        "folder_id": _token(folder.file_id),
        "relative_path": folder.relative_path if name in SAFE_BRANCHES else _safe_path(folder),
        "depth": len(folder.ancestor_ids),
        "resolve_path": resolved.status,
        "cd": cd.status,
        "pwd_matches": pwd_matches,
        "list_entries": len(listed),
        "tree_entries_depth_3": len(tree),
        "folders_listed_remote": recursive_calls,
        "files_checked": len(files),
        "files_indexable": len(indexable),
        "files_non_indexable": len(files) - len(indexable),
        "files_downloaded": recursive_downloads,
        "files_unchanged": recursive_stats["unchanged"],
        "scope_fragments": _scope_chunk_count(index, entries, folder.file_id),
        "embeddings_generated": semantic_stats["embedded"],
        "embeddings_reused": semantic_stats["unchanged"],
        "entries_removed": recursive_stats["removed"],
        "errors": len(recursive_stats["errors"]),
        "recursive_complete": recursive_stats["discovery_complete"],
        "non_recursive_files_checked": direct_stats["discovered"],
        "non_recursive_removed": direct_stats["removed"],
        "lexical_subtree_results": len(lexical),
        "semantic_subtree_results": len(semantic_matches),
        "current_results": len(current_matches),
        "elapsed_seconds": round(perf_counter() - started, 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    config = GoogleDriveOAuthConfig.default(
        PROJECT_ROOT, root_folder_id=ATLAS_PROJECT_GOOGLE_DRIVE_FOLDER_ID
    )
    real_client = GoogleDriveOAuthProvider(config).build_client(interactive=False)
    if real_client is None:
        raise RuntimeError("No hay sesión OAuth guardada.")
    client = MeasuredClient(real_client)

    with TemporaryDirectory(prefix="atlas-drive-validation-") as temporary:
        temporary_path = Path(temporary)
        structure = GoogleDriveStructureIndex(temporary_path / "structure.json")
        structure_started = perf_counter()
        structure_stats = structure.sync(
            client,
            user_id="validation-user",
            drive_account_id="validation-account",
            root_folder_id=ATLAS_PROJECT_GOOGLE_DRIVE_FOLDER_ID,
            root_folder_name="Atlas Project",
            force=True,
        )
        structure_elapsed = perf_counter() - structure_started
        entries = structure.entries(
            user_id="validation-user",
            drive_account_id="validation-account",
            root_folder_id=ATLAS_PROJECT_GOOGLE_DRIVE_FOLDER_ID,
        )
        navigation = DriveNavigationService(structure)
        identity = {
            "user_id": "validation-user",
            "session_id": "validation-session",
            "drive_account_id": "validation-account",
            "root_folder_id": ATLAS_PROJECT_GOOGLE_DRIVE_FOLDER_ID,
            "root_folder_name": "Atlas Project",
        }
        root = entries[ATLAS_PROJECT_GOOGLE_DRIVE_FOLDER_ID]
        root_children = {entry.name: entry for entry in entries.values() if entry.parent_id == root.file_id and entry.is_folder}
        missing = [name for name in SAFE_BRANCHES[1:] if name not in root_children]
        if missing:
            raise RuntimeError("Faltan ramas obligatorias: " + ", ".join(missing))

        folders = [entry for entry in entries.values() if entry.is_folder and entry.traversal_status == "available"]
        deep = max(folders, key=lambda entry: len(entry.ancestor_ids))
        second_level = next((entry for entry in folders if len(entry.ancestor_ids) == 2), deep)
        child_counts = Counter(entry.parent_id for entry in entries.values())
        empty = next((entry for entry in folders if child_counts[entry.file_id] == 0 and entry.file_id != root.file_id), None)

        def folder_file_classes(folder: DriveStructureEntry) -> tuple[int, int]:
            scoped_files = [entry for entry in _descendants(entries, folder.file_id, True) if not entry.is_folder]
            supported = sum(
                document_index_probe._is_indexable_file(DriveItem(
                    entry.file_id, entry.name, entry.mime_type, entry.modified_time,
                    entry.parent_id, size_bytes=entry.size,
                ))
                for entry in scoped_files
            )
            return supported, len(scoped_files) - supported

        document_index_probe = GoogleDriveDocumentIndex(temporary_path / "policy-probe.json")
        indexable_folder = next(
            (folder for folder in folders if folder_file_classes(folder)[0] > 0),
            None,
        )
        non_indexable_folder = next(
            (
                folder for folder in folders
                if folder_file_classes(folder)[0] == 0 and folder_file_classes(folder)[1] > 0
            ),
            None,
        )

        document_index = GoogleDriveDocumentIndex(temporary_path / "documents.json")
        client.reset()
        global_started = perf_counter()
        global_stats = document_index.sync_scope(
            client,
            root_folder_id=root.file_id,
            target_folder_id=root.file_id,
            recursive=True,
            drive_account_id=identity["drive_account_id"],
            owner_user_id=identity["user_id"],
            structure_entries=entries,
            max_items=5000,
            folder_limit=1000,
        )
        global_list_calls = client.list_calls
        global_elapsed = perf_counter() - global_started
        semantic = GoogleDriveSemanticIndex(
            temporary_path / "semantic.json",
            document_index,
            OllamaEmbeddingClient(timeout=180),
        )
        semantic_started = perf_counter()
        global_semantic = semantic.sync(scope={
            "type": "global",
            "root_folder_id": root.file_id,
            "drive_account_id": identity["drive_account_id"],
            "user_id": identity["user_id"],
        })
        global_semantic_elapsed = perf_counter() - semantic_started

        branch_entries = [("Atlas Project", root)] + [(name, root_children[name]) for name in SAFE_BRANCHES[1:]]
        branch_results = {}
        for name, folder in branch_entries:
            print(f"Validating {name}...", flush=True)
            branch_results[name] = _branch_metrics(
                name, folder, client=client, entries=entries, navigation=navigation,
                index=document_index, semantic=semantic, identity=identity,
            )

        special_results = {
            "second_level": _branch_metrics(
                "second-level-anonymized", second_level, client=client, entries=entries,
                navigation=navigation, index=document_index, semantic=semantic, identity=identity,
            ),
            "deep_folder": _branch_metrics(
                "deep-folder-anonymized", deep, client=client, entries=entries,
                navigation=navigation, index=document_index, semantic=semantic, identity=identity,
            ),
        }
        if empty is not None:
            special_results["empty_folder"] = _branch_metrics(
                "empty-folder-anonymized", empty, client=client, entries=entries,
                navigation=navigation, index=document_index, semantic=semantic, identity=identity,
            )
        if indexable_folder is not None:
            special_results["indexable_folder"] = _branch_metrics(
                "indexable-folder-anonymized", indexable_folder, client=client, entries=entries,
                navigation=navigation, index=document_index, semantic=semantic, identity=identity,
            )
        if non_indexable_folder is not None:
            special_results["non_indexable_folder"] = _branch_metrics(
                "non-indexable-folder-anonymized", non_indexable_folder, client=client, entries=entries,
                navigation=navigation, index=document_index, semantic=semantic, identity=identity,
            )

        outside_main = [
            entry for entry in entries.values()
            if not entry.is_folder
            and not any(name in entry.ancestor_names for name in ("00 - Documentación", "04 - Python"))
            and document_index._is_indexable_file(DriveItem(
                entry.file_id, entry.name, entry.mime_type, entry.modified_time,
                entry.parent_id, size_bytes=entry.size,
            ))
        ]
        file_result: dict[str, Any] = {"available": False}
        if outside_main:
            item_entry = outside_main[0]
            client.reset()
            started = perf_counter()
            file_stats = document_index.sync_scope(
                client,
                root_folder_id=root.file_id,
                target_file_id=item_entry.file_id,
                drive_account_id=identity["drive_account_id"],
                owner_user_id=identity["user_id"],
                structure_entries=entries,
            )
            file_result = {
                "available": True,
                "file_id": _token(item_entry.file_id),
                "branch": next((name for name in SAFE_BRANCHES if name in item_entry.ancestor_names), "other"),
                "unchanged": file_stats["unchanged"],
                "downloaded": client.read_calls,
                "metadata_calls": client.metadata_calls,
                "removed": file_stats["removed"],
                "elapsed_seconds": round(perf_counter() - started, 6),
            }

        preservation: dict[str, Any] = {}
        ordered_scopes = ["00 - Documentación", "01 - Raspberry", "02 - PC", "04 - Python", "11 - Backups", "Releases"]
        available_scopes = {name: root_children[name] for name in ordered_scopes if name in root_children}
        before = {name: _scope_signature(document_index, entries, folder.file_id) for name, folder in available_scopes.items()}
        for target_name in ("02 - PC", "11 - Backups"):
            target = available_scopes[target_name]
            document_index.sync_scope(
                client, root_folder_id=root.file_id, target_folder_id=target.file_id,
                recursive=True, drive_account_id=identity["drive_account_id"],
                owner_user_id=identity["user_id"], structure_entries=entries,
                max_items=5000, folder_limit=1000,
            )
            after = {name: _scope_signature(document_index, entries, folder.file_id) for name, folder in available_scopes.items()}
            preservation[target_name] = {
                "other_scopes_unchanged": all(after[name] == before[name] for name in available_scopes if name != target_name),
                "compared_scopes": [name for name in available_scopes if name != target_name],
                "target_count_before": len(before[target_name]),
                "target_count_after": len(after[target_name]),
            }
            before = after

        deep_parent = entries.get(deep.parent_id or "")
        sibling_ids = {
            entry.file_id for entry in entries.values()
            if deep_parent is not None and entry.parent_id == deep_parent.file_id and entry.file_id != deep.file_id
        }
        sibling_before = {
            file_id: document.get("content_hash")
            for file_id, document in document_index.load()["documents"].items()
            if file_id in sibling_ids or any(sibling in entries.get(file_id, deep).ancestor_ids for sibling in sibling_ids)
        }
        document_index.sync_scope(
            client, root_folder_id=root.file_id, target_folder_id=deep.file_id,
            recursive=True, drive_account_id=identity["drive_account_id"],
            owner_user_id=identity["user_id"], structure_entries=entries,
            max_items=5000, folder_limit=1000,
        )
        sibling_after = {
            file_id: document.get("content_hash")
            for file_id, document in document_index.load()["documents"].items()
            if file_id in sibling_ids or any(sibling in entries.get(file_id, deep).ancestor_ids for sibling in sibling_ids)
        }
        preservation["deep_folder"] = {
            "folder_id": _token(deep.file_id),
            "depth": len(deep.ancestor_ids),
            "sibling_documents_unchanged": sibling_before == sibling_after,
            "sibling_document_count": len(sibling_before),
        }

        mime_counts = Counter(entry.mime_type for entry in entries.values() if not entry.is_folder)
        non_indexable_mimes = Counter(
            entry.mime_type for entry in entries.values()
            if not entry.is_folder and not document_index._is_indexable_file(DriveItem(
                entry.file_id, entry.name, entry.mime_type, entry.modified_time,
                entry.parent_id, size_bytes=entry.size,
            ))
        )
        result = {
            "mode": "real_read_only",
            "root": "Atlas Project",
            "oauth_scope": "drive.readonly",
            "ids_anonymized": True,
            "content_recorded": False,
            "structure": {
                **structure_stats,
                "elapsed_seconds": round(structure_elapsed, 6),
                "maximum_real_depth": max(len(entry.ancestor_ids) for entry in entries.values()),
            },
            "global_index": {
                "elapsed_seconds": round(global_elapsed, 6),
                "remote_list_calls": global_list_calls,
                "files_checked": global_stats["discovered"],
                "downloaded": global_stats["downloaded"],
                "unchanged": global_stats["unchanged"],
                "documents": global_stats["document_count"],
                "fragments": global_stats["chunk_count"],
                "excluded": global_stats["excluded"],
                "errors": len(global_stats["errors"]),
            },
            "global_semantic": {
                "elapsed_seconds": round(global_semantic_elapsed, 6),
                "generated": global_semantic["embedded"],
                "reused": global_semantic["unchanged"],
            },
            "branches": branch_results,
            "special_scopes": special_results,
            "individual_file": file_result,
            "preservation": preservation,
            "mime_counts": dict(sorted(mime_counts.items())),
            "non_indexable_mime_counts": dict(sorted(non_indexable_mimes.items())),
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
