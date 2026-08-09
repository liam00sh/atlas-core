from voice.prosody import segment_text
from voice.text_normalizer import normalize_for_tts


def test_visual_and_spoken_text_are_separate_for_vocatives() -> None:
    visual = "REDACTED_0f38c2ded26fnando y atento, REDACTED_2c7b6821719d. ¿Cómo estás tú?"
    assert normalize_for_tts(visual) == "REDACTED_0f38c2ded26fnando y atento REDACTED_2c7b6821719d. ¿Cómo estás tú?"
    assert visual == "REDACTED_0f38c2ded26fnando y atento, REDACTED_2c7b6821719d. ¿Cómo estás tú?"


def test_tts_normalizer_removes_markdown_emojis_and_raw_urls() -> None:
    spoken = normalize_for_tts(
        "**Listo** 😄: consulta [la guía](https://example.com/a) o https://example.com/b."
    )
    assert "**" not in spoken
    assert "😄" not in spoken
    assert "https://" not in spoken
    assert "la guía" in spoken
    assert "enlace web" in spoken


def test_tts_normalizer_preserves_numbers_hours_and_abbreviations() -> None:
    spoken = normalize_for_tts("A las 18:30, el Sr. Pérez tiene un 75% completado.")
    assert "18:30" in spoken
    assert "Sr. Pérez" in spoken
    assert "75 por ciento" in spoken


def test_tts_normalizer_softens_parentheses_and_dashes() -> None:
    spoken = normalize_for_tts("Atlas (local) — estable - y atento.")
    assert "(" not in spoken and ")" not in spoken
    assert "—" not in spoken
    assert "local" in spoken


def test_prosody_encodes_commas_colons_without_sending_symbols_to_engine() -> None:
    segments = segment_text("Hola, REDACTED_2c7b6821719d: todo listo.")
    assert segments
    assert all("," not in segment.text and ":" not in segment.text for segment in segments)
    assert any(segment.pause_after_ms > 0 for segment in segments[:-1])
