def test_temporary_location_and_habitual_home_remain_separate(atlas_core, capsys):
    assert atlas_core.change_user("Vega") is True
    capsys.readouterr()

    atlas_core.process("He venido a casa de Alex unos días.")
    first = capsys.readouterr().out.casefold()
    assert "temporalmente" in first
    assert "casa de alex" in first

    atlas_core.process("¿Dónde estoy ahora?")
    current = capsys.readouterr().out.casefold()
    assert "casa de alex" in current
    assert "domicilio" in current

    atlas_core.process("¿Dónde vivo?")
    home = capsys.readouterr().out.casefold()
    assert "provincia ejemplo" in home
    assert "habitual" in home
    assert "casa de Alex" not in home

    state = atlas_core.conversation_manager.current()
    assert state.authenticated_identity == "Vega"
    assert state.home_presence != "home_verified"
