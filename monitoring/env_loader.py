"""
Proyecto Atlas
Archivo: monitoring/env_loader.py

Carga segura del archivo .env para los módulos de monitorización.
"""

from __future__ import annotations

from pathlib import Path


def load_monitoring_env() -> bool:
    """
    Carga el archivo .env de la raíz del proyecto.

    Devuelve True si python-dotenv está disponible y la carga se realiza.
    Devuelve False si la dependencia no está instalada.
    """
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return False

    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")
    return True
