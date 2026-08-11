"""Pruebas integradas de la Etapa D contra el motor común."""

from pathlib import Path
import platform

import pytest

from automation.automation_permissions import AutomationPermissions, UserAccess
from automation.automation_registry import AutomationRegistry
from automation.models import AutomationStatus
from automation.stage_d_catalog import register_stage_d_actions
from automation.windows_adapter import WindowsActionError, WindowsAdapter


def _manager(tmp_path: Path):
    from automation.automation_manager import AutomationManager

    registry = AutomationRegistry()
    register_stage_d_actions(registry)

    permissions = AutomationPermissions()
    permissions.set_user(
        UserAccess(
            user_id="Alex",
            roles={"owner"},
            permissions={
                "windows.status.read",
                "windows.process.read",
                "windows.application.open",
            },
        )
    )
    permissions.set_user(
        UserAccess(
            user_id="Vega",
            roles={"family"},
            permissions={
                "windows.status.read",
                "windows.application.open",
            },
        )
    )
    permissions.set_user(
        UserAccess(
            user_id="Carla",
            roles={"family"},
            permissions=set(),
        )
    )
    return AutomationManager(
        storage_path=tmp_path / "automations.json",
        registry=registry,
        permissions=permissions,
    )


def test_stage_d_catalog_matches_existing_contract() -> None:
    registry = AutomationRegistry()
    register_stage_d_actions(registry)

    assert {item.action_id for item in registry.list_actions()} == {
        "windows.system.info.read",
        "windows.disk.space.read",
        "windows.process.status.read",
        "windows.application.open",
    }


def test_Alex_can_execute_system_info(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    automation = manager.create(
        action_id="windows.system.info.read",
        owner_user_id="Alex",
        creator_user_id="Alex",
    )

    result = manager.execute(
        automation.automation_id,
        requested_by_user_id="Alex",
        channel="test",
    )

    assert result.success is True
    assert result.status is AutomationStatus.COMPLETED


def test_Vega_can_open_authorized_app_by_permission(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    automation = manager.create(
        action_id="windows.application.open",
        owner_user_id="Vega",
        creator_user_id="Vega",
        parameters={"app_id": "notepad"},
    )

    if platform.system().casefold() == "windows":
        result = manager.execute(
            automation.automation_id,
            requested_by_user_id="Vega",
            channel="test",
        )
        assert result.success is True
    else:
        result = manager.execute(
            automation.automation_id,
            requested_by_user_id="Vega",
            channel="test",
        )
        assert result.success is False
        assert result.error_code == "WindowsActionError"


def test_Carla_cannot_open_windows_apps(tmp_path: Path) -> None:
    manager = _manager(tmp_path)
    automation = manager.create(
        action_id="windows.application.open",
        owner_user_id="Carla",
        creator_user_id="Carla",
        parameters={"app_id": "calculator"},
    )

    result = manager.execute(
        automation.automation_id,
        requested_by_user_id="Carla",
        channel="test",
    )

    assert result.success is False
    assert result.error_code == "permission_denied"


def test_family_user_cannot_create_technical_action(tmp_path: Path) -> None:
    manager = _manager(tmp_path)

    with pytest.raises(PermissionError):
        manager.create(
            action_id="windows.process.status.read",
            owner_user_id="Vega",
            creator_user_id="Vega",
            parameters={"process_name": "python.exe"},
        )


def test_unknown_parameters_are_rejected_before_execution(tmp_path: Path) -> None:
    manager = _manager(tmp_path)

    with pytest.raises(ValueError):
        manager.create(
            action_id="windows.application.open",
            owner_user_id="Alex",
            creator_user_id="Alex",
            parameters={
                "app_id": "notepad",
                "command": "powershell",
            },
        )


def test_unregistered_application_is_rejected() -> None:
    adapter = WindowsAdapter()

    with pytest.raises(WindowsActionError):
        adapter.execute(
            "windows.application.open",
            {"app_id": "powershell"},
        )


def test_arbitrary_action_is_rejected() -> None:
    adapter = WindowsAdapter()

    with pytest.raises(WindowsActionError):
        adapter.execute("windows.command.run", {})
