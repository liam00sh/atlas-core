def test_why_weather_used_VillaEjemplo_answers_cause_not_forecast(atlas_core, capsys):
    assert atlas_core.change_user("Vega") is True
    state = atlas_core._daily_state_for("Vega")
    state["last_weather_resolution"] = {
        "location": "VillaEjemplo",
        "source": "ubicación predeterminada de la casa",
    }
    capsys.readouterr()
    atlas_core.process("¿Por qué me das el tiempo de VillaEjemplo?")
    answer = capsys.readouterr().out.casefold()
    assert "estaba usando villaejemplo" in answer
    assert "origen" in answer
    assert "temperatura" not in answer
