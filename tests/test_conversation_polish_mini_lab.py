from tools.generate_conversation_polish_mini_lab import samples


def test_mini_lab_is_small_and_has_no_pseudophonetic_spellings():
    rows = samples()
    assert len(rows) == 24
    assert {row["category"] for row in rows} == {
        "spanish_es", "english_terms", "long_responses", "conversation"
    }
    combined = " ".join(row["text"] for row in rows)
    assert "Dóquer" not in combined
    assert "Assístan" not in combined
