
from core.user_manager import UserManager


def test_REDACTED_6915771be1c5_effective_profile_uses_structured_biography():
    manager = UserManager()

    profile = manager.get_effective_profile("REDACTED_aebac53c46bb")

    assert profile["linked_person"]["name"] == "REDACTED_ba2c2b03ba9a"
    assert profile["birthday"] == "7 de junio de 1972"
    assert profile["birth_place"] == "REDACTED_a77d7bb7adbf"
    assert profile["residence"] == "REDACTED_a77d7bb7adbf"
    assert profile["location"] == "REDACTED_a77d7bb7adbf"


def test_effective_profile_does_not_mutate_operational_profile():
    manager = UserManager()

    assert "birthday" not in manager.get_profile("REDACTED_aebac53c46bb")
    assert "residence" not in manager.get_profile("REDACTED_aebac53c46bb")

    manager.get_effective_profile("REDACTED_aebac53c46bb")

    assert "birthday" not in manager.get_profile("REDACTED_aebac53c46bb")
    assert "residence" not in manager.get_profile("REDACTED_aebac53c46bb")


def test_REDACTED_f73137d930c3_and_REDACTED_7b9528898599_read_linked_person_data():
    manager = UserManager()

    REDACTED_f73137d930c3 = manager.get_effective_profile("REDACTED_2c7b6821719d")
    REDACTED_7b9528898599 = manager.get_effective_profile("REDACTED_bc04a68d9192")

    assert REDACTED_f73137d930c3["birthday"] == "25 de noviembre de 2000"
    assert REDACTED_f73137d930c3["location"] == "REDACTED_a77d7bb7adbf"
    assert REDACTED_7b9528898599["birthday"] == "18 de noviembre de 2003"
    assert REDACTED_7b9528898599["location"] == "REDACTED_4cde1bf18b9c"


def test_unlinked_profile_remains_safe():
    manager = UserManager()
    manager.register_profile("Invitado")

    profile = manager.get_effective_profile("Invitado")

    assert profile["name"] == "Invitado"
    assert profile["linked_person"] is None
