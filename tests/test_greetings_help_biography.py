
from core.user_manager import UserManager


def test_effective_profile_has_REDACTED_f73137d930c3_biography():
    manager = UserManager()
    profile = manager.get_effective_profile("REDACTED_2c7b6821719d")

    assert profile["birthday"] == "25 de noviembre de 2000"
    assert profile["birth_place"] == "REDACTED_a77d7bb7adbf"
    assert profile["location"] == "REDACTED_a77d7bb7adbf"
    assert "REDACTED_4cde1bf18b9c" in profile["previous_residences"]


def test_special_greetings_are_not_generic_fast_greetings():
    from telegram_interface.core_adapter import AtlasCoreAdapter

    adapter = AtlasCoreAdapter.__new__(AtlasCoreAdapter)
    assert "buenos dias" not in {"hola", "buenas", "buenas tardes", "hey", "ey", "holi"}
    assert "buenas noches" not in {"hola", "buenas", "buenas tardes", "hey", "ey", "holi"}


def test_help_without_context_hides_owner_commands():
    from console.command_help import handle_command_help_request

    output = handle_command_help_request("ayuda")

    assert "crear perfil de usuario" not in output.casefold()
    assert "estado de atlas" not in output.casefold()
    assert "estado de telegram" not in output.casefold()
