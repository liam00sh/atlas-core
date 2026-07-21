from console.command_help import handle_command_help_request, render_help, search_entries


def test_full_help_has_categories():
    text = render_help()
    assert "GENERAL" in text
    assert "TELEGRAM" in text
    assert "MEMORIA" in text


def test_help_topic():
    text = handle_command_help_request("ayuda telegram")
    assert text is not None
    assert "generar código telegram" in text.casefold()


def test_natural_language_guidance_does_not_execute():
    text = handle_command_help_request("Quiero vincular el Telegram de mi madre")
    assert text is not None
    assert "no he ejecutado nada" in text.casefold()
    assert "código" in text.casefold()


def test_search_and_suggestion():
    assert search_entries("usuario")
    text = handle_command_help_request("crear us")
    assert text is not None
    assert "crear usuario" in text.casefold()
