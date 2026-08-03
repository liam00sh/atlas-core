from voice.prosody import segment_text


def test_comma_adds_short_pause() -> None:
    segments = segment_text("Hola, REDACTED_2c7b6821719d.")

    assert len(segments) == 2
    assert segments[0].text == "Hola,"
    assert segments[0].pause_after_ms == 150
    assert segments[1].text == "REDACTED_2c7b6821719d."
    assert segments[1].pause_after_ms == 0


def test_paragraph_adds_longer_pause() -> None:
    segments = segment_text(
        "Primera frase.\n\nSegunda frase."
    )

    assert len(segments) == 2
    assert segments[0].text == "Primera frase."
    assert segments[0].pause_after_ms == 760
    assert segments[1].text == "Segunda frase."
    assert segments[1].pause_after_ms == 0


def test_decimal_is_not_split() -> None:
    segments = segment_text("Hay 3.5 litros.")

    assert len(segments) == 1
    assert segments[0].text == "Hay 3.5 litros."


def test_ip_is_not_split() -> None:
    segments = segment_text("La IP es 192.168.1.20.")

    assert len(segments) == 1
    assert segments[0].text == "La IP es 192.168.1.20."


def test_abbreviation_is_not_split() -> None:
    segments = segment_text("El Sr. García ha llegado.")

    assert len(segments) == 1
    assert segments[0].text == "El Sr. García ha llegado."


def test_semicolon_adds_medium_pause() -> None:
    segments = segment_text(
        "Primero revisamos esto; después continuamos."
    )

    assert len(segments) == 2
    assert segments[0].pause_after_ms == 280


def test_ellipsis_adds_long_pause() -> None:
    segments = segment_text(
        "Bueno... vamos a intentarlo."
    )

    assert len(segments) == 2
    assert segments[0].text == "Bueno..."
    assert segments[0].pause_after_ms == 600
