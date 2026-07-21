from core.internet_lookup import _extract_entity_query
from telegram_interface.progress import build_progress_message, classify_progress


def test_population_query_extracts_exact_place_name():
    assert _extract_entity_query("Cuántos habitantes tiene Beneixama") == "Beneixama"
    assert _extract_entity_query("población actual de Campo de Mirra") == "Campo de Mirra"


def test_progress_classification():
    assert classify_progress("Busca en Internet cuántos habitantes tiene Beneixama") == "internet"
    assert classify_progress("Actualiza el índice de Drive") == "drive_index"
    assert classify_progress("Traduce buenos días al alemán") == "translation"


def test_progress_messages_are_personality_aware():
    daxter = build_progress_message("Busca en Internet Beneixama", "Daxter")
    coco = build_progress_message("Busca en Internet Beneixama", "Coco")
    assert daxter
    assert coco
    assert daxter != coco
