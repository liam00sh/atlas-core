"""Construcción del entorno real de la Etapa C."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from automation.backup_adapter import BackupAdapter
from automation.notification_adapter import NotificationAdapter
from automation.service_monitor import ServiceMonitor
from automation.stage_c_catalog import register_stage_c_actions
from automation.stage_c_integrations import (
    TelegramPrivateNotificationProvider,
    build_atlas_probe,
    build_disk_probe,
    build_drive_probe,
    build_health_check_routine,
    build_manual_project_backup_plan,
    build_ollama_probe,
    build_pc_status_probe,
    build_telegram_probe,
)
from automation.technical_routines import TechnicalRoutineRegistry


@dataclass(slots=True)
class StageCEnvironment:
    service_monitor: ServiceMonitor
    backup_adapter: BackupAdapter
    notification_adapter: NotificationAdapter
    routine_registry: TechnicalRoutineRegistry


def build_stage_c_environment(
    *,
    registry: Any,
    project_root: str | Path,
    data_root: str | Path,
    telegram_client: Any | None = None,
    telegram_recipient_resolver: Callable[[str], int | str | None] | None = None,
    ollama_provider: Any | None = None,
    drive_client: Any | None = None,
    atlas_version_getter: Callable[[], str] | None = None,
    atlas_started_getter: Callable[[], bool] | None = None,
) -> StageCEnvironment:
    project_root = Path(project_root)
    data_root = Path(data_root)

    service_monitor = ServiceMonitor()
    service_monitor.register(build_atlas_probe(
        version_getter=atlas_version_getter,
        started_getter=atlas_started_getter,
    ))
    service_monitor.register(build_disk_probe(project_root))
    service_monitor.register(build_pc_status_probe(
        data_root / "monitoring" / "pc_status.json"
    ))

    if telegram_client is not None:
        service_monitor.register(build_telegram_probe(telegram_client))
    if ollama_provider is not None:
        service_monitor.register(build_ollama_probe(ollama_provider))
    if drive_client is not None:
        service_monitor.register(build_drive_probe(drive_client))

    backup_adapter = BackupAdapter(
        data_root / "automation" / "backup_manifests"
    )
    backup_adapter.register(build_manual_project_backup_plan(
        project_root=project_root,
        destination_dir=project_root.parent.parent / "11 - Backups" / "Copias manuales de Atlas",
    ))

    if telegram_client is not None and telegram_recipient_resolver is not None:
        provider = TelegramPrivateNotificationProvider(
            telegram_client,
            telegram_recipient_resolver,
        )
        notification_adapter = NotificationAdapter(provider, channel="telegram")
    else:
        class DisabledNotificationProvider:
            def send(self, recipient_user_id: str, message: str) -> bool:
                return False

        notification_adapter = NotificationAdapter(
            DisabledNotificationProvider(),
            channel="unavailable",
        )

    routine_registry = TechnicalRoutineRegistry()
    routine_registry.register(build_health_check_routine(
        service_summary=service_monitor.summary,
    ))

    register_stage_c_actions(
        registry,
        service_monitor=service_monitor,
        backup_adapter=backup_adapter,
        notification_adapter=notification_adapter,
        routine_registry=routine_registry,
    )

    return StageCEnvironment(
        service_monitor=service_monitor,
        backup_adapter=backup_adapter,
        notification_adapter=notification_adapter,
        routine_registry=routine_registry,
    )
