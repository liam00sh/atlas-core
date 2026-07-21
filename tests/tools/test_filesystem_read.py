"""
Pruebas de FilesystemReadTool.

Cubren lectura, permisos, límites de ruta, archivos sensibles, binarios,
tamaño máximo y truncado.
"""

from pathlib import Path

import pytest

from tools.context import ToolContext
from tools.filesystem_read import FilesystemReadTool
from tools.manager import ToolManager
from tools.registry import ToolRegistry


def build_manager(root: Path, max_bytes: int = 1_000_000):
    registry = ToolRegistry()
    registry.register(
        FilesystemReadTool(
            allowed_roots=(root,),
            max_bytes=max_bytes,
        )
    )
    return ToolManager(registry)


def build_context(*, permission: bool = True) -> ToolContext:
    permissions = (
        {"filesystem.read"}
        if permission
        else set()
    )
    return ToolContext(
        requested_by="Liam",
        channel="test",
        permissions=permissions,
    )


def test_reads_text_file_inside_allowed_root(
    tmp_path: Path,
) -> None:
    target = tmp_path / "notes.txt"
    target.write_text(
        "Hola desde Atlas",
        encoding="utf-8",
    )

    result = build_manager(tmp_path).execute(
        "filesystem.read",
        arguments={"path": "notes.txt"},
        context=build_context(),
    )

    assert result.success is True
    assert result.data["content"] == "Hola desde Atlas"
    assert result.data["path"] == "notes.txt"
    assert result.data["truncated"] is False


def test_requires_filesystem_permission(
    tmp_path: Path,
) -> None:
    from tools.exceptions import ToolPermissionError

    target = tmp_path / "notes.txt"
    target.write_text("contenido", encoding="utf-8")

    with pytest.raises(ToolPermissionError):
        build_manager(tmp_path).execute(
            "filesystem.read",
            arguments={"path": "notes.txt"},
            context=build_context(permission=False),
        )


def test_blocks_path_traversal(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / "outside_atlas.txt"
    outside.write_text("secreto", encoding="utf-8")

    result_manager = build_manager(tmp_path)

    from tools.exceptions import ToolExecutionError

    with pytest.raises(ToolExecutionError):
        result_manager.execute(
            "filesystem.read",
            arguments={"path": "../outside_atlas.txt"},
            context=build_context(),
        )


def test_blocks_sensitive_file(
    tmp_path: Path,
) -> None:
    sensitive = tmp_path / ".env"
    sensitive.write_text(
        "TOKEN=secret",
        encoding="utf-8",
    )

    from tools.exceptions import ToolExecutionError

    with pytest.raises(ToolExecutionError):
        build_manager(tmp_path).execute(
            "filesystem.read",
            arguments={"path": ".env"},
            context=build_context(),
        )


def test_rejects_binary_file(
    tmp_path: Path,
) -> None:
    binary = tmp_path / "image.bin"
    binary.write_bytes(b"\x89PNG\x00binary")

    from tools.exceptions import ToolExecutionError

    with pytest.raises(ToolExecutionError):
        build_manager(tmp_path).execute(
            "filesystem.read",
            arguments={"path": "image.bin"},
            context=build_context(),
        )


def test_rejects_file_over_size_limit(
    tmp_path: Path,
) -> None:
    target = tmp_path / "large.txt"
    target.write_text("123456", encoding="utf-8")

    from tools.exceptions import ToolExecutionError

    with pytest.raises(ToolExecutionError):
        build_manager(
            tmp_path,
            max_bytes=5,
        ).execute(
            "filesystem.read",
            arguments={"path": "large.txt"},
            context=build_context(),
        )


def test_truncates_content_when_requested(
    tmp_path: Path,
) -> None:
    target = tmp_path / "long.txt"
    target.write_text(
        "abcdefghij",
        encoding="utf-8",
    )

    result = build_manager(tmp_path).execute(
        "filesystem.read",
        arguments={
            "path": "long.txt",
            "max_chars": 4,
        },
        context=build_context(),
    )

    assert result.success is True
    assert result.data["content"] == "abcd"
    assert result.data["truncated"] is True
    assert result.warnings
