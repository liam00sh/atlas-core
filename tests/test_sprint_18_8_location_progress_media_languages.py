from telegram_interface.core_adapter import AtlasCoreAdapter
from telegram_interface.models import TelegramMessage
from telegram_interface.progress import append_response_time, classify_operation, progress_delay_for
from core.internet_lookup import _extract_entity_query, _source_is_relevant, InternetSource


def test_location_entity_extraction_and_typing_protection():
    assert _extract_entity_query("En qué comunidad está VillaEjemplo?") == "VillaEjemplo"
    assert _extract_entity_query("En qué comunidad está VillaEjemplo?") == "VillaEjemplo"
    corrected = AtlasCoreAdapter._correct_typing("En que comunidad está VillaEjemplo")
    assert "está" in corrected
    assert "estás" not in corrected


def test_irrelevant_location_source_is_rejected():
    wrong = InternetSource("Otra ciudad", "https://example.test/otra", "Otra ciudad está en otra provincia")
    right = InternetSource("VillaEjemplo", "https://example.test/VillaEjemplo", "VillaEjemplo está en Provincia Ejemplo")
    assert not _source_is_relevant(wrong, "VillaEjemplo")
    assert _source_is_relevant(right, "VillaEjemplo")


def test_progress_requires_real_latency_and_has_elapsed_footer():
    assert classify_operation("Busca en Internet la población de VillaEjemplo") == "internet"
    assert progress_delay_for("Busca en Internet la población de VillaEjemplo") >= 4.5
    assert "4,2 s" in append_response_time("Respuesta", 4.2, "Daxter")


def test_telegram_message_accepts_photo_without_text():
    message = TelegramMessage.from_update({
        "update_id": 1,
        "message": {
            "message_id": 2,
            "date": 0,
            "from": {"id": 3, "first_name": "Alex"},
            "chat": {"id": 3, "type": "private"},
            "photo": [
                {"file_id": "small", "file_size": 10},
                {"file_id": "large", "file_size": 100},
            ],
        },
    })
    assert message is not None
    assert message.media_type == "photo"
    assert message.file_id == "large"
    assert message.text == ""
