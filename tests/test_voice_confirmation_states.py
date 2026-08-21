from core.confirmation_manager import ConfirmationManager
from core.atlas_tools import AtlasToolsMixin
from commands import restart_telegram


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


def test_telegram_restart_creates_real_pending_confirmation_and_cancel_clears_it(monkeypatch):
    class Atlas(AtlasToolsMixin):
        def __init__(self):
            self.confirmations = ConfirmationManager()

        def get_user(self):
            return "Liam"

    atlas = Atlas()
    monkeypatch.setattr(restart_telegram.context, "atlas", atlas)
    monkeypatch.setattr(restart_telegram, "require_admin_user", lambda: True)

    assert restart_telegram.execute() is True
    pending = atlas.confirmations.get_confirmation()
    assert pending is not None
    assert pending["action_type"] == "telegram_restart"
    assert pending["confirmation_state"] == "dangerous_action_confirmation"

    assert atlas._handle_pending_confirmation("cancelar") is True
    assert atlas.confirmations.has_pending_confirmation() is False
