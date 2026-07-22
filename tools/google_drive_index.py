"""
===============================================================================
Proyecto Atlas
Archivo: tools/google_drive_index.py

Descripción:
    Índice documental local y persistente para Google Drive.

    El índice es reconstruible y está separado de la memoria personal.
    Google Drive continúa utilizándose exclusivamente en modo lectura.
===============================================================================
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

from tools.base_tool import BaseTool, ToolRisk
from tools.capability import Capability
from tools.context import ToolContext
from tools.google_drive import (
    DriveDocument,
    DriveItem,
    GoogleDriveClient,
)
from tools.result import ToolResult


INDEX_VERSION = 4
CHUNKER_VERSION = "fixed_chars_v2_priority_policy"

GOOGLE_FOLDER_MIME = "application/vnd.google-apps.folder"
GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
GOOGLE_SHEET_MIME = "application/vnd.google-apps.spreadsheet"
GOOGLE_SLIDES_MIME = "application/vnd.google-apps.presentation"

INDEXABLE_APPLICATION_MIME_TYPES = frozenset(
    {
        "application/json",
        "application/ld+json",
        "application/xml",
        "application/x-yaml",
        "application/yaml",
    }
)

EXCLUDED_FOLDER_NAMES = frozenset(
    {
        ".git",
        ".agents",
        ".pytest_cache",
        "__pycache__",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        "venv",
        "node_modules",
        "logs",
    }
)

EXCLUDED_FILE_SUFFIXES = frozenset(
    {
        ".zip",
        ".7z",
        ".rar",
        ".exe",
        ".dll",
        ".iso",
        ".img",
        ".bin",
        ".pyc",
        ".log",
        ".tmp",
        ".part",
        ".crdownload",
        ".download",
    }
)


@dataclass(frozen=True, slots=True)
class IndexedChunk:
    """Fragmento persistido de un documento."""

    text: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class IndexedDocument:
    """Documento textual almacenado en el índice."""

    item: DriveItem
    content_hash: str
    indexed_at: str
    chunks: tuple[IndexedChunk, ...]


@dataclass(frozen=True, slots=True)
class IndexSearchMatch:
    """Resultado procedente del índice local."""

    item: DriveItem
    snippet: str
    score: float
    chunk_index: int


@dataclass(frozen=True, slots=True)
class IndexChunkMatch:
    """Fragmento individual recuperado para RAG."""

    item: DriveItem
    text: str
    score: float
    chunk_index: int


class GoogleDriveDocumentIndex:
    """Gestiona la persistencia, sincronización y búsqueda del índice."""

    DEFAULT_CHUNK_CHARS = 1200
    DEFAULT_OVERLAP_CHARS = 180
    DEFAULT_MAX_DOCUMENT_CHARS = 300_000

    def __init__(
        self,
        path: Path,
        *,
        chunk_chars: int = DEFAULT_CHUNK_CHARS,
        overlap_chars: int = DEFAULT_OVERLAP_CHARS,
        excluded_folder_names: frozenset[str] | set[str] | None = None,
    ) -> None:
        self.path = Path(path).resolve()
        self.chunk_chars = chunk_chars
        self.overlap_chars = overlap_chars
        self.excluded_folder_names = frozenset(
            name.strip().casefold()
            for name in (
                EXCLUDED_FOLDER_NAMES
                if excluded_folder_names is None
                else excluded_folder_names
            )
            if name.strip()
        )

        if chunk_chars < 200:
            raise ValueError(
                "Los fragmentos del índice deben tener al menos 200 caracteres."
            )
        if overlap_chars < 0 or overlap_chars >= chunk_chars:
            raise ValueError(
                "El solapamiento debe ser menor que el tamaño del fragmento."
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _normalize(value: str) -> str:
        normalized = unicodedata.normalize(
            "NFKD",
            value.casefold(),
        )
        return "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        )

    @classmethod
    def _terms(cls, query: str) -> list[str]:
        stopwords = {
            "de", "del", "donde", "el", "en", "la", "las", "los",
            "por", "que", "qué", "se", "sobre", "un", "una", "y",
        }
        return list(
            dict.fromkeys(
                term
                for term in re.findall(
                    r"[\w-]+",
                    cls._normalize(query),
                )
                if len(term) >= 2 and term not in stopwords
            )
        )

    def _empty_payload(self) -> dict[str, Any]:
        return {
            "version": INDEX_VERSION,
            "updated_at": None,
            "root_folder_id": None,
            "documents": {},
            "file_states": {},
        }

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty_payload()

        try:
            payload = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return self._empty_payload()

        if payload.get("version") != INDEX_VERSION:
            return self._empty_payload()
        if not isinstance(payload.get("documents"), dict):
            return self._empty_payload()
        if not isinstance(payload.get("file_states"), dict):
            payload["file_states"] = {}
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        temporary = self.path.with_suffix(
            self.path.suffix + ".tmp"
        )
        temporary.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def clear(self) -> bool:
        if not self.path.exists():
            return False
        self.path.unlink()
        return True

    def status(self) -> dict[str, Any]:
        payload = self.load()
        documents = payload["documents"]
        chunk_count = sum(
            len(document.get("chunks", []))
            for document in documents.values()
        )
        return {
            "path": str(self.path),
            "exists": self.path.exists(),
            "version": payload["version"],
            "updated_at": payload.get("updated_at"),
            "root_folder_id": payload.get(
                "root_folder_id"
            ),
            "document_count": len(documents),
            "chunk_count": chunk_count,
        }

    def _chunks(self, content: str) -> tuple[IndexedChunk, ...]:
        cleaned = content.replace("\x00", "")
        if not cleaned.strip():
            return ()

        chunks: list[IndexedChunk] = []
        step = self.chunk_chars - self.overlap_chars
        start = 0

        while start < len(cleaned):
            end = min(
                len(cleaned),
                start + self.chunk_chars,
            )
            if end < len(cleaned):
                boundary = cleaned.rfind(
                    "\n",
                    start + 200,
                    end,
                )
                if boundary < 0:
                    boundary = cleaned.rfind(
                        " ",
                        start + 200,
                        end,
                    )
                if boundary > start:
                    end = boundary

            text = " ".join(
                cleaned[start:end].split()
            )
            if text:
                chunks.append(
                    IndexedChunk(
                        text=text,
                        start=start,
                        end=end,
                    )
                )

            if end >= len(cleaned):
                break
            start = max(
                start + step,
                end - self.overlap_chars,
            )

        return tuple(chunks)

    @staticmethod
    def _serialize_item(item: DriveItem) -> dict[str, Any]:
        return asdict(item)

    @staticmethod
    def _deserialize_item(data: dict[str, Any]) -> DriveItem:
        return DriveItem(**data)

    def _serialize_document(
        self,
        document: IndexedDocument,
    ) -> dict[str, Any]:
        return {
            "item": self._serialize_item(document.item),
            "content_hash": document.content_hash,
            "indexed_at": document.indexed_at,
            "chunks": [
                asdict(chunk)
                for chunk in document.chunks
            ],
            "policy": self._document_policy(
                document.item,
                str(getattr(document.item, "name", "")),
            ),
        }

    def _is_excluded_folder(self, item: DriveItem) -> bool:
        return (
            item.is_folder
            and item.name.strip().casefold()
            in self.excluded_folder_names
        )

    @staticmethod
    def _is_indexable_file(item: DriveItem) -> bool:
        if item.is_folder:
            return False

        suffix = Path(
            item.name
        ).suffix.casefold()
        if suffix in EXCLUDED_FILE_SUFFIXES:
            return False

        mime_type = item.mime_type.casefold()

        if mime_type in {
            GOOGLE_DOC_MIME,
            GOOGLE_SHEET_MIME,
            GOOGLE_SLIDES_MIME,
        }:
            return True

        if mime_type.startswith("text/"):
            return True

        return (
            mime_type
            in INDEXABLE_APPLICATION_MIME_TYPES
        )

    def _discover_items(
        self,
        client: GoogleDriveClient,
        *,
        max_items: int,
        folder_limit: int,
        target_folder_id: str | None = None,
        recursive: bool = True,
    ) -> tuple[list[DriveItem], int, bool]:
        queue: list[str | None] = [target_folder_id]
        visited_folders: set[str] = set()
        discovered: dict[str, DriveItem] = {}
        excluded = 0
        complete = True

        while queue and len(discovered) < max_items:
            folder_id = queue.pop(0)
            if folder_id is not None:
                if folder_id in visited_folders:
                    continue
                visited_folders.add(folder_id)

            children = client.list_folder(
                folder_id,
                limit=folder_limit,
            )
            if len(children) >= folder_limit:
                complete = False
            for item in children:
                if item.item_id in discovered:
                    continue

                if self._is_excluded_folder(item):
                    excluded += 1
                    continue

                if item.is_folder:
                    if recursive:
                        queue.append(item.item_id)
                    continue

                if not self._is_indexable_file(item):
                    excluded += 1
                    continue

                discovered[item.item_id] = item

                if len(discovered) >= max_items:
                    complete = False
                    break

        if queue:
            complete = False
        return list(discovered.values()), excluded, complete

    def sync(
        self,
        client: GoogleDriveClient,
        *,
        max_items: int = 500,
        folder_limit: int = 100,
        max_document_chars: int = DEFAULT_MAX_DOCUMENT_CHARS,
        force: bool = False,
    ) -> dict[str, Any]:
        """Mantiene el contrato global histórico sin convertirlo en parcial."""
        return self.sync_scope(
            client,
            max_items=max_items,
            folder_limit=folder_limit,
            max_document_chars=max_document_chars,
            force=force,
        )

    @staticmethod
    def _entry_value(entry: Any, name: str, default: Any = None) -> Any:
        if entry is None:
            return default
        if isinstance(entry, dict):
            return entry.get(name, default)
        return getattr(entry, name, default)

    @classmethod
    def _document_policy(cls, item: DriveItem, relative_path: str) -> dict[str, Any]:
        """Clasifica vigencia, autoridad y sensibilidad sin depender del contenido."""
        combined = cls._normalize(f"{relative_path} {item.name}")
        path_parts = [part for part in re.split(r"[\\/]", combined) if part]
        is_backup = any(token in combined for token in ("backup", "backups", "copia de seguridad", "releases"))
        is_historical = any(token in combined for token in ("historico", "historial", "antiguo", "archive", "archivado", "legacy"))
        is_patch = any(token in combined for token in ("patch", "parche", "fix", "correccion", "tmp", "final"))
        is_official = any(token in combined for token in ("documentacion oficial", "00 documentacion", "documentacion", "roadmap", "changelog", "manual"))
        is_release = any(token in combined for token in ("release", "version", "v0 ", "v1 "))
        if is_backup:
            document_class = "backup"
            authority = 0.35
        elif is_historical:
            document_class = "historical"
            authority = 0.45
        elif is_patch:
            document_class = "patch"
            authority = 0.60
        elif is_release:
            document_class = "release"
            authority = 0.85
        elif is_official:
            document_class = "official_active"
            authority = 1.00
        else:
            document_class = "personal_current"
            authority = 0.75
        return {
            "document_class": document_class,
            "authority_score": authority,
            "is_current_candidate": document_class in {"official_active", "release", "personal_current"},
            "is_backup": is_backup,
            "is_historical": is_historical,
            "path_parts": path_parts,
        }

    @staticmethod
    def _priority_bonus(document: dict[str, Any]) -> float:
        policy = document.get("policy", {})
        authority = float(policy.get("authority_score", 0.5) or 0.5)
        bonus = authority * 4.0
        if policy.get("is_current_candidate"):
            bonus += 2.0
        if policy.get("is_backup"):
            bonus -= 3.0
        if policy.get("is_historical"):
            bonus -= 2.0
        return bonus

    def _provenance(
        self,
        item: DriveItem,
        *,
        drive_account_id: str,
        owner_user_id: str | None,
        root_folder_id: str | None,
        scope_folder_id: str | None,
        structure_entries: dict[str, Any] | None,
    ) -> dict[str, Any]:
        entry = (structure_entries or {}).get(item.item_id)
        relative_path = self._entry_value(entry, "relative_path", item.name)
        access_user_ids = list(self._entry_value(entry, "access_user_ids", ()))
        if owner_user_id and owner_user_id not in access_user_ids:
            access_user_ids.append(owner_user_id)
        return {
            "drive_account_id": drive_account_id,
            "owner_user_id": owner_user_id,
            "root_folder_id": root_folder_id,
            "file_id": item.item_id,
            "file_name": item.name,
            "parent_folder_id": item.parent_id,
            "relative_path": relative_path,
            "ancestor_ids": list(self._entry_value(entry, "ancestor_ids", ())),
            "ancestor_names": list(self._entry_value(entry, "ancestor_names", ())),
            "scope_folder_id": scope_folder_id,
            "modified_time": item.modified_time,
            "content_hash": None,
            "chunker_version": CHUNKER_VERSION,
            "access_user_ids": access_user_ids,
            "visibility": self._entry_value(entry, "visibility", "owner_only" if owner_user_id else "root_scoped"),
        }

    @staticmethod
    def _belongs_to_scope(
        document: dict[str, Any],
        *,
        target_folder_id: str | None,
        recursive: bool,
        target_file_id: str | None,
    ) -> bool:
        item = document.get("item", {})
        if target_file_id is not None:
            return item.get("item_id") == target_file_id
        if target_folder_id is None:
            return True
        provenance = document.get("provenance", {})
        if recursive:
            return (
                item.get("parent_id") == target_folder_id
                or target_folder_id in provenance.get("ancestor_ids", [])
            )
        return item.get("parent_id") == target_folder_id

    def sync_scope(
        self,
        client: GoogleDriveClient,
        *,
        root_folder_id: str | None = None,
        target_folder_id: str | None = None,
        recursive: bool = True,
        target_file_id: str | None = None,
        target_file_item: DriveItem | None = None,
        drive_account_id: str = "default",
        owner_user_id: str | None = None,
        structure_entries: dict[str, Any] | None = None,
        max_items: int = 500,
        folder_limit: int = 100,
        max_document_chars: int = DEFAULT_MAX_DOCUMENT_CHARS,
        force: bool = False,
    ) -> dict[str, Any]:
        """Actualiza una raíz, subárbol, carpeta directa o archivo sin borrar otros ámbitos."""
        if target_folder_id and target_file_id:
            raise ValueError("No se puede actualizar una carpeta y un archivo a la vez.")

        effective_root = root_folder_id or getattr(client, "root_folder_id", None)
        global_scope = target_file_id is None and (
            target_folder_id is None or target_folder_id == effective_root
        ) and recursive
        scope_folder_id = target_folder_id or effective_root
        payload = self.load()
        previous = payload["documents"]
        previous_states = payload.get("file_states", {})
        current: dict[str, Any] = {} if global_scope else dict(previous)
        current_states: dict[str, Any] = {} if global_scope else dict(previous_states)

        stats = {
            "discovered": 0,
            "indexed": 0,
            "updated": 0,
            "unchanged": 0,
            "skipped": 0,
            "excluded": 0,
            "removed": 0,
            "renamed": 0,
            "moved": 0,
            "downloaded": 0,
            "scope_folder_id": scope_folder_id,
            "target_file_id": target_file_id,
            "recursive": recursive,
            "global_scope": global_scope,
            "errors": [],
        }

        if target_file_id is not None:
            item = target_file_item
            if item is None and hasattr(client, "get_item"):
                item = client.get_item(target_file_id)  # type: ignore[attr-defined]
            if item is None:
                raise LookupError("No se han proporcionado metadatos seguros del archivo objetivo.")
            items, excluded = [item], 0
        else:
            items, excluded, discovery_complete = self._discover_items(
                client,
                max_items=max_items,
                folder_limit=folder_limit,
                target_folder_id=(None if global_scope else target_folder_id),
                recursive=recursive,
            )
        if target_file_id is not None:
            discovery_complete = True
        stats["discovered"] = len(items)
        stats["excluded"] = excluded
        stats["discovery_complete"] = discovery_complete
        discovered_ids = {item.item_id for item in items}

        for item in items:
            if item.is_folder:
                continue

            old = previous.get(item.item_id)
            old_item = old.get("item", {}) if old else {}
            if old and old_item.get("name") != item.name:
                stats["renamed"] += 1
            if old and old_item.get("parent_id") != item.parent_id:
                stats["moved"] += 1
            provenance = self._provenance(
                item,
                drive_account_id=drive_account_id,
                owner_user_id=owner_user_id,
                root_folder_id=effective_root,
                scope_folder_id=scope_folder_id,
                structure_entries=structure_entries,
            )
            same_revision = (
                not force
                and old is not None
                and old.get("item", {}).get("modified_time")
                == item.modified_time
                and old.get("item", {}).get("size_bytes") == item.size_bytes
                and old.get("chunker_version") == CHUNKER_VERSION
            )
            if same_revision:
                retained = dict(old)
                retained["item"] = self._serialize_item(item)
                retained["provenance"] = {
                    **provenance,
                    "content_hash": old.get("content_hash"),
                }
                retained["chunker_version"] = CHUNKER_VERSION
                retained["policy"] = self._document_policy(item, str(provenance.get("relative_path", item.name)))
                current[item.item_id] = retained
                current_states.pop(item.item_id, None)
                stats["unchanged"] += 1
                continue

            old_state = previous_states.get(item.item_id, {})
            if (
                not force
                and old is None
                and old_state.get("status") == "empty"
                and old_state.get("modified_time") == item.modified_time
                and old_state.get("size_bytes") == item.size_bytes
                and old_state.get("chunker_version") == CHUNKER_VERSION
            ):
                current_states[item.item_id] = old_state
                stats["unchanged"] += 1
                stats["skipped"] += 1
                continue

            try:
                drive_document: DriveDocument = (
                    client.read_document(
                        item.item_id,
                        max_chars=max_document_chars,
                    )
                )
                stats["downloaded"] += 1
            except (
                FileNotFoundError,
                IsADirectoryError,
                RuntimeError,
                UnicodeError,
                ValueError,
            ) as exception:
                stats["skipped"] += 1
                stats["errors"].append(
                    {
                        "item_id": item.item_id,
                        "name": item.name,
                        "error": str(exception),
                    }
                )
                if old is not None:
                    current[item.item_id] = old
                continue

            chunks = self._chunks(
                drive_document.content
            )
            if not chunks:
                stats["skipped"] += 1
                current_states[item.item_id] = {
                    "status": "empty",
                    "modified_time": item.modified_time,
                    "size_bytes": item.size_bytes,
                    "chunker_version": CHUNKER_VERSION,
                    "scope_folder_id": scope_folder_id,
                    "parent_folder_id": item.parent_id,
                    "ancestor_ids": provenance.get("ancestor_ids", []),
                    "root_folder_id": effective_root,
                    "drive_account_id": drive_account_id,
                    "owner_user_id": owner_user_id,
                }
                continue

            content_hash = hashlib.sha256(
                drive_document.content.encode(
                    "utf-8",
                    errors="replace",
                )
            ).hexdigest()

            indexed = IndexedDocument(
                item=drive_document.item,
                content_hash=content_hash,
                indexed_at=self._now(),
                chunks=chunks,
            )
            current[item.item_id] = (
                self._serialize_document(indexed)
            )
            current[item.item_id]["provenance"] = {
                **provenance,
                "content_hash": content_hash,
            }
            current[item.item_id]["policy"] = self._document_policy(
                item,
                str(provenance.get("relative_path", item.name)),
            )
            current[item.item_id]["chunker_version"] = CHUNKER_VERSION
            current_states.pop(item.item_id, None)

            if old is None:
                stats["indexed"] += 1
            else:
                stats["updated"] += 1

        if not discovery_complete:
            removed_ids: set[str] = set()
            removed_state_ids: set[str] = set()
            if global_scope:
                for item_id, document in previous.items():
                    current.setdefault(item_id, document)
                for item_id, state in previous_states.items():
                    current_states.setdefault(item_id, state)
        elif global_scope:
            removed_ids = set(previous) - set(current)
            removed_state_ids = set(previous_states) - set(current_states)
        else:
            removed_ids = {
                item_id for item_id, document in previous.items()
                if self._belongs_to_scope(
                    document,
                    target_folder_id=target_folder_id,
                    recursive=recursive,
                    target_file_id=target_file_id,
                ) and item_id not in discovered_ids
            }
            moved_outside_scope: set[str] = set()
            for item_id in tuple(removed_ids):
                entry = (structure_entries or {}).get(item_id)
                old_document = previous.get(item_id)
                if entry is None or old_document is None:
                    continue
                new_parent = self._entry_value(entry, "parent_id")
                new_ancestors = tuple(self._entry_value(entry, "ancestor_ids", ()))
                still_in_scope = (
                    new_parent == target_folder_id
                    or (recursive and target_folder_id in new_ancestors)
                )
                if still_in_scope:
                    continue
                old_item = self._deserialize_item(old_document["item"])
                moved_item = DriveItem(
                    item_id=old_item.item_id,
                    name=str(self._entry_value(entry, "name", old_item.name)),
                    mime_type=str(self._entry_value(entry, "mime_type", old_item.mime_type)),
                    modified_time=self._entry_value(entry, "modified_time", old_item.modified_time),
                    parent_id=new_parent,
                    web_url=old_item.web_url,
                    size_bytes=self._entry_value(entry, "size", old_item.size_bytes),
                    is_folder=False,
                )
                retained = dict(old_document)
                retained["item"] = self._serialize_item(moved_item)
                retained["provenance"] = {
                    **self._provenance(
                        moved_item,
                        drive_account_id=drive_account_id,
                        owner_user_id=owner_user_id,
                        root_folder_id=effective_root,
                        scope_folder_id=new_parent,
                        structure_entries=structure_entries,
                    ),
                    "content_hash": old_document.get("content_hash"),
                }
                current[item_id] = retained
                moved_outside_scope.add(item_id)
                stats["moved"] += 1
            removed_ids -= moved_outside_scope
            removed_state_ids = set()
            for item_id, state in previous_states.items():
                if item_id in discovered_ids:
                    continue
                if target_file_id is not None:
                    if item_id == target_file_id:
                        removed_state_ids.add(item_id)
                    continue
                parent_id = state.get("parent_folder_id")
                ancestor_ids = state.get("ancestor_ids")
                if parent_id is None or not isinstance(ancestor_ids, list):
                    # Un estado heredado sin procedencia no se elimina desde
                    # un ámbito parcial porque no puede asignarse con certeza.
                    continue
                if parent_id == target_folder_id or (
                    recursive and target_folder_id in ancestor_ids
                ):
                    removed_state_ids.add(item_id)
            for item_id in removed_ids:
                current.pop(item_id, None)
            for item_id in removed_state_ids:
                current_states.pop(item_id, None)
        stats["removed"] = len(removed_ids)

        payload = {
            "version": INDEX_VERSION,
            "updated_at": self._now(),
            "root_folder_id": effective_root,
            "documents": current,
            "file_states": current_states,
        }
        self.save(payload)
        stats.update(self.status())
        return stats

    def search_chunks(
        self,
        query: str,
        *,
        limit: int = 8,
        max_per_document: int = 3,
        scope: dict[str, Any] | None = None,
    ) -> list[IndexChunkMatch]:
        """
        Recupera los fragmentos más relevantes sin limitarse a uno por archivo.

        Esta operación es la base léxica del RAG del Sprint 10. No utiliza
        embeddings y funciona completamente sobre el índice local.
        """

        terms = self._terms(query)
        if not terms:
            return []

        normalized_query = self._normalize(
            query.strip()
        )
        payload = self.load()
        candidates: list[IndexChunkMatch] = []

        for document in payload["documents"].values():
            if not self._matches_search_scope(document, scope):
                continue
            try:
                item = self._deserialize_item(
                    document["item"]
                )
            except (KeyError, TypeError):
                continue

            normalized_name = self._normalize(
                item.name
            )

            for chunk_index, chunk in enumerate(
                document.get("chunks", [])
            ):
                text = str(chunk.get("text", "")).strip()
                if not text:
                    continue

                normalized_text = self._normalize(
                    text
                )
                counts = [
                    normalized_text.count(term)
                    for term in terms
                ]
                matched = sum(
                    1 for count in counts if count
                )

                name_counts = [
                    normalized_name.count(term)
                    for term in terms
                ]
                name_matched = sum(
                    1 for count in name_counts if count
                )

                phrase_count = (
                    normalized_text.count(
                        normalized_query
                    )
                    if normalized_query
                    else 0
                )

                if matched == 0 and name_matched == 0:
                    continue

                coverage = matched / len(terms)
                name_coverage = (
                    name_matched / len(terms)
                )
                score = (
                    coverage * 12.0
                    + name_coverage * 4.0
                    + min(sum(counts), 24) * 0.3
                    + min(sum(name_counts), 8) * 0.4
                    + (6.0 if phrase_count else 0.0)
                    + self._priority_bonus(document)
                )

                candidates.append(
                    IndexChunkMatch(
                        item=item,
                        text=text,
                        score=round(score, 3),
                        chunk_index=chunk_index,
                    )
                )

        candidates.sort(
            key=lambda match: (
                -match.score,
                match.item.name.casefold(),
                match.chunk_index,
            )
        )

        selected: list[IndexChunkMatch] = []
        per_document: dict[str, int] = {}

        for match in candidates:
            current_count = per_document.get(
                match.item.item_id,
                0,
            )
            if current_count >= max_per_document:
                continue

            selected.append(match)
            per_document[match.item.item_id] = (
                current_count + 1
            )

            if len(selected) >= limit:
                break

        return selected

    @staticmethod
    def _matches_search_scope(document: dict[str, Any], scope: dict[str, Any] | None) -> bool:
        if not scope:
            return True
        item = document.get("item", {})
        provenance = document.get("provenance", {})
        account_id = scope.get("drive_account_id")
        owner_user_id = scope.get("user_id")
        root_id = scope.get("root_folder_id")
        if account_id and provenance.get("drive_account_id") not in {None, account_id}:
            return False
        if owner_user_id:
            document_owner = provenance.get("owner_user_id")
            access_user_ids = {str(value).casefold() for value in provenance.get("access_user_ids", [])}
            if document_owner is None:
                return False
            if str(document_owner).casefold() != str(owner_user_id).casefold() and str(owner_user_id).casefold() not in access_user_ids:
                return False
        if root_id and provenance.get("root_folder_id") not in {None, root_id}:
            return False
        if scope.get("type", "global") == "global":
            return True
        scope_type = scope.get("type")
        target_id = scope.get("target_id")
        if scope_type == "file":
            return item.get("item_id") == target_id
        if scope_type == "root":
            return provenance.get("root_folder_id") == target_id
        if scope_type in {"current", "subtree"}:
            return item.get("parent_id") == target_id or target_id in provenance.get("ancestor_ids", [])
        return True

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        context_chars: int = 700,
        scope: dict[str, Any] | None = None,
    ) -> list[IndexSearchMatch]:
        terms = self._terms(query)
        if not terms:
            return []

        normalized_query = self._normalize(
            query.strip()
        )
        payload = self.load()
        candidates: list[IndexSearchMatch] = []

        for document in payload["documents"].values():
            if not self._matches_search_scope(document, scope):
                continue
            try:
                item = self._deserialize_item(
                    document["item"]
                )
            except (KeyError, TypeError):
                continue

            for chunk_index, chunk in enumerate(
                document.get("chunks", [])
            ):
                text = str(chunk.get("text", ""))
                normalized = self._normalize(text)
                counts = [
                    normalized.count(term)
                    for term in terms
                ]
                matched = sum(
                    1 for count in counts if count
                )
                if matched == 0:
                    continue

                phrase_count = normalized.count(
                    normalized_query
                )
                coverage = matched / len(terms)
                score = (
                    coverage * 10.0
                    + min(sum(counts), 20) * 0.25
                    + (5.0 if phrase_count else 0.0)
                    + self._priority_bonus(document)
                )

                first_positions = [
                    normalized.find(term)
                    for term in terms
                    if normalized.find(term) >= 0
                ]
                center = min(first_positions)
                half = max(80, context_chars // 2)
                start = max(0, center - half)
                end = min(len(text), center + half)

                snippet = text[start:end].strip()
                if start > 0:
                    snippet = "…" + snippet
                if end < len(text):
                    snippet += "…"

                candidates.append(
                    IndexSearchMatch(
                        item=item,
                        snippet=snippet,
                        score=round(score, 3),
                        chunk_index=chunk_index,
                    )
                )

        candidates.sort(
            key=lambda match: (
                -match.score,
                match.item.name.casefold(),
                match.chunk_index,
            )
        )

        unique: list[IndexSearchMatch] = []
        seen_documents: set[str] = set()
        for match in candidates:
            if match.item.item_id in seen_documents:
                continue
            seen_documents.add(match.item.item_id)
            unique.append(match)
            if len(unique) >= limit:
                break

        return unique


class GoogleDriveIndexTool(BaseTool):
    """Herramienta del framework para el índice documental local."""

    tool_id = "google.drive.index"
    name = "Índice documental de Google Drive"
    capabilities = (
        Capability("documents.index.sync"),
        Capability("documents.index.sync_scope"),
        Capability("documents.index.search"),
        Capability("documents.index.status"),
        Capability("documents.index.clear"),
    )
    required_permissions = frozenset(
        {"google.drive.read"}
    )
    risk = ToolRisk.LOW

    def __init__(
        self,
        client: GoogleDriveClient,
        index: GoogleDriveDocumentIndex,
        structure_index: Any = None,
    ) -> None:
        super().__init__()
        self.client = client
        self.index = index
        self.structure_index = structure_index
        if not client.is_available():
            self.disable()

    def validate_arguments(
        self,
        arguments: dict[str, Any],
    ) -> None:
        super().validate_arguments(arguments)

        query = arguments.get("query")
        if query is not None and (
            not isinstance(query, str)
            or not query.strip()
        ):
            raise ValueError(
                "'query' debe ser texto no vacío."
            )

        for key, maximum in (
            ("limit", 50),
            ("max_items", 5000),
            ("folder_limit", 1000),
            ("context_chars", 4000),
        ):
            value = arguments.get(key)
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 1
                or value > maximum
            ):
                raise ValueError(
                    f"'{key}' debe estar entre 1 y {maximum}."
                )
        for key in ("target_folder_id", "target_file_id"):
            value = arguments.get(key)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"'{key}' debe ser un identificador no vacío.")
        if arguments.get("target_folder_id") and arguments.get("target_file_id"):
            raise ValueError("No se puede seleccionar carpeta y archivo simultáneamente.")
        scope = arguments.get("scope")
        if scope is not None and not isinstance(scope, dict):
            raise ValueError("'scope' debe ser un objeto estructurado.")

    @staticmethod
    def _match_data(
        match: IndexSearchMatch,
    ) -> dict[str, Any]:
        return {
            "item": asdict(match.item),
            "snippet": match.snippet,
            "score": match.score,
            "chunk_index": match.chunk_index,
        }

    def execute(
        self,
        capability: Capability,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        self.validate_arguments(arguments)
        root_folder_id = getattr(self.client, "root_folder_id", None)
        account_id = str(context.metadata.get("drive_account_id") or "default")

        if capability == Capability(
            "documents.index.sync"
        ) or capability == Capability("documents.index.sync_scope"):
            structure_entries = None
            if self.structure_index is not None and root_folder_id:
                structure_entries = self.structure_index.entries(
                    user_id=context.requested_by,
                    drive_account_id=account_id,
                    root_folder_id=root_folder_id,
                )
            target_file_id = arguments.get("target_file_id")
            target_file_item = None
            if target_file_id and structure_entries:
                entry = structure_entries.get(str(target_file_id))
                if entry is not None:
                    target_file_item = DriveItem(
                        item_id=entry.file_id,
                        name=entry.name,
                        mime_type=entry.mime_type,
                        modified_time=entry.modified_time,
                        parent_id=entry.parent_id,
                        size_bytes=entry.size,
                        is_folder=entry.is_folder,
                    )
            stats = self.index.sync_scope(
                self.client,
                root_folder_id=root_folder_id,
                target_folder_id=arguments.get("target_folder_id"),
                recursive=bool(arguments.get("recursive", True)),
                target_file_id=target_file_id,
                target_file_item=target_file_item,
                drive_account_id=account_id,
                owner_user_id=context.requested_by,
                structure_entries=structure_entries,
                max_items=arguments.get(
                    "max_items",
                    500,
                ),
                folder_limit=arguments.get(
                    "folder_limit",
                    100,
                ),
                force=bool(
                    arguments.get("force", False)
                ),
            )
            return ToolResult.ok(
                "Índice de Google Drive actualizado.",
                data=stats,
            )

        if capability == Capability(
            "documents.index.search"
        ):
            query = arguments.get("query")
            if not isinstance(query, str) or not query.strip():
                raise ValueError(
                    "'query' es obligatorio para buscar en el índice."
                )

            requested_scope = dict(arguments.get("scope") or {"type": "global"})
            requested_scope.setdefault("user_id", context.requested_by)
            requested_scope.setdefault("drive_account_id", account_id)
            requested_scope.setdefault("root_folder_id", root_folder_id)
            matches = self.index.search(
                query,
                limit=arguments.get("limit", 10),
                context_chars=arguments.get(
                    "context_chars",
                    700,
                ),
                scope=requested_scope,
            )
            return ToolResult.ok(
                "Búsqueda en el índice completada.",
                data={
                    "query": query.strip(),
                    "count": len(matches),
                    "matches": [
                        self._match_data(match)
                        for match in matches
                    ],
                },
            )

        if capability == Capability(
            "documents.index.status"
        ):
            return ToolResult.ok(
                "Estado del índice obtenido.",
                data=self.index.status(),
            )

        if capability == Capability(
            "documents.index.clear"
        ):
            deleted = self.index.clear()
            return ToolResult.ok(
                (
                    "Índice local eliminado."
                    if deleted
                    else "El índice local ya estaba vacío."
                ),
                data={"deleted": deleted},
            )

        return ToolResult.fail(
            "Capacidad no compatible con el índice de Drive.",
            error="unsupported_capability",
        )
