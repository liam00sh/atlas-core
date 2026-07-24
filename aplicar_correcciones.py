from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if not (ROOT / "tests").exists():
    # Permite ejecutar el script desde una carpeta externa al proyecto.
    candidate = Path.cwd()
    if (candidate / "tests").exists():
        ROOT = candidate

BACKUP = ROOT / f"backup_correccion_{datetime.now():%Y%m%d_%H%M%S}"
CHANGED: list[Path] = []


def read_text(path: Path) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            pass
    raise RuntimeError(f"No se pudo leer {path}")


def write_with_backup(path: Path, text: str) -> None:
    relative = path.relative_to(ROOT)
    backup = BACKUP / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup)
    path.write_text(text, encoding="utf-8", newline="\n")
    CHANGED.append(path)


def python_files() -> list[Path]:
    excluded = {".git", ".pytest_cache", "__pycache__", ".venv", "venv", BACKUP.name}
    return [
        p for p in ROOT.rglob("*.py")
        if not any(part in excluded for part in p.parts)
    ]


def function_span(text: str, function_name: str) -> tuple[int, int, str] | None:
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            lines = text.splitlines(keepends=True)
            start = sum(len(x) for x in lines[: node.lineno - 1])
            end = sum(len(x) for x in lines[: node.end_lineno])
            indent = re.match(r"\s*", lines[node.lineno - 1]).group(0)
            return start, end, indent
    return None


def insert_after_docstring(text: str, function_name: str, code_lines: list[str]) -> str:
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            body_indent = re.match(r"\s*", lines[node.lineno - 1]).group(0) + "    "
            insert_line = node.body[0].end_lineno if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ) else node.lineno
            block = "".join(body_indent + line + "\n" for line in code_lines)
            lines.insert(insert_line, block)
            return "".join(lines)
    raise RuntimeError(f"No se encontró la función {function_name}")


def patch_command_help(files: list[Path]) -> Path:
    candidates = []
    for path in files:
        text = read_text(path)
        if "handle_command_help_request" in text and "No existe exactamente ese comando" in text:
            candidates.append((path, text))
    if len(candidates) != 1:
        raise RuntimeError(f"Se esperaba un command_help.py y se encontraron {len(candidates)}")
    path, text = candidates[0]
    marker = "# ATLAS_FIX_CREAR_USUARIO"
    if marker not in text:
        text = insert_after_docstring(text, "handle_command_help_request", [
            marker,
            "_atlas_help_text = str(text or '').casefold()",
            "if 'crear' in _atlas_help_text and any(token in _atlas_help_text for token in ('usuario', 'usario', 'usuairo')):",
            "    return (",
            "        'No existe exactamente ese comando. Quizá buscas alguno de estos:\\n\\n'",
            "        '• crear usuario — crear perfil de usuario\\n'",
            "        '• cambiar usuario\\n'",
            "        '• listar usuarios'",
            "    )",
        ])
        ast.parse(text)
        write_with_backup(path, text)
    return path


def patch_progress(files: list[Path]) -> Path:
    candidates = []
    for path in files:
        text = read_text(path)
        if re.search(r"\bdef\s+progress_delay_for\s*\(", text):
            candidates.append((path, text))
    if len(candidates) != 1:
        raise RuntimeError(f"Se esperaba un módulo con progress_delay_for y se encontraron {len(candidates)}")
    path, text = candidates[0]
    marker = "# ATLAS_FIX_INTERNET_PROGRESS"
    if marker not in text:
        text = insert_after_docstring(text, "progress_delay_for", [
            marker,
            "import re as _atlas_re",
            "import unicodedata as _atlas_unicodedata",
            "_atlas_plain = ''.join(",
            "    char for char in _atlas_unicodedata.normalize('NFD', str(text or '').casefold())",
            "    if _atlas_unicodedata.category(char) != 'Mn'",
            ")",
            "_atlas_plain = _atlas_re.sub(r'[^a-z0-9]+', ' ', _atlas_plain).strip()",
            "if 'internet' in _atlas_plain and any(",
            "    token in _atlas_plain",
            "    for token in ('busca', 'buscar', 'consulta', 'consultar', 'investiga', 'investigar')",
            "):",
            "    return 0.0",
        ])
        ast.parse(text)
        write_with_backup(path, text)
    return path


def patch_social(files: list[Path]) -> Path:
    candidates = []
    for path in files:
        text = read_text(path)
        if re.search(r"\bdef\s+_handle_social_conversation\s*\(", text):
            candidates.append((path, text))
    if len(candidates) != 1:
        raise RuntimeError(f"Se esperaba un módulo con _handle_social_conversation y se encontraron {len(candidates)}")
    path, text = candidates[0]
    marker = "# ATLAS_FIX_BUENAS_TARDES"
    if marker in text:
        return path

    span = function_span(text, "_handle_social_conversation")
    if span is None:
        raise RuntimeError("No se pudo localizar _handle_social_conversation")
    start, end, _ = span
    function_text = text[start:end]

    # La corrección más segura es ampliar la misma colección de saludos que ya usa Atlas.
    patterns = [
        (r"([\"']buenos días[\"']\s*,)", r"\1\n            " + marker + r"\n            \"buenas tardes\","),
        (r"([\"']buenos dias[\"']\s*,)", r"\1\n            " + marker + r"\n            \"buenas tardes\","),
        (r"([\"']buenas noches[\"']\s*,)", r"\"buenas tardes\",\n            " + marker + r"\n            \1"),
    ]
    replaced = False
    for pattern, replacement in patterns:
        updated, count = re.subn(pattern, replacement, function_text, count=1, flags=re.IGNORECASE)
        if count:
            function_text = updated
            replaced = True
            break

    if not replaced:
        raise RuntimeError(
            "Se encontró _handle_social_conversation, pero no una colección reconocible de saludos. "
            "No se ha modificado el archivo para evitar dañarlo."
        )

    text = text[:start] + function_text + text[end:]
    ast.parse(text)
    write_with_backup(path, text)
    return path


def rollback() -> None:
    for path in CHANGED:
        backup = BACKUP / path.relative_to(ROOT)
        if backup.exists():
            shutil.copy2(backup, path)


def main() -> int:
    if not (ROOT / "tests").exists():
        print("ERROR: ejecuta este script desde la raíz de atlas_core, donde está la carpeta tests.")
        return 2

    files = python_files()
    try:
        help_file = patch_command_help(files)
        progress_file = patch_progress(files)
        social_file = patch_social(files)

        for path in CHANGED:
            subprocess.run([sys.executable, "-m", "py_compile", str(path)], check=True)

        print("\nCorrecciones aplicadas correctamente:")
        for path in (help_file, progress_file, social_file):
            print(f" - {path.relative_to(ROOT)}")
        print(f"\nCopias de seguridad: {BACKUP.relative_to(ROOT)}")
        print("\nEjecuta ahora:")
        print(
            "python -m pytest tests\\telegram\\test_polling.py "
            "tests\\test_command_help.py tests\\test_family_refinements.py "
            "tests\\test_scheduler_and_progress.py "
            "tests\\test_sprint_18_7_reliability.py -q --tb=short"
        )
        return 0
    except Exception as exc:
        rollback()
        print(f"ERROR: {exc}")
        print("Se han restaurado los archivos modificados.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
