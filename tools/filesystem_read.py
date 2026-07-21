"""
===============================================================================
Proyecto Atlas
Archivo: tools/filesystem_read.py

Descripción:
    Herramienta de lectura segura de archivos de texto.

    Solo permite leer archivos situados dentro de raíces autorizadas.
    Resuelve rutas reales para bloquear recorridos ".." y enlaces simbólicos
    que intenten salir de esas raíces.
===============================================================================
"""

from pathlib import Path
from typing import Any, Iterable

from tools.base_tool import BaseTool, ToolRisk
from tools.capability import Capability
from tools.context import ToolContext
from tools.result import ToolResult


class FilesystemReadTool(BaseTool):
    """Lee archivos de texto dentro de raíces explícitamente autorizadas."""

    tool_id = "filesystem.read"
    name = "Lectura segura de archivos"
    capabilities = (Capability("filesystem.read"),)
    required_permissions = frozenset({"filesystem.read"})
    risk = ToolRisk.MEDIUM

    DEFAULT_MAX_BYTES = 1_000_000
    DEFAULT_MAX_CHARS = 100_000
    MAX_ALLOWED_CHARS = 500_000

    BLOCKED_NAMES = frozenset(
        {
            ".env",
            ".env.local",
            ".env.production",
            "credentials.json",
            "token.json",
            "id_rsa",
            "id_ed25519",
        }
    )
    BLOCKED_SUFFIXES = frozenset(
        {
            ".key",
            ".pem",
            ".p12",
            ".pfx",
        }
    )

    def __init__(
        self,
        allowed_roots: Iterable[str | Path],
        *,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> None:
        super().__init__()

        roots = tuple(
            Path(root).expanduser().resolve()
            for root in allowed_roots
        )

        if not roots:
            raise ValueError(
                "FilesystemReadTool necesita al menos una raíz autorizada."
            )

        invalid_roots = [
            root
            for root in roots
            if not root.exists() or not root.is_dir()
        ]
        if invalid_roots:
            raise ValueError(
                "Las raíces autorizadas deben existir y ser directorios: "
                + ", ".join(str(root) for root in invalid_roots)
            )

        if max_bytes <= 0:
            raise ValueError("max_bytes debe ser mayor que cero.")

        self.allowed_roots = roots
        self.max_bytes = max_bytes

    def validate_arguments(
        self,
        arguments: dict[str, Any],
    ) -> None:
        super().validate_arguments(arguments)

        path = arguments.get("path")
        if not isinstance(path, str) or not path.strip():
            raise ValueError(
                "El argumento 'path' es obligatorio y debe ser texto."
            )

        encoding = arguments.get("encoding", "utf-8")
        if encoding not in {"utf-8", "utf-8-sig", "latin-1"}:
            raise ValueError(
                "La codificación debe ser utf-8, utf-8-sig o latin-1."
            )

        max_chars = arguments.get(
            "max_chars",
            self.DEFAULT_MAX_CHARS,
        )
        if (
            isinstance(max_chars, bool)
            or not isinstance(max_chars, int)
            or max_chars <= 0
            or max_chars > self.MAX_ALLOWED_CHARS
        ):
            raise ValueError(
                "'max_chars' debe ser un entero entre 1 y "
                f"{self.MAX_ALLOWED_CHARS}."
            )

    def _resolve_requested_path(
        self,
        raw_path: str,
    ) -> tuple[Path, Path]:
        requested = Path(raw_path).expanduser()

        candidates = (
            (requested,)
            if requested.is_absolute()
            else tuple(root / requested for root in self.allowed_roots)
        )

        for candidate in candidates:
            resolved = candidate.resolve(strict=False)

            for root in self.allowed_roots:
                if resolved.is_relative_to(root):
                    return resolved, root

        raise PermissionError(
            "La ruta solicitada está fuera de las raíces autorizadas."
        )

    def _ensure_safe_file(
        self,
        path: Path,
    ) -> None:
        if not path.exists():
            raise FileNotFoundError(
                f"El archivo no existe: {path}"
            )

        if not path.is_file():
            raise IsADirectoryError(
                f"La ruta no corresponde a un archivo: {path}"
            )

        lowered_name = path.name.lower()
        if (
            lowered_name in self.BLOCKED_NAMES
            or path.suffix.lower() in self.BLOCKED_SUFFIXES
        ):
            raise PermissionError(
                "El archivo solicitado está bloqueado por contener "
                "posibles credenciales o claves."
            )

        size = path.stat().st_size
        if size > self.max_bytes:
            raise ValueError(
                "El archivo supera el tamaño máximo permitido "
                f"de {self.max_bytes} bytes."
            )

        with path.open("rb") as file:
            sample = file.read(4096)

        if b"\x00" in sample:
            raise ValueError(
                "El archivo parece binario y no puede leerse como texto."
            )

    def execute(
        self,
        capability: Capability,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        raw_path = arguments["path"].strip()
        encoding = arguments.get("encoding", "utf-8")
        max_chars = arguments.get(
            "max_chars",
            self.DEFAULT_MAX_CHARS,
        )

        path, matched_root = self._resolve_requested_path(
            raw_path
        )
        self._ensure_safe_file(path)

        content = path.read_text(encoding=encoding)
        truncated = len(content) > max_chars
        visible_content = content[:max_chars]

        relative_path = path.relative_to(matched_root)

        warnings: list[str] = []
        if truncated:
            warnings.append(
                "El contenido se ha truncado al límite solicitado."
            )

        result = ToolResult.ok(
            "Archivo leído correctamente.",
            data={
                "path": str(relative_path),
                "absolute_path": str(path),
                "root": str(matched_root),
                "encoding": encoding,
                "size_bytes": path.stat().st_size,
                "content": visible_content,
                "truncated": truncated,
                "requested_by": context.requested_by,
                "channel": context.channel,
            },
        )
        result.warnings.extend(warnings)
        return result
