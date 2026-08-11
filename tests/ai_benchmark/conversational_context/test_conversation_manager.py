from conversation.manager import ConversationManager


def test_temporary_location_does_not_change_identity_home_or_presence():
    manager = ConversationManager()
    state = manager.begin_turn(
        channel="telegram",
        session_id="chat-1",
        authenticated_identity="Vega",
        conversational_identity="Vega",
    )
    manager.set_habitual_residence("Provincia Ejemplo", verified=True)
    manager.observe_user_message("He venido a casa de Alex unos días.")

    assert state.authenticated_identity == "Vega"
    assert state.conversational_identity == "Vega"
    assert state.habitual_residence == "Provincia Ejemplo"
    assert state.temporary_location == "casa de alex"
    assert state.home_presence == "unknown"


def test_state_is_scoped_by_channel_session_and_authenticated_user():
    manager = ConversationManager()
    first = manager.begin_turn(channel="telegram", session_id="1", authenticated_identity="Vega")
    manager.observe_user_message("Estoy en casa de Alex unos días")
    second = manager.begin_turn(channel="cli", session_id="local", authenticated_identity="Alex")
    assert first.temporary_location == "casa de alex"
    assert second.temporary_location is None
