"""Gestión centralizada del registro de actividad de Atlas.

Los mensajes se guardan en ``logs/atlas.log`` con fecha, hora y nivel.
Un fallo temporal de disco o de una unidad virtual nunca debe detener Atlas.
"""

from __future__ import annotations

import sys
from datetime import datetime

from config import LOG_FILE
from config import LOGGING_ENABLED
from config import ensure_runtime_directories


def write(level: str, message: str) -> None:
    """Escribe un mensaje en el log sin interrumpir la ejecución de Atlas."""

    if not LOGGING_ENABLED:
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}\n"

    try:
        ensure_runtime_directories()
        with LOG_FILE.open("a", encoding="utf-8") as log_file:
            log_file.write(line)
    except OSError as exc:
        # El registro es auxiliar: si Google Drive o la unidad asignada no
        # están disponibles, Atlas debe continuar y mostrar el aviso.
        print(
            f"[ATLAS] No se pudo escribir el log ({exc}).",
            file=sys.stderr,
        )


def info(message: str) -> None:
    """Registra un mensaje informativo."""

    write("INFO", message)


def warning(message: str) -> None:
    """Registra una advertencia."""

    write("WARNING", message)


def error(message: str) -> None:
    """Registra un error."""

    write("ERROR", message)
