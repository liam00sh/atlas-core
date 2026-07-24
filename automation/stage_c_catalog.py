"""Catálogo inicial de acciones seguras para la Etapa C."""

from __future__ import annotations

from automation.backup_adapter import BackupAdapter
from automation.notification_adapter import NotificationAdapter
from automation.service_monitor import ServiceMonitor
from automation.technical_routines import TechnicalRoutineRegistry
from automation.automation_registry import AutomationRegistry
from automation.models import (
    ActionDefinition,
    AutomationRisk,
    ConfirmationLevel,
)


def register_stage_c_actions(
    registry: AutomationRegistry,
    *,
    service_monitor: ServiceMonitor,
    backup_adapter: BackupAdapter,
    notification_adapter: NotificationAdapter,
    routine_registry: TechnicalRoutineRegistry,
) -> None:
    registry.register_many([
        ActionDefinition(
            action_id="atlas.status.read",
            name="Consultar estado general de Atlas",
            description="Resume el estado de los servicios registrados.",
            handler=lambda params: service_monitor.summary(),
            required_permission="system.status.read",
            allowed_parameters=frozenset(),
        ),
        ActionDefinition(
            action_id="service.status.read",
            name="Consultar estado de un servicio",
            description="Comprueba un servicio previamente registrado.",
            handler=lambda params: service_monitor.check(params["service_id"]),
            required_permission="system.status.read",
            allowed_parameters=frozenset({"service_id"}),
        ),
        ActionDefinition(
            action_id="backup.manual.create",
            name="Crear copia manual",
            description="Ejecuta un plan de copia previamente registrado.",
            handler=lambda params: backup_adapter.create(params["plan_id"]),
            required_permission="backup.create",
            risk=AutomationRisk.SENSITIVE,
            confirmation=ConfirmationLevel.SIMPLE,
            allowed_parameters=frozenset({"plan_id"}),
            technical_only=True,
        ),
        ActionDefinition(
            action_id="incident.notification.send",
            name="Enviar notificación de incidencia",
            description="Envía un aviso privado mediante un adaptador registrado.",
            handler=lambda params: notification_adapter.send(
                params["recipient_user_id"],
                params["title"],
                params["message"],
            ),
            required_permission="automation.execute.technical",
            risk=AutomationRisk.SENSITIVE,
            confirmation=ConfirmationLevel.SIMPLE,
            allowed_parameters=frozenset({
                "recipient_user_id", "title", "message"
            }),
            technical_only=True,
        ),
        ActionDefinition(
            action_id="technical.routine.run",
            name="Ejecutar rutina técnica",
            description="Ejecuta una rutina técnica cerrada y registrada.",
            handler=lambda params: routine_registry.run(params["routine_id"]),
            required_permission="routine.execute",
            risk=AutomationRisk.SENSITIVE,
            confirmation=ConfirmationLevel.SIMPLE,
            allowed_parameters=frozenset({"routine_id"}),
            technical_only=True,
        ),
    ])
