"""Pruebas unitarias de la Etapa B del motor de automatizaciones."""

from datetime import timedelta

import pytest

from automation.automation_manager import AutomationManager
from automation.automation_permissions import AutomationPermissions, UserAccess
from automation.automation_registry import AutomationRegistry
from automation.models import (
    ActionDefinition,
    AutomationRisk,
    AutomationStatus,
    ConfirmationLevel,
    Visibility,
    utc_now,
)


@pytest.fixture
def permissions():
    return AutomationPermissions({
        "REDACTED_2c7b6821719d": UserAccess(
            "REDACTED_2c7b6821719d",
            roles={"owner"},
            permissions={"automation.execute.safe"},
            groups={"unidad_familiar"},
        ),
        "REDACTED_bc04a68d9192": UserAccess(
            "REDACTED_bc04a68d9192",
            permissions={"automation.execute.safe"},
            groups={"unidad_familiar"},
        ),
        "REDACTED_aebac53c46bb": UserAccess(
            "REDACTED_aebac53c46bb",
            permissions={"automation.execute.safe"},
            groups={"unidad_familiar"},
        ),
        "system": UserAccess(
            "system",
            roles={"administrator"},
            permissions={"automation.execute.safe"},
        ),
    })


@pytest.fixture
def registry():
    registry = AutomationRegistry()
    registry.register(ActionDefinition(
        action_id="reminder.create",
        name="Crear recordatorio",
        description="Crea un recordatorio seguro.",
        handler=lambda params: {"message": params["message"]},
        required_permission="automation.execute.safe",
        allowed_parameters=frozenset({"message"}),
    ))
    registry.register(ActionDefinition(
        action_id="service.telegram.restart",
        name="Reiniciar Telegram",
        description="Reinicia el servicio registrado.",
        handler=lambda params: "ok",
        required_permission="automation.execute.technical",
        risk=AutomationRisk.SENSITIVE,
        confirmation=ConfirmationLevel.SIMPLE,
        technical_only=True,
    ))
    return registry


@pytest.fixture
def manager(tmp_path, registry, permissions):
    return AutomationManager(
        tmp_path / "automations.json",
        registry=registry,
        permissions=permissions,
    )


def test_private_automation_isolated(manager):
    item = manager.create(
        action_id="reminder.create",
        owner_user_id="REDACTED_aebac53c46bb",
        creator_user_id="REDACTED_aebac53c46bb",
        parameters={"message": "Comprar pan"},
    )
    assert manager.get(item.automation_id, "REDACTED_aebac53c46bb") is item
    with pytest.raises(PermissionError):
        manager.get(item.automation_id, "REDACTED_bc04a68d9192")


def test_family_group_can_view_shared_resource(manager):
    item = manager.create(
        action_id="reminder.create",
        owner_user_id="REDACTED_aebac53c46bb",
        creator_user_id="REDACTED_aebac53c46bb",
        parameters={"message": "Comprar champú"},
        visibility=Visibility.SHARED,
        shared_group_ids=["unidad_familiar"],
    )
    assert manager.get(item.automation_id, "REDACTED_bc04a68d9192") is item


def test_admin_can_view_private_automation(manager):
    item = manager.create(
        action_id="reminder.create",
        owner_user_id="REDACTED_aebac53c46bb",
        creator_user_id="REDACTED_aebac53c46bb",
        parameters={"message": "Privado"},
    )
    assert manager.get(item.automation_id, "REDACTED_2c7b6821719d") is item


def test_non_admin_cannot_create_technical_automation(manager):
    with pytest.raises(PermissionError):
        manager.create(
            action_id="service.telegram.restart",
            owner_user_id="REDACTED_bc04a68d9192",
            creator_user_id="REDACTED_bc04a68d9192",
        )


def test_confirmation_is_required(manager):
    item = manager.create(
        action_id="service.telegram.restart",
        owner_user_id="REDACTED_2c7b6821719d",
        creator_user_id="REDACTED_2c7b6821719d",
    )
    result = manager.execute(
        item.automation_id,
        requested_by_user_id="REDACTED_2c7b6821719d",
        channel="telegram",
    )
    assert result.error_code == "confirmation_required"
    assert item.status == AutomationStatus.PENDING_CONFIRMATION


def test_confirmed_technical_action_executes(manager):
    item = manager.create(
        action_id="service.telegram.restart",
        owner_user_id="REDACTED_2c7b6821719d",
        creator_user_id="REDACTED_2c7b6821719d",
    )
    result = manager.execute(
        item.automation_id,
        requested_by_user_id="REDACTED_2c7b6821719d",
        channel="telegram",
        confirmed=True,
    )
    assert result.success is True
    assert item.status == AutomationStatus.COMPLETED


def test_parameters_outside_catalog_are_rejected(manager):
    with pytest.raises(ValueError):
        manager.create(
            action_id="reminder.create",
            owner_user_id="REDACTED_aebac53c46bb",
            creator_user_id="REDACTED_aebac53c46bb",
            parameters={
                "message": "Comprar pan",
                "shell": "rm -rf /",
            },
        )


def test_persistence_roundtrip(tmp_path, registry, permissions):
    path = tmp_path / "automations.json"
    first = AutomationManager(path, registry, permissions)
    item = first.create(
        action_id="reminder.create",
        owner_user_id="REDACTED_aebac53c46bb",
        creator_user_id="REDACTED_aebac53c46bb",
        parameters={"message": "Persistente"},
    )
    second = AutomationManager(path, registry, permissions)
    loaded = second.get(item.automation_id, "REDACTED_aebac53c46bb")
    assert loaded.parameters["message"] == "Persistente"


def test_scheduler_executes_due_automation(manager):
    item = manager.create(
        action_id="reminder.create",
        owner_user_id="REDACTED_aebac53c46bb",
        creator_user_id="REDACTED_aebac53c46bb",
        parameters={"message": "Ahora"},
        scheduled_for=utc_now() - timedelta(seconds=1),
    )
    results = manager.run_due()
    assert results[0].success is True
    assert item.status == AutomationStatus.COMPLETED


def test_audit_redacts_secrets(manager):
    item = manager.create(
        action_id="reminder.create",
        owner_user_id="REDACTED_aebac53c46bb",
        creator_user_id="REDACTED_aebac53c46bb",
        parameters={"message": "Sin secretos"},
        metadata={"password": "1234"},
    )
    manager.audit.record(
        __import__("automation.models", fromlist=["AuditEvent"]).AuditEvent(
            event_type="test.secret",
            automation_id=item.automation_id,
            action_id=item.action_id,
            owner_user_id=item.owner_user_id,
            requested_by_user_id="REDACTED_aebac53c46bb",
            channel="test",
            details={"password": "1234", "safe": "ok"},
        )
    )
    event = manager.audit.read_all()[-1]
    assert event["details"]["password"] == "[REDACTADO]"
    assert event["details"]["safe"] == "ok"
