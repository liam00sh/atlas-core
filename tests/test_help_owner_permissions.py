from commands import admin_policy
from console.command_help import render_help_for_user


def test_Alex_owner_sees_admin_commands():
    result = render_help_for_user(
        {
            "name": "Alex",
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
    assert "sistema y administración" in result.casefold()
    assert "copia de seguridad" in result
    assert "estado de Atlas" in result
    assert "reinicia atlas" in result


def test_non_admin_does_not_see_owner_commands():
    result = render_help_for_user(
        {
            "name": "Carla",
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


def test_guest_and_missing_context_do_not_see_owner_commands():
    for user in (
        None,
        {
            "name": "Invitado",
            "profile_exists": False,
            "is_admin": False,
            "is_owner": False,
            "permissions": ["atlas_admin"],
        },
    ):
        result = render_help_for_user(user, channel="pc").casefold()
        assert "estado de atlas" not in result
        assert "reinicia atlas" not in result
        assert "reinicia telegram" not in result


def test_family_permissions_show_only_authorized_help():
    result = render_help_for_user(
        {
            "name": "Carla",
            "role": "family",
            "profile_exists": True,
            "permissions": ["internet_lookup"],
        },
        channel="pc",
    ).casefold()
    assert "buscar en internet" in result
    assert "estado de atlas" not in result
    assert "copia de seguridad" not in result


def test_owner_identity_is_not_inferred_from_an_approximate_name():
    result = render_help_for_user(
        {
            "name": "Alex invitado",
            "role": "user",
            "profile_exists": True,
            "permissions": ["conversation", "help"],
        },
        channel="telegram",
    ).casefold()
    assert "estado de atlas" not in result
    assert "reinicia atlas" not in result


def test_filtered_topic_search_does_not_reveal_owner_help():
    result = render_help_for_user(None, topic="estado de Atlas", channel="pc")
    assert "diagnóstico del núcleo" not in result.casefold()


def test_admin_visibility_and_owner_execution_use_verified_identity(monkeypatch):
    admin_help = render_help_for_user(
        {
            "name": "Operador",
            "role": "admin",
            "profile_exists": True,
            "is_admin": True,
            "is_owner": False,
            "permissions": ["atlas_admin"],
        },
        channel="pc",
    ).casefold()
    assert "reinicia atlas" not in admin_help

    class AtlasStub:
        current_user_id = "Alex invitado"

        @staticmethod
        def get_main_user():
            return "Alex"

    monkeypatch.setattr(admin_policy.context, "atlas", AtlasStub())
    assert admin_policy.is_admin_user() is False

    AtlasStub.current_user_id = "Alex"
    assert admin_policy.is_admin_user() is True
