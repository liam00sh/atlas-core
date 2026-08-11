from console.command_help import (
    HelpEntry,
    build_help_access_context,
    _entry_visible_for_context,
)


def admin_entry():
    return HelpEntry(
        "crear usuario",
        "x",
        "Usuarios",
        (),
        (),
        owner_only=True,
        capability="user_management",
    )


def internet_entry():
    return HelpEntry(
        "internet",
        "x",
        "Internet y fuentes",
        (),
        (),
        capability="internet_lookup",
    )


def backup_entry():
    return HelpEntry(
        "backup",
        "x",
        "Sistema y administración",
        (),
        (),
        capability="backups",
    )


def test_Alex_own_bot_admin_sees_all():
    context = build_help_access_context(
        channel="telegram",
        authenticated_user="Alex",
        profile_exists=True,
        is_admin=True,
        is_owner=True,
        guest_session=None,
        permissions={"atlas_admin", "user_management"},
    )
    assert _entry_visible_for_context(admin_entry(), context)


def test_Alex_other_bot_is_guest():
    context = build_help_access_context(
        channel="telegram",
        authenticated_user="Alex",
        profile_exists=True,
        is_admin=True,
        is_owner=True,
        guest_session=object(),
        permissions={"atlas_admin", "user_management"},
    )
    assert context.effective_role == "guest"
    assert not _entry_visible_for_context(admin_entry(), context)


def test_family_profile_on_pc_keeps_profile_permissions():
    context = build_help_access_context(
        channel="pc",
        authenticated_user="Carla",
        profile_exists=True,
        is_admin=False,
        guest_session=None,
        permissions={"internet_lookup"},
    )
    assert _entry_visible_for_context(internet_entry(), context)
    assert not _entry_visible_for_context(backup_entry(), context)


def test_family_profile_on_other_bot_is_guest():
    context = build_help_access_context(
        channel="telegram",
        authenticated_user="Carla",
        profile_exists=True,
        is_admin=False,
        guest_session=object(),
        permissions={"internet_lookup", "memory"},
    )
    assert context.effective_role == "guest"
    assert _entry_visible_for_context(internet_entry(), context)
    assert not _entry_visible_for_context(backup_entry(), context)


def test_unknown_pc_user_is_guest():
    context = build_help_access_context(
        channel="pc",
        authenticated_user="Diego",
        profile_exists=False,
        is_admin=False,
        guest_session=None,
        permissions={"atlas_admin"},
    )
    assert context.effective_role == "guest"
    assert not _entry_visible_for_context(backup_entry(), context)
