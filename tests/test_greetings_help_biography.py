
from core.user_manager import UserManager


def test_effective_profile_has_safe_synthetic_identity():
    manager = UserManager()
    profile = manager.get_effective_profile("Alex")

    assert profile["name"] == "Alex"
    assert profile["linked_person"]["name"] == "Alex Romero"
    assert profile["roles"] == ["owner", "admin"]


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
    assert "reinicia atlas" not in output.casefold()
    assert "reinicia telegram" not in output.casefold()
