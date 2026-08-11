from console.command_help import (
    all_entries,
    build_help_access_context,
    handle_command_help_request,
    inventory_records,
    render_help_for_user,
    search_entries,
)


def user(**overrides):
    payload = {
        "name": "Vega",
        "role": "family",
        "profile_exists": True,
        "permissions": ["conversation", "help", "home.control.light"],
        "presence": "away_verified",
    }
    payload.update(overrides)
    return payload


def test_home_actions_follow_effective_presence():
    away = render_help_for_user(user(), topic="luz")
    home = render_help_for_user(
        user(presence="home_verified"), topic="luz"
    )
    assert "encender luz" not in away.casefold()
    assert "encender luz" in home.casefold()


def test_unknown_presence_uses_safe_policy():
    output = render_help_for_user(user(presence="unknown"), topic="luz")
    assert "encender luz" not in output.casefold()


def test_search_never_reintroduces_hidden_owner_or_home_action():
    alias_ejemplo_04_01 = build_help_access_context(
        channel="pc", authenticated_user="Carla", profile_exists=True,
        is_admin=False, permissions={"conversation", "help"},
    )
    Vega_away = build_help_access_context(
        channel="telegram", authenticated_user="Vega", profile_exists=True,
        is_admin=False, permissions={"home.control.light"},
        presence="away_verified",
    )
    assert not any("crear perfil" in entry.name for entry in search_entries("usuarios", context=alias_ejemplo_04_01))
    assert not any("encender luz" in entry.name for entry in search_entries("luz", context=Vega_away))


def test_owner_only_is_not_visible_to_non_owner_admin():
    output = render_help_for_user(user(
        name="Operador", role="admin", is_admin=True, is_owner=False,
        permissions=["atlas_admin"],
    ))
    assert "reinicia atlas" not in output.casefold()


def test_channel_exclusive_command_is_hidden_from_telegram():
    owner = user(
        name="Alex", role="owner", is_admin=True, is_owner=True,
        permissions=[], presence="home_verified",
    )
    assert "abrir aplicación windows" in render_help_for_user(owner, channel="pc").casefold()
    assert "abrir aplicación windows" not in render_help_for_user(owner, channel="telegram").casefold()


def test_alias_category_and_approximate_search_are_deterministic():
    owner_context = build_help_access_context(
        channel="pc", authenticated_user="Alex", profile_exists=True,
        is_admin=True, is_owner=True, permissions=(), presence="home_verified",
    )
    first = [entry.name for entry in search_entries("reiniciar bot", context=owner_context)]
    second = [entry.name for entry in search_entries("reiniciar bot", context=owner_context)]
    assert first == second
    assert "reinicia telegram" in first
    assert "consultar el tiempo" in render_help_for_user(user(permissions=["weather"]), topic="Clima")


def test_explanatory_home_request_never_becomes_an_action():
    context = build_help_access_context(
        channel="pc", authenticated_user="Vega", profile_exists=True,
        is_admin=False, permissions={"home.control.light"}, presence="home_verified",
    )
    explanation = handle_command_help_request("¿Cómo enciendo la luz?", context=context)
    imperative = handle_command_help_request("Enciende la luz", context=context)
    assert explanation is not None
    assert "No he ejecutado nada" in explanation
    assert imperative is None


def test_missing_function_and_permission_are_distinguished():
    alias_ejemplo_04_01 = build_help_access_context(
        channel="pc", authenticated_user="Carla", profile_exists=True,
        is_admin=False, permissions={"conversation"},
    )
    denied = handle_command_help_request("buscar comandos crear usuario", context=alias_ejemplo_04_01)
    missing = handle_command_help_request("buscar comandos teletransportar la casa", context=alias_ejemplo_04_01)
    assert "no está disponible para tu identidad" in denied
    assert "no dispone de una función implementada" in missing


def test_catalog_contains_registered_and_service_capabilities_without_duplicates():
    names = [entry.name.casefold() for entry in all_entries()]
    assert len(names) == len(set(names))
    for expected in ("ayuda", "consultar el tiempo", "estado de servicios", "buscar documentos en drive"):
        assert expected in names
    required = {
        "name", "aliases", "category", "description", "examples",
        "capability", "owner_only", "channels", "requires_home_presence",
        "informative", "executes_action", "implementation_status",
    }
    assert all(required == set(record) for record in inventory_records())
