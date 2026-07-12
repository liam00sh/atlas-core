"""Configuración central del Proyecto Atlas.

Este módulo reúne valores compartidos por distintos componentes. No debe
contener lógica de negocio ni información secreta.
"""

from pathlib import Path

# Identidad y entorno.
PROJECT_NAME = "Proyecto Atlas"
ASSISTANT_NAME = "Daxter"
DEFAULT_LANGUAGE = "es"
DEBUG = False

# Rutas principales.
BASE_DIR = Path(__file__).resolve().parent
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

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
