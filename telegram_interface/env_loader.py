"""Carga segura y mínima de variables desde un archivo .env local.

No sobrescribe variables ya definidas en el proceso. No imprime valores ni
registra secretos. Está pensada para la configuración local de Telegram.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import MutableMapping


class EnvFileError(ValueError):
    """El archivo .env existe, pero contiene una línea no válida."""


def load_env_file(
    path: str | Path,
    *,
    environ: MutableMapping[str, str] | None = None,
    override: bool = False,
) -> bool:
    """Carga ``CLAVE=VALOR`` desde *path* y devuelve si el archivo existía.

    Se ignoran líneas vacías y comentarios. Se admiten valores entre comillas
    simples o dobles. Por seguridad, los valores no se incluyen en errores.
    """
    env = os.environ if environ is None else environ
    file_path = Path(path)
    if not file_path.exists():
        return False

    try:
        lines = file_path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise EnvFileError("No se pudo leer el archivo .env local.") from exc

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            raise EnvFileError(f"Línea {line_number} no válida en .env.")

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not key.replace("_", "A").isalnum() or key[0].isdigit():
            raise EnvFileError(f"Clave no válida en la línea {line_number} de .env.")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if override or key not in env:
            env[key] = value
    return True
