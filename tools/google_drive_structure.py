"""Árbol ligero y navegación segura dentro de una raíz autorizada de Drive."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from time import monotonic
from typing import Any

from tools.base_tool import BaseTool, ToolRisk
from tools.capability import Capability
from tools.context import ToolContext
from tools.google_drive import DriveItem, GoogleDriveClient
from tools.result import ToolResult


STRUCTURE_INDEX_VERSION = 1
DEFAULT_ACCOUNT_ID = "default"
DEFAULT_ROOT_NAME = "Atlas Project"
PRUNED_TECHNICAL_FOLDERS = frozenset({
    ".git", ".agents", ".pytest_cache", "__pycache__", ".mypy_cache",
    ".ruff_cache", ".venv", "venv",
    "node_modules", "logs",
})


@dataclass(frozen=True, slots=True)
class DriveStructureEntry:
    """Metadatos mínimos para navegar; nunca contiene texto ni embeddings."""

    file_id: str
    name: str
    mime_type: str
    parent_id: str | None
    root_id: str
    relative_path: str
    ancestor_ids: tuple[str, ...]
    ancestor_names: tuple[str, ...]
    modified_time: str | None
    size: int | None
    is_folder: bool
    traversal_status: str = "available"
    exclusion_reason: str | None = None


@dataclass(frozen=True, slots=True)
class DrivePathResolution:
    status: str
    entry: DriveStructureEntry | None = None
    candidates: tuple[DriveStructureEntry, ...] = ()
    message: str = ""


@dataclass(slots=True)
class DriveNavigationState:
    root_folder_id: str
    current_folder_id: str
    breadcrumbs: tuple[tuple[str, str], ...]


class GoogleDriveStructureIndex:
    """Índice estructural persistente, aislado por usuario, cuenta y raíz."""

    def __init__(
        self,
        path: Path,
        *,
        ttl_seconds: float = 120.0,
        max_namespaces: int = 32,
        pruned_folder_names: frozenset[str] | set[str] | None = None,
    ) -> None:
        self.path = Path(path).resolve()
        self.ttl_seconds = max(0.0, float(ttl_seconds))
        self.max_namespaces = max(1, int(max_namespaces))
        self.pruned_folder_names = frozenset(
            name.strip().casefold()
            for name in (
                PRUNED_TECHNICAL_FOLDERS
                if pruned_folder_names is None
                else pruned_folder_names
            )
            if name.strip()
        )
        self._refreshed_at: dict[str, float] = {}

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def namespace_key(user_id: str, drive_account_id: str, root_folder_id: str) -> str:
        raw = "\0".join((user_id.strip().casefold(), drive_account_id.strip(), root_folder_id.strip()))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _empty(self) -> dict[str, Any]:
        return {"version": STRUCTURE_INDEX_VERSION, "namespaces": {}}

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._empty()
        if payload.get("version") != STRUCTURE_INDEX_VERSION or not isinstance(payload.get("namespaces"), dict):
            return self._empty()
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        temporary.replace(self.path)

    def invalidate(self, *, user_id: str, drive_account_id: str, root_folder_id: str) -> None:
        self._refreshed_at.pop(self.namespace_key(user_id, drive_account_id, root_folder_id), None)

    def is_fresh(self, *, user_id: str, drive_account_id: str, root_folder_id: str) -> bool:
        refreshed = self._refreshed_at.get(self.namespace_key(user_id, drive_account_id, root_folder_id))
        return refreshed is not None and monotonic() - refreshed <= self.ttl_seconds

    def entries(self, *, user_id: str, drive_account_id: str, root_folder_id: str) -> dict[str, DriveStructureEntry]:
        namespace = self.load()["namespaces"].get(
            self.namespace_key(user_id, drive_account_id, root_folder_id), {}
        )
        result: dict[str, DriveStructureEntry] = {}
        for file_id, raw in namespace.get("entries", {}).items():
            try:
                data = dict(raw)
                data["ancestor_ids"] = tuple(data.get("ancestor_ids", ()))
                data["ancestor_names"] = tuple(data.get("ancestor_names", ()))
                result[file_id] = DriveStructureEntry(**data)
            except (TypeError, ValueError):
                continue
        return result

    def sync(
        self,
        client: GoogleDriveClient,
        *,
        user_id: str,
        drive_account_id: str,
        root_folder_id: str,
        root_folder_name: str = DEFAULT_ROOT_NAME,
        force: bool = False,
        folder_limit: int = 1000,
        max_items: int = 10_000,
    ) -> dict[str, Any]:
        key = self.namespace_key(user_id, drive_account_id, root_folder_id)
        existing = self.entries(
            user_id=user_id, drive_account_id=drive_account_id, root_folder_id=root_folder_id
        )
        if existing and not force and self.is_fresh(
            user_id=user_id, drive_account_id=drive_account_id, root_folder_id=root_folder_id
        ):
            return {"cached": True, "entry_count": len(existing), "folder_count": sum(e.is_folder for e in existing.values())}

        root = DriveStructureEntry(
            file_id=root_folder_id,
            name=root_folder_name,
            mime_type="application/vnd.google-apps.folder",
            parent_id=None,
            root_id=root_folder_id,
            relative_path=root_folder_name,
            ancestor_ids=(),
            ancestor_names=(),
            modified_time=None,
            size=None,
            is_folder=True,
        )
        entries = {root_folder_id: root}
        queue = [root]
        list_calls = 0
        while queue and len(entries) < max_items:
            parent = queue.pop(0)
            children = client.list_folder(parent.file_id, limit=folder_limit)
            list_calls += 1
            for item in children:
                if item.item_id in entries:
                    continue
                pruned = item.is_folder and item.name.strip().casefold() in self.pruned_folder_names
                entry = DriveStructureEntry(
                    file_id=item.item_id,
                    name=item.name,
                    mime_type=item.mime_type,
                    parent_id=parent.file_id,
                    root_id=root_folder_id,
                    relative_path=f"{parent.relative_path}/{item.name}",
                    ancestor_ids=parent.ancestor_ids + (parent.file_id,),
                    ancestor_names=parent.ancestor_names + (parent.name,),
                    modified_time=item.modified_time,
                    size=item.size_bytes,
                    is_folder=item.is_folder,
                    traversal_status="excluded_by_policy" if pruned else "available",
                    exclusion_reason="technical_folder_name" if pruned else None,
                )
                entries[item.item_id] = entry
                if item.is_folder and not pruned:
                    queue.append(entry)
                if len(entries) >= max_items:
                    break

        payload = self.load()
        namespaces = payload["namespaces"]
        if key not in namespaces and len(namespaces) >= self.max_namespaces:
            oldest = min(namespaces, key=lambda item: str(namespaces[item].get("updated_at", "")))
            namespaces.pop(oldest, None)
        namespaces[key] = {
            "user_key": hashlib.sha256(user_id.casefold().encode("utf-8")).hexdigest(),
            "drive_account_id": drive_account_id,
            "root_folder_id": root_folder_id,
            "root_folder_name": root_folder_name,
            "updated_at": self._now(),
            "entries": {file_id: asdict(entry) for file_id, entry in entries.items()},
        }
        self.save(payload)
        self._refreshed_at[key] = monotonic()
        return {
            "cached": False,
            "entry_count": len(entries),
            "folder_count": sum(entry.is_folder for entry in entries.values()),
            "file_count": sum(not entry.is_folder for entry in entries.values()),
            "remote_list_calls": list_calls,
        }


class DriveNavigationService:
    """Resuelve rutas y conserva la ubicación por usuario, sesión y cuenta."""

    def __init__(self, structure_index: GoogleDriveStructureIndex) -> None:
        self.structure_index = structure_index
        self._states: dict[tuple[str, str, str, str], DriveNavigationState] = {}

    @staticmethod
    def _state_key(user_id: str, session_id: str, account_id: str, root_id: str) -> tuple[str, str, str, str]:
        return (user_id.casefold(), session_id, account_id, root_id)

    def state(self, *, user_id: str, session_id: str, drive_account_id: str, root_folder_id: str, root_folder_name: str) -> DriveNavigationState:
        key = self._state_key(user_id, session_id, drive_account_id, root_folder_id)
        return self._states.setdefault(
            key,
            DriveNavigationState(root_folder_id, root_folder_id, ((root_folder_id, root_folder_name),)),
        )

    def _entries(self, **identity: str) -> dict[str, DriveStructureEntry]:
        return self.structure_index.entries(
            user_id=identity["user_id"],
            drive_account_id=identity["drive_account_id"],
            root_folder_id=identity["root_folder_id"],
        )

    def resolve_path(self, path: str, *, user_id: str, session_id: str, drive_account_id: str, root_folder_id: str, root_folder_name: str, allow_file: bool = False) -> DrivePathResolution:
        entries = self._entries(user_id=user_id, drive_account_id=drive_account_id, root_folder_id=root_folder_id)
        if root_folder_id not in entries:
            return DrivePathResolution("missing_index", message="El índice estructural de Drive no está creado.")
        state = self.state(
            user_id=user_id, session_id=session_id, drive_account_id=drive_account_id,
            root_folder_id=root_folder_id, root_folder_name=root_folder_name,
        )
        raw = path.strip().replace("\\", "/") or "."
        absolute = raw.startswith("/") or raw.casefold() == root_folder_name.casefold() or raw.casefold().startswith(root_folder_name.casefold() + "/")
        if raw == "/" or raw.casefold() == root_folder_name.casefold():
            return DrivePathResolution("resolved", entries[root_folder_id])
        if absolute:
            current_id = root_folder_id
            raw = raw.lstrip("/")
            if raw.casefold().startswith(root_folder_name.casefold() + "/"):
                raw = raw[len(root_folder_name) + 1:]
        else:
            current_id = state.current_folder_id

        parts = [segment.strip() for segment in raw.split("/") if segment.strip()]
        for position, part in enumerate(parts):
            if not part or part == ".":
                continue
            if part == "..":
                current = entries.get(current_id)
                current_id = current.parent_id if current and current.parent_id in entries else root_folder_id
                continue
            final_part = position == len(parts) - 1
            matches = tuple(
                entry for entry in entries.values()
                if entry.parent_id == current_id
                and (entry.is_folder or (allow_file and final_part))
                and entry.name.casefold() == part.casefold()
            )
            if not matches:
                return DrivePathResolution("not_found", message=f"No existe la carpeta «{part}» dentro de la ruta autorizada.")
            if len(matches) > 1:
                return DrivePathResolution("ambiguous", candidates=matches, message="La ruta es ambigua; selecciona una de las rutas completas.")
            current_id = matches[0].file_id
        return DrivePathResolution("resolved", entries[current_id])

    @staticmethod
    def breadcrumbs(entry: DriveStructureEntry, entries: dict[str, DriveStructureEntry]) -> tuple[tuple[str, str], ...]:
        ids = entry.ancestor_ids + (entry.file_id,)
        return tuple((file_id, entries[file_id].name) for file_id in ids if file_id in entries)

    def cd(self, path: str, **identity: str) -> DrivePathResolution:
        resolution = self.resolve_path(path, **identity)
        if resolution.status != "resolved" or resolution.entry is None:
            return resolution
        entries = self._entries(
            user_id=identity["user_id"], drive_account_id=identity["drive_account_id"], root_folder_id=identity["root_folder_id"]
        )
        state = self.state(**identity)
        state.current_folder_id = resolution.entry.file_id
        state.breadcrumbs = self.breadcrumbs(resolution.entry, entries)
        return resolution

    def cd_id(self, folder_id: str, **identity: str) -> DrivePathResolution:
        entries = self._entries(
            user_id=identity["user_id"], drive_account_id=identity["drive_account_id"], root_folder_id=identity["root_folder_id"]
        )
        entry = entries.get(folder_id)
        if entry is None or not entry.is_folder:
            return DrivePathResolution("not_found", message="La carpeta seleccionada no pertenece a la raíz autorizada.")
        state = self.state(**identity)
        state.current_folder_id = entry.file_id
        state.breadcrumbs = self.breadcrumbs(entry, entries)
        return DrivePathResolution("resolved", entry)

    def list_current(self, **identity: str) -> list[DriveStructureEntry]:
        entries = self._entries(
            user_id=identity["user_id"], drive_account_id=identity["drive_account_id"], root_folder_id=identity["root_folder_id"]
        )
        current_id = self.state(**identity).current_folder_id
        return sorted(
            (entry for entry in entries.values() if entry.parent_id == current_id),
            key=lambda entry: (not entry.is_folder, entry.name.casefold(), entry.file_id),
        )

    def tree(self, *, start_folder_id: str | None = None, depth: int = 2, include_files: bool = True, **identity: str) -> list[dict[str, Any]]:
        entries = self._entries(
            user_id=identity["user_id"], drive_account_id=identity["drive_account_id"], root_folder_id=identity["root_folder_id"]
        )
        start = start_folder_id or self.state(**identity).current_folder_id
        output: list[dict[str, Any]] = []
        queue = [(start, 0)]
        while queue:
            parent_id, level = queue.pop(0)
            if level >= depth:
                continue
            children = sorted(
                (entry for entry in entries.values() if entry.parent_id == parent_id and (include_files or entry.is_folder)),
                key=lambda entry: (not entry.is_folder, entry.name.casefold(), entry.file_id),
            )
            for entry in children:
                output.append({"depth": level + 1, **asdict(entry)})
                if entry.is_folder:
                    queue.append((entry.file_id, level + 1))
        return output


class GoogleDriveStructureTool(BaseTool):
    tool_id = "google.drive.structure"
    name = "Navegación estructural de Google Drive"
    capabilities = tuple(Capability(value) for value in (
        "drive.structure.sync", "drive.pwd", "drive.cd", "drive.list", "drive.tree", "drive.resolve_path"
    ))
    required_permissions = frozenset({"google.drive.read"})
    risk = ToolRisk.LOW

    def __init__(self, client: GoogleDriveClient, index: GoogleDriveStructureIndex, navigation: DriveNavigationService, *, root_folder_name: str = DEFAULT_ROOT_NAME) -> None:
        super().__init__()
        self.client = client
        self.index = index
        self.navigation = navigation
        self.root_folder_name = root_folder_name
        if not client.is_available() or not str(getattr(client, "root_folder_id", "") or "").strip():
            self.disable()

    def validate_arguments(self, arguments: dict[str, Any]) -> None:
        super().validate_arguments(arguments)
        depth = arguments.get("depth")
        if depth is not None and (isinstance(depth, bool) or not isinstance(depth, int) or not 1 <= depth <= 20):
            raise ValueError("'depth' debe estar entre 1 y 20.")

    def _identity(self, context: ToolContext) -> dict[str, str]:
        return {
            "user_id": context.requested_by,
            "session_id": str(context.metadata.get("session_id") or f"{context.channel}:default"),
            "drive_account_id": str(context.metadata.get("drive_account_id") or DEFAULT_ACCOUNT_ID),
            "root_folder_id": str(getattr(self.client, "root_folder_id")),
            "root_folder_name": self.root_folder_name,
        }

    @staticmethod
    def _resolution_data(resolution: DrivePathResolution) -> dict[str, Any]:
        return {
            "status": resolution.status,
            "entry": asdict(resolution.entry) if resolution.entry else None,
            "candidates": [asdict(item) for item in resolution.candidates],
        }

    def execute(self, capability: Capability, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        self.validate_arguments(arguments)
        identity = self._identity(context)
        if capability == Capability("drive.structure.sync"):
            data = self.index.sync(
                self.client,
                user_id=identity["user_id"],
                drive_account_id=identity["drive_account_id"],
                root_folder_id=identity["root_folder_id"],
                root_folder_name=identity["root_folder_name"],
                force=bool(arguments.get("force", False)),
            )
            return ToolResult.ok("Estructura de Drive actualizada.", data=data)

        entries = self.index.entries(
            user_id=identity["user_id"], drive_account_id=identity["drive_account_id"], root_folder_id=identity["root_folder_id"]
        )
        if not entries:
            self.index.sync(
                self.client,
                user_id=identity["user_id"], drive_account_id=identity["drive_account_id"],
                root_folder_id=identity["root_folder_id"], root_folder_name=identity["root_folder_name"],
            )

        if capability == Capability("drive.pwd"):
            state = self.navigation.state(**identity)
            entry = self.index.entries(
                user_id=identity["user_id"], drive_account_id=identity["drive_account_id"], root_folder_id=identity["root_folder_id"]
            ).get(state.current_folder_id)
            return ToolResult.ok("Ruta actual de Drive.", data={"entry": asdict(entry) if entry else None, "breadcrumbs": [{"id": i, "name": n} for i, n in state.breadcrumbs]})
        if capability in {Capability("drive.cd"), Capability("drive.resolve_path")}:
            path = str(arguments.get("path", ".")).strip() or "."
            folder_id = arguments.get("folder_id")
            if capability == Capability("drive.cd") and isinstance(folder_id, str) and folder_id.strip():
                resolution = self.navigation.cd_id(folder_id.strip(), **identity)
            else:
                resolution = self.navigation.cd(path, **identity) if capability == Capability("drive.cd") else self.navigation.resolve_path(path, allow_file=bool(arguments.get("allow_file", True)), **identity)
            if resolution.status == "resolved":
                return ToolResult.ok("Ruta de Drive resuelta.", data=self._resolution_data(resolution))
            result = ToolResult.fail(resolution.message, error=resolution.status)
            result.data = self._resolution_data(resolution)
            return result
        if capability == Capability("drive.list"):
            return ToolResult.ok("Contenido de la carpeta actual.", data={"items": [asdict(item) for item in self.navigation.list_current(**identity)]})
        if capability == Capability("drive.tree"):
            return ToolResult.ok("Árbol de Drive obtenido.", data={"items": self.navigation.tree(start_folder_id=arguments.get("folder_id"), depth=arguments.get("depth", 2), include_files=bool(arguments.get("include_files", True)), **identity)})
        return ToolResult.fail("Capacidad estructural no compatible.", error="unsupported_capability")
