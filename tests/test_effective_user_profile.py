
from core.user_manager import UserManager


def test_effective_profile_uses_structured_synthetic_identity():
    manager = UserManager()

    profile = manager.get_effective_profile("Alex")

    assert profile["linked_person"]["name"] == "Alex Romero"
    assert profile["biography_summary"] == "Usuario principal completamente ficticio."
    assert "birthday" not in profile


def test_effective_profile_does_not_mutate_operational_profile():
    manager = UserManager()

    assert "biography_summary" not in manager.get_profile("Alex")

    manager.get_effective_profile("Alex")

    assert "biography_summary" not in manager.get_profile("Alex")


def test_Alex_and_Vega_read_linked_synthetic_people():
    manager = UserManager()

    Alex = manager.get_effective_profile("Alex")
    alias_ejemplo_44_01 = manager.get_effective_profile("Vega")

    assert Alex["linked_person"]["name"] == "Alex Romero"
    assert alias_ejemplo_44_01["linked_person"]["name"] == "Vega Ferrer"


def test_unlinked_profile_remains_safe():
    manager = UserManager()
    manager.register_profile("Invitado")

    profile = manager.get_effective_profile("Invitado")

    assert profile["name"] == "Invitado"
    assert profile["linked_person"] is None
