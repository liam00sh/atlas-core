from __future__ import annotations

import pytest

from automation.automation_permissions import UserAccess
from automation.home_intent_service import HomeIntentService
from automation.stage_e_runtime import build_stage_e_simulation


@pytest.fixture
def atlas(tmp_path, monkeypatch):
    """Construye Atlas con Home Assistant simulado y persistencia temporal."""

    import core.atlas as atlas_module

    environment = build_stage_e_simulation(tmp_path / "stage_e.json")
    monkeypatch.setattr(
        atlas_module,
        "build_stage_e_environment",
        lambda *args, **kwargs: environment,
    )
    monkeypatch.setenv("HOME_ASSISTANT_MODE", "simulated")
    instance = atlas_module.Atlas(ai_provider=None)
    assert instance.stage_e_environment.simulator is not None
    return instance


def _run(atlas, capsys, text: str) -> str:
    capsys.readouterr()
    assert atlas.process(text) is True
    return capsys.readouterr().out


def _configure_user(
    atlas,
    name: str,
    *,
    roles: set[str],
    profile_permissions: set[str] = frozenset(),
    home_permissions: set[str] = frozenset(),
) -> None:
    profile = atlas.users.get_profile(name)
    profile["roles"] = sorted(roles)
    profile["permissions"] = sorted(profile_permissions)
    atlas.users.current_user = name
    atlas.stage_e_environment.manager.permissions.set_user(
        UserAccess(
            user_id=name,
            roles=set(roles),
            permissions=set(home_permissions),
        )
    )


def _light_state(atlas) -> str:
    entity_id = atlas.home_intent_service.resolver.light_entity_id
    return atlas.stage_e_environment.adapter.get_state(entity_id)["state"]


def test_Vega_home_verified_sees_and_executes_light(atlas, capsys):
    _configure_user(
        atlas,
        "Vega",
        roles={"family"},
        home_permissions={"home.control.light"},
    )
    atlas.stage_e_environment.set_guest_presence("Vega", True)

    help_output = _run(atlas, capsys, "ayuda luz")
    assert "encender luz" in help_output.casefold()
    assert _light_state(atlas) == "off"

    execution_output = _run(atlas, capsys, "enciende la luz")
    assert "he encendido" in execution_output.casefold()
    assert _light_state(atlas) == "on"


def test_Vega_away_neither_sees_nor_executes_light(atlas, capsys):
    _configure_user(
        atlas,
        "Vega",
        roles={"family"},
        home_permissions={"home.control.light"},
    )
    atlas.stage_e_environment.set_guest_presence("Vega", False)

    help_output = _run(atlas, capsys, "ayuda luz")
    assert "encender luz" not in help_output.casefold()
    execution_output = _run(atlas, capsys, "enciende la luz")
    assert "he encendido" not in execution_output.casefold()
    assert _light_state(atlas) == "off"


def test_Vega_unknown_presence_neither_sees_nor_executes_light(
    atlas, capsys, monkeypatch
):
    _configure_user(
        atlas,
        "Vega",
        roles={"family"},
        home_permissions={"home.control.light"},
    )

    def unavailable_presence(_environment, _user_id):
        raise RuntimeError("simulated presence provider failure")

    monkeypatch.setattr(
        type(atlas.stage_e_environment),
        "is_guest_present",
        unavailable_presence,
    )

    help_output = _run(atlas, capsys, "ayuda luz")
    assert "encender luz" not in help_output.casefold()
    execution_output = _run(atlas, capsys, "enciende la luz")
    assert "he encendido" not in execution_output.casefold()
    assert _light_state(atlas) == "off"


def test_family_member_without_permission_neither_sees_nor_creates_profile(atlas, capsys):
    _configure_user(atlas, "Carla", roles={"family"})
    person = atlas.people_manager.find_person_by_name("Diego")
    assert person is not None and not person.is_user()

    help_output = _run(atlas, capsys, "ayuda crear perfil de usuario")
    assert "• crear perfil de usuario:" not in help_output.casefold()
    execution_output = _run(atlas, capsys, "crear perfil de usuario para Diego")
    assert "solo alex" in execution_output.casefold()
    assert not person.is_user()


def test_non_owner_admin_neither_sees_nor_executes_owner_only(atlas, capsys):
    _configure_user(atlas, "Operador", roles={"administrator"})
    person = atlas.people_manager.find_person_by_name("Diego")
    assert person is not None and not person.is_user()

    help_output = _run(atlas, capsys, "ayuda crear perfil de usuario")
    assert "• crear perfil de usuario:" not in help_output.casefold()
    execution_output = _run(atlas, capsys, "crear perfil de usuario para Diego")
    assert "solo alex" in execution_output.casefold()
    assert not person.is_user()


def test_Alex_owner_sees_and_executes_owner_only(atlas, capsys):
    _configure_user(atlas, "Alex", roles={"owner"})
    person = atlas.people_manager.find_person_by_name("Diego")
    assert person is not None and not person.is_user()

    help_output = _run(atlas, capsys, "ayuda crear perfil de usuario")
    assert "crear perfil de usuario" in help_output.casefold()
    execution_output = _run(atlas, capsys, "crear perfil de usuario para Diego")
    assert "perfil atlas creado" in execution_output.casefold()
    assert atlas.people_manager.find_person_by_name("Diego").is_user()


@pytest.mark.parametrize(
    "query",
    (
        "ayuda encender luz del acuario pequeño",
        "ayuda activa la luz",
        "ayuda encender lus",
        "buscar comandos luz",
        "cómo hago para encender la luz",
    ),
)
def test_guest_cannot_discover_home_actions_by_any_help_route(
    atlas, capsys, query
):
    atlas.start_guest_session("Invitado")
    output = _run(atlas, capsys, query)
    assert "encender luz del acuario" not in output.casefold()
    assert "enciende la luz del acuario" not in output.casefold()


def test_guest_neither_sees_nor_executes_home_or_admin_actions(atlas, capsys):
    atlas.start_guest_session("Invitado")

    general_help = _run(atlas, capsys, "ayuda")
    assert "encender luz" not in general_help.casefold()
    assert "crear perfil de usuario" not in general_help.casefold()

    home_output = _run(atlas, capsys, "enciende la luz")
    admin_output = _run(atlas, capsys, "crear perfil de usuario para Diego")
    assert "no tiene permiso" in home_output.casefold()
    assert "no tiene permiso" in admin_output.casefold()
    assert _light_state(atlas) == "off"
