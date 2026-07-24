from console.command_help import render_help, render_help_for_user

def test_smoke_help_home_assistant():
    text = render_help("Hogar y Home Assistant")
    assert "programar luz del acuario" in text
    assert "temporizador de luz del acuario" in text

def test_smoke_help_permissions():
    friend = render_help_for_user({"role": "friend"})
    owner = render_help_for_user({"role": "owner"})
    assert "copia de seguridad" not in friend
    assert "copia de seguridad" in owner
