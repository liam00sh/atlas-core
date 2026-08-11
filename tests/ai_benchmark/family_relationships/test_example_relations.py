def test_Vega_partner_is_resolved_without_identity_change(atlas_core, capsys):
    assert atlas_core.change_user("Vega") is True
    capsys.readouterr()
    assert atlas_core.process("¿Qué relación tengo con Alex?") is True
    answer = capsys.readouterr().out.casefold()
    assert "pareja" in answer
    assert "primo" not in answer
    assert atlas_core.get_user() == "Vega"


def test_verified_data_never_turns_Alex_into_REDACTED_d296a64095dds_cousin(atlas_core, capsys):
    assert atlas_core.change_user("Vega") is True
    capsys.readouterr()
    atlas_core.process("¿Qué relación tengo con Alex?")
    answer = capsys.readouterr().out.casefold()
    assert "pareja" in answer
    assert "primo" not in answer
