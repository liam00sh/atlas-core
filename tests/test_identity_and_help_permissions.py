from core.guest_session import GuestSessionManager
from console.command_help import (
    HelpEntry,
    build_help_access_context,
    _entry_visible_for_context,
)


def test_guest_identity_is_current_interlocutor():
    manager = GuestSessionManager()
    manager.start(
        host_user="Alex",
        guest_name="Zoe",
        assistant_name="Daxter",
    )
    assert manager.get().guest_name == "Zoe"


def test_admin_own_bot_sees_admin_entry():
    context = build_help_access_context(
        channel="telegram",
        authenticated_user="Alex",
        profile_exists=True,
        is_admin=True,
        is_owner=True,
        guest_session=None,
        permissions={"atlas_admin"},
    )
    entry = HelpEntry(
        "crear usuario", "x", "Usuarios", (), (),
        owner_only=True,
        capability="user_management",
    )
    assert _entry_visible_for_context(entry, context)


def test_admin_on_other_bot_is_guest():
    context = build_help_access_context(
        channel="telegram",
        authenticated_user="Alex",
        profile_exists=True,
        is_admin=True,
        is_owner=True,
        guest_session=object(),
        permissions={"atlas_admin"},
    )
    entry = HelpEntry(
        "crear usuario", "x", "Usuarios", (), (),
        owner_only=True,
        capability="user_management",
    )
    assert not _entry_visible_for_context(entry, context)


def test_known_pc_user_keeps_profile_permissions():
    context = build_help_access_context(
        channel="pc",
        authenticated_user="Carla",
        profile_exists=True,
        is_admin=False,
        guest_session=None,
        permissions={"internet_lookup"},
    )
    allowed = HelpEntry(
        "internet", "x", "Internet y fuentes", (), (),
        capability="internet_lookup",
    )
    blocked = HelpEntry(
        "backup", "x", "Sistema y administración", (), (),
        capability="backups",
    )
    assert _entry_visible_for_context(allowed, context)
    assert not _entry_visible_for_context(blocked, context)


def test_unknown_pc_user_is_guest():
    context = build_help_access_context(
        channel="pc",
        authenticated_user="Diego",
        profile_exists=False,
        is_admin=False,
        guest_session=None,
        permissions={"atlas_admin"},
    )
    blocked = HelpEntry(
        "backup", "x", "Sistema y administración", (), (),
        capability="backups",
    )
    assert context.effective_role == "guest"
    assert not _entry_visible_for_context(blocked, context)
