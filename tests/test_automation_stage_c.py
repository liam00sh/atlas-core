"""Pruebas de las primeras herramientas seguras de la Etapa C."""

from pathlib import Path

import pytest

from automation.automation_permissions import AutomationPermissions, UserAccess
from automation.automation_registry import AutomationRegistry
from automation.backup_adapter import BackupAdapter, BackupPlan
from automation.notification_adapter import NotificationAdapter
from automation.service_monitor import ServiceMonitor, ServiceProbe
from automation.stage_c_catalog import register_stage_c_actions
from automation.technical_routines import (
    RoutineStep,
    TechnicalRoutine,
    TechnicalRoutineRegistry,
)


class FakeNotifier:
    def __init__(self):
        self.sent = []

    def send(self, recipient_user_id, message):
        self.sent.append((recipient_user_id, message))
        return True


@pytest.fixture
def monitor():
    monitor = ServiceMonitor()
    monitor.register(ServiceProbe(
        "telegram",
        "Telegram",
        checker=lambda: {"available": True, "pid": 1234},
        critical=True,
    ))
    monitor.register(ServiceProbe(
        "ollama",
        "Ollama",
        checker=lambda: False,
    ))
    return monitor


def test_service_monitor_summary(monitor):
    summary = monitor.summary()
    assert summary["total_services"] == 2
    assert summary["healthy_services"] == 1
    assert summary["critical_unavailable"] == []


def test_unknown_service_is_rejected(monitor):
    with pytest.raises(LookupError):
        monitor.check("inventado")


def test_backup_uses_closed_plan(tmp_path):
    adapter = BackupAdapter(tmp_path)
    adapter.register(BackupPlan(
        "atlas.manual",
        "Copia manual de Atlas",
        runner=lambda: {"archive": "atlas.zip", "verified": True},
    ))
    result = adapter.create("atlas.manual")
    assert result["result"]["verified"] is True
    assert Path(result["manifest_path"]).exists()


def test_disabled_backup_plan_is_blocked(tmp_path):
    adapter = BackupAdapter(tmp_path)
    adapter.register(BackupPlan(
        "disabled",
        "Deshabilitada",
        runner=lambda: {},
        allowed=False,
    ))
    with pytest.raises(PermissionError):
        adapter.create("disabled")


def test_notification_adapter_validates_and_sends():
    provider = FakeNotifier()
    adapter = NotificationAdapter(provider)
    receipt = adapter.send("REDACTED_2c7b6821719d", "Incidencia", "Telegram no responde")
    assert receipt.delivered is True
    assert provider.sent[0][0] == "REDACTED_2c7b6821719d"


def test_notification_rejects_empty_message():
    provider = FakeNotifier()
    adapter = NotificationAdapter(provider)
    with pytest.raises(ValueError):
        adapter.send("REDACTED_2c7b6821719d", "Aviso", "")


def test_technical_routine_stops_on_error():
    registry = TechnicalRoutineRegistry()
    registry.register(TechnicalRoutine(
        routine_id="health.check",
        name="Comprobación",
        steps=(
            RoutineStep("first", lambda params: "ok"),
            RoutineStep("second", lambda params: 1 / 0),
            RoutineStep("third", lambda params: "never"),
        ),
    ))
    result = registry.run("health.check")
    assert result["success"] is False
    assert len(result["steps"]) == 2


def test_stage_c_catalog_registers_five_actions(tmp_path, monitor):
    registry = AutomationRegistry()
    backup = BackupAdapter(tmp_path)
    backup.register(BackupPlan(
        "atlas.manual",
        "Copia manual",
        runner=lambda: {"ok": True},
    ))
    notifier = NotificationAdapter(FakeNotifier())
    routines = TechnicalRoutineRegistry()
    routines.register(TechnicalRoutine(
        "health.check",
        "Comprobación",
        (RoutineStep("status", lambda params: "ok"),),
    ))

    register_stage_c_actions(
        registry,
        service_monitor=monitor,
        backup_adapter=backup,
        notification_adapter=notifier,
        routine_registry=routines,
    )

    assert registry.count == 5
    assert registry.get("atlas.status.read").technical_only is False
    assert registry.get("backup.manual.create").technical_only is True


def test_permissions_can_distinguish_status_and_backup():
    permissions = AutomationPermissions({
        "REDACTED_aebac53c46bb": UserAccess(
            "REDACTED_aebac53c46bb",
            permissions={"system.status.read"},
        ),
        "REDACTED_2c7b6821719d": UserAccess(
            "REDACTED_2c7b6821719d",
            roles={"owner"},
        ),
    })
    assert "system.status.read" in permissions.get_user("REDACTED_aebac53c46bb").permissions
    assert permissions.get_user("REDACTED_2c7b6821719d").is_admin is True
