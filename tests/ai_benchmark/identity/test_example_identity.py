def test_Vega_who_am_i_uses_authenticated_profile(atlas_core, capsys):
    assert atlas_core.change_user("Vega") is True
    capsys.readouterr()
    assert atlas_core.process("¿Quién soy?") is True
    answer = capsys.readouterr().out
    assert "Vega" in answer
    assert atlas_core.get_user() == "Vega"

