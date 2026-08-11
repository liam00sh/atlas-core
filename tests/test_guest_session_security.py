from core.guest_session import GuestSessionManager

def test_guest_starts_classic_and_isolated():
    manager = GuestSessionManager()
    session = manager.start(
        host_user="Alex",
        guest_name="Zoe",
        assistant_name="Daxter",
    )
    assert session.mode_name == "Clásico"
    assert session.can("conversation")
    assert not session.can("home_assistant")
    assert not session.can("memory_read")
    assert not session.can("reminders")

def test_guest_close():
    manager = GuestSessionManager()
    manager.start(host_user="Alex", guest_name="José", assistant_name="Daxter")
    manager.close()
    assert manager.get() is None

def test_pending_guest():
    manager = GuestSessionManager()
    manager.set_pending_guest("Juan")
    assert manager.get_pending_guest() == "Juan"
