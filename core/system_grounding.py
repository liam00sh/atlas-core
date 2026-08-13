"""Consultas locales de estado que nunca se delegan al modelo."""

from __future__ import annotations

import shutil
import subprocess


def grounded_docker_status(*, timeout_seconds: float = 4.0) -> str:
    executable = shutil.which("docker")
    if not executable:
        return "No puedo comprobar Docker porque el ejecutable no está disponible en este equipo."
    try:
        completed = subprocess.run(
            [executable, "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "No he podido comprobar el motor de Docker de forma fiable."
    version = completed.stdout.strip()
    if completed.returncode == 0 and version:
        return f"Sí. He consultado el motor local de Docker y está respondiendo; versión del servidor {version}."
    return "Docker está instalado, pero el motor no está respondiendo ahora mismo."
