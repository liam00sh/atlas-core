"""
Proyecto Atlas
Archivo: automation/stage_d_catalog.py

Registro compatible con el motor común de automatizaciones.
"""

from __future__ import annotations

from automation.automation_registry import AutomationRegistry
from automation.models import (
    ActionDefinition,
    AutomationRisk,
    ConfirmationLevel,
)
from automation.windows_adapter import WindowsAdapter


def _handler(
    adapter: WindowsAdapter,
    action_id: str,
):
    def execute(parameters: dict[str, object]) -> dict[str, object]:
        return adapter.execute(
            action_id,
            parameters=parameters,
            permissions={_required_permission_for(action_id)},
            is_admin=True,
        )
    return execute



def _required_permission_for(action_id: str) -> str:
    mapping = {
        "windows.system.info.read": "windows.status.read",
        "windows.disk.space.read": "windows.status.read",
        "windows.process.status.read": "windows.process.read",
        "windows.application.open": "windows.application.open",
    }
    try:
        return mapping[action_id]
    except KeyError as exc:
        raise ValueError(f"Acción Windows sin permiso asociado: {action_id}") from exc


def register_stage_d_actions(
    registry: AutomationRegistry,
    windows_adapter: WindowsAdapter | None = None,
) -> None:
    adapter = windows_adapter or WindowsAdapter()

    registry.register_many(
        (
            ActionDefinition(
                action_id="windows.system.info.read",
                name="Consultar sistema Windows",
                description="Consulta información básica del sistema.",
                handler=_handler(adapter, "windows.system.info.read"),
                required_permission="windows.status.read",
                risk=AutomationRisk.SAFE,
                confirmation=ConfirmationLevel.NONE,
                allowed_parameters=frozenset(),
            ),
            ActionDefinition(
                action_id="windows.disk.space.read",
                name="Consultar espacio de disco",
                description="Consulta el espacio de una ruta existente.",
                handler=_handler(adapter, "windows.disk.space.read"),
                required_permission="windows.status.read",
                risk=AutomationRisk.SAFE,
                confirmation=ConfirmationLevel.NONE,
                allowed_parameters=frozenset({"path"}),
            ),
            ActionDefinition(
                action_id="windows.process.status.read",
                name="Consultar proceso Windows",
                description="Consulta si un proceso concreto está activo.",
                handler=_handler(adapter, "windows.process.status.read"),
                required_permission="windows.process.read",
                risk=AutomationRisk.SAFE,
                confirmation=ConfirmationLevel.NONE,
                allowed_parameters=frozenset({"process_name"}),
                technical_only=True,
            ),
            ActionDefinition(
                action_id="windows.application.open",
                name="Abrir aplicación Windows",
                description="Abre una aplicación incluida en la lista autorizada.",
                handler=_handler(adapter, "windows.application.open"),
                required_permission="windows.application.open",
                risk=AutomationRisk.SAFE,
                confirmation=ConfirmationLevel.NONE,
                allowed_parameters=frozenset({"app_id"}),
            ),
        )
    )
