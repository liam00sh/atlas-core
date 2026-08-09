from tools.prepare_chatterbox_dataset import assign_splits, canonical_text, classify, text_groups


def _row(sample_id, text):
    return {"sample_id": sample_id, "text": text, "normalized_text": text}


def test_similar_text_groups_near_duplicates_together():
    rows = [_row("a", "¡Buen disparo, Jak!"), _row("b", "Buen disparo Jak"), _row("c", "Otra frase distinta")]
    groups = text_groups(rows)
    assert groups["a"] == groups["b"]
    assert groups["a"] != groups["c"]
    splits = assign_splits(rows, groups, 20260809)
    assert splits["a"] == splits["b"]


def test_classification_is_explicit_and_conservative():
    good = {"tts_usable": "True", "quality": "buena", "duration_seconds": "2.0"}
    audit = {"severity": "INFO", "readable": "True", "metadata_sha256_match": "True", "duration_seconds": "2.0", "issues": ""}
    assert classify(good, audit)[0] == "included"
    acceptable = dict(good, quality="aceptable")
    assert classify(acceptable, audit) == ("review", ["quality_aceptable"])
    limited = dict(good, quality="limite")
    assert classify(limited, audit) == ("excluded", ["quality_limite"])


def test_canonical_text_preserves_words_not_punctuation_or_accents():
    assert canonical_text("¡Átlas, está listo!") == "atlas esta listo"
