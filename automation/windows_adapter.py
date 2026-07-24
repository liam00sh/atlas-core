"""
Proyecto Atlas
Archivo: automation/windows_adapter.py

Etapa D — Integración segura con Windows.

Este módulo no acepta comandos arbitrarios. Todas las operaciones deben estar
registradas en un catálogo cerrado y utilizar parámetros validados.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import platform
import shutil
import subprocess
from typing import Callable, Mapping


class WindowsActionError(RuntimeError):
    """Error controlado durante una acción Windows."""


@dataclass(frozen=True)
class WindowsAction:
    action_id: str
    description: str
    risk_level: int
    required_permission: str
    requires_confirmation: bool
    admin_only: bool
    handler: Callable[[Mapping[str, object]], dict[str, object]]


class WindowsActionCatalog:
    """Catálogo cerrado de acciones Windows autorizadas."""

    def __init__(self) -> None:
        self._actions: dict[str, WindowsAction] = {}

    def register(self, action: WindowsAction) -> None:
        if not action.action_id or action.action_id in self._actions:
            raise ValueError(f"Acción Windows inválida o duplicada: {action.action_id!r}")
        if action.risk_level < 0 or action.risk_level > 4:
            raise ValueError("El nivel de riesgo debe estar entre 0 y 4.")
        self._actions[action.action_id] = action

    def get(self, action_id: str) -> WindowsAction:
        try:
            return self._actions[action_id]
        except KeyError as exc:
            raise WindowsActionError(
                f"La acción {action_id!r} no pertenece al catálogo Windows."
            ) from exc

    def list_actions(self) -> tuple[WindowsAction, ...]:
        return tuple(self._actions[key] for key in sorted(self._actions))


class WindowsAdapter:
    """Ejecuta exclusivamente acciones registradas y validadas."""

    def __init__(self, catalog: WindowsActionCatalog | None = None) -> None:
        self.catalog = catalog or build_stage_d_windows_catalog()

    def execute(
        self,
        action_id: str,
        parameters: Mapping[str, object] | None = None,
        *,
        permissions: set[str] | frozenset[str] | None = None,
        confirmed: bool = False,
        is_admin: bool = False,
    ) -> dict[str, object]:
        action = self.catalog.get(action_id)
        permissions = set(permissions or ())
        parameters = dict(parameters or {})

        if action.risk_level >= 4:
            raise WindowsActionError("La acción está prohibida en la Fase 5.")

        # Validaciones estructurales que no ejecutan efectos reales.
        # Se realizan antes de permisos para mantener la compatibilidad con las
        # pruebas legacy del catálogo cerrado y devolver errores de dominio
        # controlados para aplicaciones no registradas.
        if action.action_id == "windows.application.open":
            app_id = str(parameters.get("app_id") or "").strip().casefold()
            if app_id not in {"notepad", "calculator"}:
                raise WindowsActionError(
                    "La aplicación solicitada no está registrada en el catálogo."
                )

        if action.required_permission not in permissions:
            raise PermissionError(
                f"Falta el permiso {action.required_permission!r}."
            )

        if action.admin_only and not is_admin:
            raise PermissionError("La acción está reservada al administrador.")

        if action.requires_confirmation and not confirmed:
            raise WindowsActionError("La acción requiere confirmación explícita.")

        result = action.handler(parameters)
        return {
            "ok": True,
            "action_id": action.action_id,
            "risk_level": action.risk_level,
            "result": result,
        }


def _require_windows() -> None:
    if platform.system().casefold() != "windows":
        raise WindowsActionError("Esta acción solo puede ejecutarse en Windows.")


def _system_info(_: Mapping[str, object]) -> dict[str, object]:
    return {
        "platform": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "computer_name": os.environ.get("COMPUTERNAME", ""),
        "user_name": os.environ.get("USERNAME", ""),
    }


def _disk_space(parameters: Mapping[str, object]) -> dict[str, object]:
    raw_path = str(parameters.get("path") or Path.home().anchor or "C:\\")
    path = Path(raw_path).expanduser()
    if not path.exists():
        raise WindowsActionError(f"La ruta no existe: {path}")
    usage = shutil.disk_usage(path)
    return {
        "path": str(path.resolve()),
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
    }


def _process_status(parameters: Mapping[str, object]) -> dict[str, object]:
    _require_windows()
    process_name = str(parameters.get("process_name") or "").strip()
    if not process_name or any(ch in process_name for ch in "\\/;&|><"):
        raise WindowsActionError("Nombre de proceso inválido.")

    completed = subprocess.run(
        ["tasklist", "/FI", f"IMAGENAME eq {process_name}"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        shell=False,
    )
    if completed.returncode not in {0, 1}:
        raise WindowsActionError("Windows no pudo consultar el proceso.")

    output = completed.stdout.casefold()
    return {
        "process_name": process_name,
        "running": process_name.casefold() in output,
    }


def _open_registered_application(parameters: Mapping[str, object]) -> dict[str, object]:
    _require_windows()
    app_id = str(parameters.get("app_id") or "").strip().casefold()

    applications = {
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
    }
    command = applications.get(app_id)
    if command is None:
        raise WindowsActionError(
            "La aplicación solicitada no está registrada en el catálogo."
        )

    subprocess.Popen(
        command,
        shell=False,
        close_fds=True,
    )
    return {"app_id": app_id, "started": True}


def build_stage_d_windows_catalog() -> WindowsActionCatalog:
    catalog = WindowsActionCatalog()

    catalog.register(
        WindowsAction(
            action_id="windows.system.info.read",
            description="Consultar información básica del sistema Windows.",
            risk_level=0,
            required_permission="windows.status.read",
            requires_confirmation=False,
            admin_only=False,
            handler=_system_info,
        )
    )
    catalog.register(
        WindowsAction(
            action_id="windows.disk.space.read",
            description="Consultar el espacio de una ruta existente.",
            risk_level=0,
            required_permission="windows.status.read",
            requires_confirmation=False,
            admin_only=False,
            handler=_disk_space,
        )
    )
    catalog.register(
        WindowsAction(
            action_id="windows.process.status.read",
            description="Comprobar si un proceso concreto está en ejecución.",
            risk_level=0,
            required_permission="windows.process.read",
            requires_confirmation=False,
            admin_only=True,
            handler=_process_status,
        )
    )
    catalog.register(
        WindowsAction(
            action_id="windows.application.open",
            description="Abrir una aplicación incluida en la lista autorizada.",
            risk_level=1,
            required_permission="windows.application.open",
            requires_confirmation=False,
            admin_only=False,
            handler=_open_registered_application,
        )
    )

    return catalog
