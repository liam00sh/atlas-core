from core.confirmation_manager import ConfirmationManager


def test_action_and_dangerous_confirmation_states_are_distinct():
    manager = ConfirmationManager()
    manager.create_confirmation(
        user="test", action_type="tool", action_name="read", arguments={}
    )
    assert manager.get_confirmation()["confirmation_state"] == "action_confirmation"
    manager.create_confirmation(
        user="test", action_type="tool", action_name="delete", arguments={}, dangerous=True
    )
    assert manager.get_confirmation()["confirmation_state"] == "dangerous_action_confirmation"
