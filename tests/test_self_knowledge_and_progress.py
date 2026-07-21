from telegram_interface.progress import progress_delay_for


def test_simple_greeting_has_no_progress():
    assert progress_delay_for("Hola") < 0
    assert progress_delay_for("¿Cómo estás?") < 0


def test_slow_operations_wait_four_seconds():
    assert progress_delay_for("Busca en Internet la población de Alicante") == 4.0
    assert progress_delay_for("Traduce este texto") == 4.0
    assert progress_delay_for("Explícame una cosa compleja") == 4.0
