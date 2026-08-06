from assistant_identity.mode import CLASSIC_MODE, WORK_MODE
from core.atlas_commands import AtlasCommandsMixin
from core.guest_session import GuestSessionManager


class _Identity:
    def __init__(self):
        self.mode = CLASSIC_MODE

    def get_active_mode_name(self):
        return self.mode

    def get_active_mode_label(self):
        return self.mode

    def set_mode(self, *, mode_name, **_kwargs):
        self.mode = mode_name
        return True


class _Commands(AtlasCommandsMixin):
    def __init__(self):
        self.identity_manager = _Identity()
        self.guest_sessions = GuestSessionManager()


def test_guest_mode_is_temporary_and_does_not_mutate_owner(capsys):
    atlas = _Commands()
    guest = atlas.guest_sessions.start(
        host_user="Nora", guest_name="Invitado", assistant_name="Daxter"
    )
    assert atlas._change_assistant_mode(WORK_MODE, "modo trabajo")
    assert guest.mode_name == WORK_MODE
    assert atlas.identity_manager.mode == CLASSIC_MODE
    atlas._show_active_assistant_mode()
    assert "Trabajo" in capsys.readouterr().out


def test_registered_user_mode_still_uses_persistent_manager():
    atlas = _Commands()
    assert atlas._change_assistant_mode(WORK_MODE, "modo trabajo")
    assert atlas.identity_manager.mode == WORK_MODE
