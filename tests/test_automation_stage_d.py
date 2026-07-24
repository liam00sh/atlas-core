"""Pruebas de la Fase 5, Etapa D: integración segura con Windows."""

from pathlib import Path

import pytest

from automation.windows_adapter import (
    WindowsAction,
    WindowsActionCatalog,
    WindowsActionError,
    WindowsAdapter,
    build_stage_d_windows_catalog,
)


def test_catalog_is_closed() -> None:
    adapter = WindowsAdapter(build_stage_d_windows_catalog())

    with pytest.raises(WindowsActionError):
        adapter.execute(
            "windows.powershell.run",
            permissions={"windows.status.read"},
            is_admin=True,
        )


def test_system_info_requires_permission() -> None:
    adapter = WindowsAdapter()

    with pytest.raises(PermissionError):
        adapter.execute("windows.system.info.read")


def test_system_info_is_read_only_and_needs_no_confirmation() -> None:
    adapter = WindowsAdapter()

    result = adapter.execute(
        "windows.system.info.read",
        permissions={"windows.status.read"},
    )

    assert result["ok"] is True
    assert result["risk_level"] == 0
    assert "platform" in result["result"]


def test_disk_space_rejects_missing_path(tmp_path: Path) -> None:
    adapter = WindowsAdapter()

    with pytest.raises(WindowsActionError):
        adapter.execute(
            "windows.disk.space.read",
            parameters={"path": str(tmp_path / "missing")},
            permissions={"windows.status.read"},
        )


def test_disk_space_accepts_existing_path(tmp_path: Path) -> None:
    adapter = WindowsAdapter()

    result = adapter.execute(
        "windows.disk.space.read",
        parameters={"path": str(tmp_path)},
        permissions={"windows.status.read"},
    )

    assert result["result"]["free_bytes"] >= 0


def test_admin_only_action_is_blocked_for_family_user() -> None:
    adapter = WindowsAdapter()

    with pytest.raises(PermissionError):
        adapter.execute(
            "windows.process.status.read",
            parameters={"process_name": "python.exe"},
            permissions={"windows.process.read"},
            is_admin=False,
        )


def test_sensitive_action_requires_confirmation() -> None:
    catalog = WindowsActionCatalog()
    catalog.register(
        WindowsAction(
            action_id="windows.test.sensitive",
            description="Acción sensible simulada.",
            risk_level=2,
            required_permission="windows.test",
            requires_confirmation=True,
            admin_only=True,
            handler=lambda _: {"done": True},
        )
    )
    adapter = WindowsAdapter(catalog)

    with pytest.raises(WindowsActionError):
        adapter.execute(
            "windows.test.sensitive",
            permissions={"windows.test"},
            is_admin=True,
            confirmed=False,
        )


def test_arbitrary_application_is_rejected() -> None:
    adapter = WindowsAdapter()

    with pytest.raises(WindowsActionError):
        adapter.execute(
            "windows.application.open",
            parameters={"app_id": "powershell"},
            permissions={"windows.application.open"},
        )


def test_catalog_contains_only_initial_authorized_actions() -> None:
    ids = {
        action.action_id
        for action in build_stage_d_windows_catalog().list_actions()
    }

    assert ids == {
        "windows.system.info.read",
        "windows.disk.space.read",
        "windows.process.status.read",
        "windows.application.open",
    }
