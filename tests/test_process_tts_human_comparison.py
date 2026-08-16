from tools.process_tts_human_comparison import classify_note, phrase_category


def test_phrase_categories_cover_the_directed_benchmark():
    assert phrase_category("TTS001_A") == "tildes_espanol"
    assert phrase_category("TTS014_C") == "nombres"
    assert phrase_category("TTS020_B") == "terminos_ingleses"
    assert phrase_category("TTS023_A") == "numeros_fechas"
    assert phrase_category("TTS026_C") == "frases_largas"
    assert phrase_category("TTS028_B") == "interrogaciones_exclamaciones"


def test_human_notes_are_classified_without_rewriting_them():
    note = "acción; Home. Se corta al inicio y al final se escuchan artefactos; queda poco natural"
    assert classify_note(note) == [
        "acentos_tildes", "terminos_ingleses", "corte_inicial", "artefactos", "ritmo_extrano",
    ]
