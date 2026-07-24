from types import SimpleNamespace

from automation.pc_access_policy import PresenceStatus, can_access_REDACTED_f73137d930c3_pc
from automation.stage_d_bootstrap import build_stage_d_permissions
from commands import admin_policy


def test_restart_permissions_are_admin_only(monkeypatch):
    monkeypatch.setattr(
        admin_policy.context,
        "atlas",
        SimpleNamespace(current_user_id="REDACTED_f73137d930c3"),
    )
    assert admin_policy.is_admin_user() is True

    monkeypatch.setattr(
        admin_policy.context,
        "atlas",
        SimpleNamespace(current_user_id="REDACTED_7b9528898599"),
    )
    assert admin_policy.is_admin_user() is False


def test_REDACTED_7b9528898599_has_no_pc_application_permission_until_presence_is_verified():
    permissions = build_stage_d_permissions()
    assert "windows.application.open" in permissions.get_user("REDACTED_f73137d930c3").permissions
    assert "windows.application.open" not in permissions.get_user("REDACTED_7b9528898599").permissions


def test_REDACTED_7b9528898599_pc_access_is_denied_when_presence_unknown():
    decision = can_access_REDACTED_f73137d930c3_pc(
        user_id="REDACTED_7b9528898599",
        presence=PresenceStatus.UNKNOWN,
    )
    assert decision.allowed is False
    assert decision.reason == "home_presence_not_verified"


def test_REDACTED_7b9528898599_pc_access_can_be_enabled_only_when_home_is_verified():
    decision = can_access_REDACTED_f73137d930c3_pc(
        user_id="REDACTED_7b9528898599",
        presence=PresenceStatus.HOME_VERIFIED,
    )
    assert decision.allowed is True
