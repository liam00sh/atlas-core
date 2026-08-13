from tools.build_tts_v2_v3_es_es_blind import CANDIDATES, HUMAN_COLUMNS, phrases


def test_comparison_battery_covers_required_terms():
    text = " ".join(phrases()).casefold()
    assert 24 <= len(phrases()) <= 30
    for term in ("acción", "pronunciación", "home assistant", "docker", "github", "google drive", "wi-fi", "¿", "¡"):
        assert term in text


def test_human_schema_is_empty_score_ready():
    assert CANDIDATES == ("v2", "v3", "es_es")
    assert HUMAN_COLUMNS[-2:] == ("preferido_en_grupo", "notas")
