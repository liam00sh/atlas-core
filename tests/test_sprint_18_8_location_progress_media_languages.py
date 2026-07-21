from telegram_interface.core_adapter import AtlasCoreAdapter
from telegram_interface.models import TelegramMessage
from telegram_interface.progress import append_response_time, classify_operation, progress_delay_for
from core.internet_lookup import _extract_entity_query, _source_is_relevant, InternetSource


def test_location_entity_extraction_and_typing_protection():
    assert _extract_entity_query("En qué comunidad está REDACTED_039ed2c608a5?") == "REDACTED_039ed2c608a5"
    assert _extract_entity_query("En qué comunidad está REDACTED_a77d7bb7adbf?") == "REDACTED_a77d7bb7adbf"
    corrected = AtlasCoreAdapter._correct_typing("En que comunidad está REDACTED_039ed2c608a5")
    assert "está" in corrected
    assert "estás" not in corrected


def test_irrelevant_location_source_is_rejected():
    wrong = InternetSource("REDACTED_039ed2c608a5", "https://example.test/REDACTED_32919f6b2abb", "REDACTED_039ed2c608a5 está en REDACTED_49a799c6beb3")
    right = InternetSource("REDACTED_a77d7bb7adbf", "https://example.test/REDACTED_fddd19092a14", "REDACTED_a77d7bb7adbf está en REDACTED_4cde1bf18b9c")
    assert not _source_is_relevant(wrong, "REDACTED_a77d7bb7adbf")
    assert _source_is_relevant(right, "REDACTED_a77d7bb7adbf")


def test_progress_is_early_for_known_slow_work_and_has_elapsed_footer():
    assert classify_operation("Busca en Internet la población de REDACTED_a77d7bb7adbf") == "internet"
    assert progress_delay_for("Busca en Internet la población de REDACTED_a77d7bb7adbf") < 2.0
    assert "4,2 s" in append_response_time("Respuesta", 4.2, "Daxter")


def test_telegram_message_accepts_photo_without_text():
    message = TelegramMessage.from_update({
        "update_id": 1,
        "message": {
            "message_id": 2,
            "date": 0,
            "from": {"id": 3, "first_name": "REDACTED_2c7b6821719d"},
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
