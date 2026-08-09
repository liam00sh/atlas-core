def test_why_weather_used_REDACTED_fddd19092a14_answers_cause_not_forecast(atlas_core, capsys):
    assert atlas_core.change_user("REDACTED_bc04a68d9192") is True
    state = atlas_core._daily_state_for("REDACTED_bc04a68d9192")
    state["last_weather_resolution"] = {
        "location": "REDACTED_a77d7bb7adbf",
        "source": "ubicación predeterminada de la casa",
    }
    capsys.readouterr()
    atlas_core.process("¿Por qué me das el tiempo de REDACTED_a77d7bb7adbf?")
    answer = capsys.readouterr().out.casefold()
    assert "estaba usando REDACTED_fddd19092a14" in answer
    assert "origen" in answer
    assert "temperatura" not in answer

