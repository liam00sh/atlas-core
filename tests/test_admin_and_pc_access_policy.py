from types import SimpleNamespace

from automation.pc_access_policy import PresenceStatus, can_access_Alex_pc
from automation.stage_d_bootstrap import build_stage_d_permissions
from commands import admin_policy


def test_restart_permissions_are_admin_only(monkeypatch):
    monkeypatch.setattr(
        admin_policy.context,
        "atlas",
        SimpleNamespace(current_user_id="Alex"),
    )
    assert admin_policy.is_admin_user() is True

    monkeypatch.setattr(
        admin_policy.context,
        "atlas",
        SimpleNamespace(current_user_id="Vega"),
    )
    assert admin_policy.is_admin_user() is False


def test_Vega_has_no_pc_application_permission_until_presence_is_verified():
    permissions = build_stage_d_permissions()
    assert "windows.application.open" in permissions.get_user("Alex").permissions
    assert "windows.application.open" not in permissions.get_user("Vega").permissions


def test_Vega_pc_access_is_denied_when_presence_unknown():
    decision = can_access_Alex_pc(
        user_id="Vega",
        presence=PresenceStatus.UNKNOWN,
    )
    assert decision.allowed is False
    assert decision.reason == "home_presence_not_verified"


def test_Vega_pc_access_can_be_enabled_only_when_home_is_verified():
    decision = can_access_Alex_pc(
        user_id="Vega",
        presence=PresenceStatus.HOME_VERIFIED,
    )
    assert decision.allowed is True
