"""Gestión centralizada del registro de actividad de Atlas.

Los mensajes se guardan en ``logs/atlas.log`` con fecha, hora y nivel.
"""

from datetime import datetime

from config import LOG_FILE
from config import LOGGING_ENABLED
from config import ensure_runtime_directories


def write(level: str, message: str) -> None:
    """Escribe un mensaje en el log con el nivel indicado."""

    if not LOGGING_ENABLED:
        return

    ensure_runtime_directories()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}\n"

    with LOG_FILE.open("a", encoding="utf-8") as log_file:
        log_file.write(line)


def info(message: str) -> None:
    """Registra un mensaje informativo."""

    write("INFO", message)


def warning(message: str) -> None:
    """Registra una advertencia."""

    write("WARNING", message)


def error(message: str) -> None:
    """Registra un error."""

    write("ERROR", message)
