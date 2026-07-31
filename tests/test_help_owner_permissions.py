from console.command_help import render_help_for_user


def test_REDACTED_f73137d930c3_owner_sees_admin_commands():
    result = render_help_for_user(
        {
            "name": "REDACTED_2c7b6821719d",
            "role": "owner",
            "roles": ["owner", "admin"],
            "profile_exists": True,
            "is_admin": True,
            "is_owner": True,
            "permissions": (),
            "own_bot": True,
        },
        channel="telegram",
    )
    assert "Sistema y administración" in result
    assert "copia de seguridad" in result
    assert "estado de Atlas" in result


def test_non_admin_does_not_see_owner_commands():
    result = render_help_for_user(
        {
            "name": "REDACTED_aebac53c46bb",
            "role": "family",
            "roles": ["family", "known"],
            "profile_exists": True,
            "is_admin": False,
            "is_owner": False,
            "permissions": ["conversation", "help"],
            "own_bot": True,
        },
        channel="telegram",
    )
    assert "copia de seguridad" not in result
    assert "estado de Atlas" not in result
