from core.internet_lookup import build_comparison_context, is_comparison_query, InternetSource
from memory.memory_service import MemoryService
from telegram_interface.progress import progress_delay_for


def test_social_messages_do_not_show_progress():
    assert progress_delay_for("Hola") < 0
    assert progress_delay_for("¿Cómo estás?") < 0
    assert progress_delay_for("¡Gracias!") < 0


def test_nontrivial_message_uses_four_seconds():
    assert progress_delay_for("Explícame cómo exportar a PDF desde Excel") == 4.0


def test_profile_essentials_are_detected():
    assert MemoryService._essential_category("Mi fecha de nacimiento es 1 de enero") == "birth"
    assert MemoryService._essential_category("Trabajo como administrador") == "work"
    assert MemoryService._essential_category("Vivo en Beneixama") == "residence"
    assert MemoryService._essential_category("Tengo un gato llamado Funcio") == "pets"


def test_comparison_query_and_context():
    assert is_comparison_query("Compara dos móviles")
    text = build_comparison_context("Compara A y B", [InternetSource("Fuente", "https://example.com", "Dato")])
    assert "No declares un ganador" in text
