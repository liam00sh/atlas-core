def test_temporary_location_does_not_grant_home_assistant_permission(atlas_core, capsys):
    assert atlas_core.change_user("Vega") is True
    capsys.readouterr()
    atlas_core.process("Estoy en casa de Alex unos días.")
    capsys.readouterr()
    atlas_core.process("Apaga la luz del acuario pequeño.")
    answer = capsys.readouterr().out.casefold()
    assert "no puedo realizar" in answer
    assert "presencia" in answer or "permiso" in answer
    assert "he apagado" not in answer
    decision = atlas_core.conversation_manager.current().recent_actions[-1]
    assert decision["executed"] is False
    assert decision["authorized"] is False


def test_action_wording_never_counts_as_execution_without_confirmation():
    from automation.home_intent_service import HomeIntentResponse
    from core.atlas import Atlas

    unconfirmed = Atlas._home_decision(
        HomeIntentResponse(handled=True, message="He apagado la luz.")
    )
    confirmed = Atlas._home_decision(
        HomeIntentResponse(
            handled=True,
            message="He apagado la luz.",
            authorized=True,
            execution_confirmed=True,
        )
    )

    assert unconfirmed.executed is False
    assert confirmed.executed is True
