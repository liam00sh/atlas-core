from console.command_help import render_help, render_help_for_user


def test_home_assistant_functions_are_in_help():
    text = render_help("Hogar y Home Assistant")
    assert "programar luz del acuario" in text
    assert "temporizador de luz del acuario" in text
    assert "activar horario del acuario" in text


def test_non_owner_help_hides_owner_only_entries():
    text = render_help_for_user({"role": "friend"})
    assert "confirmar código de Telegram" not in text
    assert "copia de seguridad" not in text


def test_owner_help_includes_owner_entries():
    text = render_help_for_user({"role": "owner"})
    assert "confirmar código de Telegram" in text
    assert "copia de seguridad" in text


def test_explicit_category_permissions_filter_help():
    text = render_help_for_user(
        {
            "role": "friend",
            "help_categories": {"General", "Hogar y Home Assistant"},
            "permissions": {"conversation", "home.control.light", "home.control.switch"},
            "presence": "home_verified",
        }
    )
    assert "HOGAR Y HOME ASSISTANT" in text
    assert "TELEGRAM" not in text
