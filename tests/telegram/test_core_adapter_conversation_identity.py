"""Regresiones de identidad conversacional y consultas meta de Telegram."""

from telegram_interface.core_adapter import AtlasCoreAdapter


def test_identity_parser_stops_at_comma_and_question():
    assert AtlasCoreAdapter._parse_identity_declaration(
        "Soy Noa, qué sabes de mí"
    ) == ("Noa", "qué sabes de mí")


def test_identity_parser_accepts_full_name():
    assert AtlasCoreAdapter._parse_identity_declaration(
        "Soy Noa Melinte Carreres, dónde vivo"
    ) == ("Noa Melinte Carreres", "dónde vivo")


def test_safe_typing_correction_handles_com_and_ppsible():
    corrected = AtlasCoreAdapter._correct_typing(
        "Com quien vive Raúl y es ppsible avisarle"
    )
    assert corrected.startswith("con quien")
    assert "posible" in corrected


def test_visibility_labels_are_hidden_from_telegram():
    clean = AtlasCoreAdapter._clean_response(
        "1. dato [Personas de confianza]\n2. otro [Cualquier persona]"
    )
    assert "[" not in clean
    assert "dato" in clean
    assert "otro" in clean
