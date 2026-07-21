"""Benchmark reproducible de Drive para la ampliacion del Sprint 17.

Usa exclusivamente el alcance OAuth de solo lectura de Atlas. No imprime IDs,
contenido, credenciales ni rutas de archivos individuales.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
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
from tools.google_drive_structure import GoogleDriveStructureIndex


@dataclass
class Counters:
    list_calls: int = 0
    read_calls: int = 0
    metadata_calls: int = 0


class MeasuredClient:
    def __init__(self, client: GoogleDriveClient, *, virtual_root: str | None = None) -> None:
        self.client = client
        self.virtual_root = virtual_root
        self.root_folder_id = getattr(client, "root_folder_id", None)
        self.counters = Counters()

    def is_available(self) -> bool:
        return self.client.is_available()

    def list_folder(self, folder_id: str | None, *, limit: int) -> list[DriveItem]:
        self.counters.list_calls += 1
        return self.client.list_folder(
            self.virtual_root if folder_id is None and self.virtual_root else folder_id,
            limit=limit,
        )

    def read_document(self, file_id: str, *, max_chars: int) -> DriveDocument:
        self.counters.read_calls += 1
        return self.client.read_document(file_id, max_chars=max_chars)

    def get_item(self, file_id: str) -> DriveItem:
        self.counters.metadata_calls += 1
        return self.client.get_item(file_id)

    def search_documents(self, query: str, *, limit: int, parent_id: str | None = None) -> list[DriveItem]:
        return self.client.search_documents(query, limit=limit, parent_id=parent_id)

    def search_content(self, query: str, *, limit: int, max_documents: int, context_chars: int) -> list[Any]:
        return self.client.search_content(
            query,
            limit=limit,
            max_documents=max_documents,
            context_chars=context_chars,
        )


def _run_sync(client: GoogleDriveClient, target: Path) -> tuple[dict[str, Any], GoogleDriveDocumentIndex]:
    index = GoogleDriveDocumentIndex(target)
    start = perf_counter()
    stats = index.sync(client, max_items=5000, folder_limit=1000)
    stats["elapsed_seconds"] = round(perf_counter() - start, 6)
    stats["remote_list_calls"] = client.counters.list_calls  # type: ignore[attr-defined]
    stats["remote_downloads"] = client.counters.read_calls  # type: ignore[attr-defined]
    return stats, index


def _sanitize(stats: dict[str, Any]) -> dict[str, Any]:
    result = dict(stats)
    result.pop("path", None)
    errors = result.pop("errors", [])
    result["error_count"] = len(errors)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("baseline", "results"), default="baseline")
    args = parser.parse_args()
    project_root = PROJECT_ROOT
    config = GoogleDriveOAuthConfig.default(
        project_root,
        root_folder_id=ATLAS_PROJECT_GOOGLE_DRIVE_FOLDER_ID,
    )
    provider = GoogleDriveOAuthProvider(config)
    client = provider.build_client(interactive=False)
    if client is None:
        raise RuntimeError("No hay una sesion OAuth guardada disponible.")

    root_items = client.list_folder(None, limit=1000)
    folders = {item.name: item for item in root_items if item.is_folder}
    targets = {
        "00_documentation": next((item for name, item in folders.items() if name.startswith("00 -")), None),
        "04_python": next((item for name, item in folders.items() if name.startswith("04 -")), None),
    }

    result: dict[str, Any] = {
        "mode": "real_read_only",
        "root_name": "Atlas Project",
        "oauth_scope": "drive.readonly",
        "real_mutations_induced": False,
        "scenarios": {},
        "benchmark_phase": args.mode,
    }

    with TemporaryDirectory(prefix="atlas-drive-benchmark-") as temporary:
        temp = Path(temporary)
        global_client = MeasuredClient(client)
        global_stats, global_index = _run_sync(global_client, temp / "global.json")
        result["scenarios"]["global_first"] = _sanitize(global_stats)

        global_client.counters = Counters()
        start = perf_counter()
        second = global_index.sync(global_client, max_items=5000, folder_limit=1000)
        second["elapsed_seconds"] = round(perf_counter() - start, 6)
        second["remote_list_calls"] = global_client.counters.list_calls
        second["remote_downloads"] = global_client.counters.read_calls
        result["scenarios"]["global_second_unchanged"] = _sanitize(second)

        if args.mode == "results":
            structure_client = MeasuredClient(client)
            structure = GoogleDriveStructureIndex(temp / "structure.json", ttl_seconds=120)
            started = perf_counter()
            structure_stats = structure.sync(
                structure_client,
                user_id="benchmark-user",
                drive_account_id="benchmark-account",
                root_folder_id=ATLAS_PROJECT_GOOGLE_DRIVE_FOLDER_ID,
                root_folder_name="Atlas Project",
                force=True,
            )
            structure_stats["elapsed_seconds"] = round(perf_counter() - started, 6)
            structure_stats["remote_list_calls"] = structure_client.counters.list_calls
            result["scenarios"]["structure_first"] = structure_stats

            structure_client.counters = Counters()
            started = perf_counter()
            cached_structure = structure.sync(
                structure_client,
                user_id="benchmark-user",
                drive_account_id="benchmark-account",
                root_folder_id=ATLAS_PROJECT_GOOGLE_DRIVE_FOLDER_ID,
                root_folder_name="Atlas Project",
            )
            cached_structure["elapsed_seconds"] = round(perf_counter() - started, 6)
            cached_structure["remote_list_calls"] = structure_client.counters.list_calls
            result["scenarios"]["structure_cached"] = cached_structure

        partial_indexes: list[tuple[str, GoogleDriveDocumentIndex]] = []
        for label, folder in targets.items():
            if folder is None:
                result["scenarios"][label] = {"available": False}
                continue
            measured = MeasuredClient(client, virtual_root=folder.item_id)
            stats, index = _run_sync(measured, temp / f"{label}.json")
            result["scenarios"][label] = _sanitize(stats)
            partial_indexes.append((label, index))
            if args.mode == "results":
                global_client.counters = Counters()
                started = perf_counter()
                incremental = global_index.sync_scope(
                    global_client,
                    root_folder_id=ATLAS_PROJECT_GOOGLE_DRIVE_FOLDER_ID,
                    target_folder_id=folder.item_id,
                    recursive=True,
                    max_items=5000,
                    folder_limit=1000,
                    owner_user_id="benchmark-user",
                    drive_account_id="benchmark-account",
                )
                incremental["elapsed_seconds"] = round(perf_counter() - started, 6)
                incremental["remote_list_calls"] = global_client.counters.list_calls
                incremental["remote_downloads"] = global_client.counters.read_calls
                result["scenarios"][f"{label}_incremental_after_global"] = _sanitize(incremental)

        candidates = sorted(
            (
                (label, index.status()["document_count"], index)
                for label, index in partial_indexes
                if index.status()["document_count"]
            ),
            key=lambda entry: entry[1],
        )
        if candidates:
            label, count, small_index = candidates[0]
            embedder = OllamaEmbeddingClient(timeout=180)
            semantic = GoogleDriveSemanticIndex(temp / "semantic.json", small_index, embedder)
            start = perf_counter()
            semantic_stats = semantic.sync(batch_size=16)
            semantic_stats["elapsed_seconds"] = round(perf_counter() - start, 6)
            semantic_stats["source_scope"] = label
            semantic_stats["source_documents"] = count
            result["scenarios"]["semantic_small_scope"] = _sanitize(semantic_stats)

            start = perf_counter()
            semantic_second = semantic.sync(batch_size=16)
            semantic_second["elapsed_seconds"] = round(perf_counter() - start, 6)
            semantic_second["source_scope"] = label
            result["scenarios"]["semantic_second_unchanged"] = _sanitize(semantic_second)

        docs = global_index.load().get("documents", {})
        if docs:
            first_id = next(iter(docs))
            measured_file = MeasuredClient(client)
            start = perf_counter()
            if args.mode == "baseline":
                document = measured_file.read_document(first_id, max_chars=300_000)
                chunks = global_index._chunks(document.content)
                result["scenarios"]["single_file_read_and_chunk"] = {
                    "elapsed_seconds": round(perf_counter() - start, 6),
                    "remote_downloads": measured_file.counters.read_calls,
                    "chunks_generated": len(chunks),
                }
            else:
                file_stats = global_index.sync_scope(
                    measured_file,
                    root_folder_id=ATLAS_PROJECT_GOOGLE_DRIVE_FOLDER_ID,
                    target_file_id=first_id,
                    owner_user_id="benchmark-user",
                    drive_account_id="benchmark-account",
                )
                file_stats["elapsed_seconds"] = round(perf_counter() - start, 6)
                file_stats["remote_downloads"] = measured_file.counters.read_calls
                file_stats["remote_metadata_calls"] = measured_file.counters.metadata_calls
                result["scenarios"]["single_file_incremental"] = _sanitize(file_stats)

    result["scenarios"]["modified_renamed_moved"] = {
        "executed_on_real_drive": False,
        "reason": "La integracion conserva drive.readonly; no se inducen cambios remotos para un benchmark.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
