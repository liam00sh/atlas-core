"""Configuración central del Proyecto Atlas.

Este módulo reúne valores compartidos por distintos componentes. No debe
contener lógica de negocio ni información secreta.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Identidad y entorno.
PROJECT_NAME = "Proyecto Atlas"
ASSISTANT_NAME = "Daxter"
DEFAULT_LANGUAGE = "es"
DEBUG = False


def _resolve_base_dir() -> Path:
    """Devuelve una raíz de proyecto utilizable.

    La ruta del propio archivo es la opción principal. Si la unidad o el
    directorio dejan de estar disponibles temporalmente (por ejemplo, una
    unidad virtual de Google Drive), se usa una carpeta local de emergencia.
    """

    configured = os.getenv("ATLAS_BASE_DIR", "").strip()
    candidate = Path(configured).expanduser() if configured else Path(__file__).resolve().parent

    try:
        if candidate.drive and not Path(candidate.drive + "\\").exists():
            raise OSError(f"La unidad {candidate.drive} no está disponible.")
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    except OSError:
        fallback = Path(
            os.getenv(
                "ATLAS_RUNTIME_FALLBACK",
                str(Path(tempfile.gettempdir()) / "atlas_core_runtime"),
            )
        ).expanduser()
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


# Rutas principales.
BASE_DIR = _resolve_base_dir()
DATA_DIR = BASE_DIR / "memory" / "data"
LOG_DIR = BASE_DIR / "logs"
MODEL_DIR = BASE_DIR / "models"

# Subsistemas disponibles por defecto.
CHAT_ENABLED = True
MEMORY_ENABLED = True
AI_ENABLED = False
VOICE_ENABLED = False
TOOLS_ENABLED = False
AUTOMATION_ENABLED = False
INTERNET_ENABLED = False

# Registro de actividad.
LOGGING_ENABLED = True
LOG_LEVEL = "DEBUG" if DEBUG else "INFO"
LOG_FILE = LOG_DIR / "atlas.log"

# Configuración provisional de IA local.
AI_PROVIDER = "ollama"
AI_MODEL: str | None = None


def ensure_runtime_directories() -> None:
    """Crea las carpetas de ejecución necesarias si todavía no existen."""

    for directory in (DATA_DIR, LOG_DIR):
        directory.mkdir(parents=True, exist_ok=True)
