"""Capa de compatibilidad para el sistema de logs de Atlas.

El logger oficial vive en :mod:`core.log_manager`. Este archivo conserva una
ruta de importación antigua para no romper módulos o pruebas existentes.
"""

from core.log_manager import error
from core.log_manager import info
from core.log_manager import warning
from core.log_manager import write

__all__ = [
    "error",
    "info",
    "warning",
    "write",
]
