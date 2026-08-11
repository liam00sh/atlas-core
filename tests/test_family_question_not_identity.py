import re
import unicodedata


def normalize(text: str) -> str:
    value = unicodedata.normalize("NFD", text.casefold())
    return "".join(c for c in value if unicodedata.category(c) != "Mn")


def is_identity_declaration(text: str) -> bool:
    return re.match(
        r"^(?:(?:si|sí)[, ]+)?soy\s+"
        r"(?!mi\b|mis\b|el\b|la\b|los\b|las\b)"
        r"(?P<name>[a-záéíóúüñ][a-záéíóúüñ '-]{1,60})\s*$",
        text.casefold().strip(),
    ) is not None


def is_family_question(text: str) -> bool:
    normalized = normalize(text).strip(" .,:;!?¡¿")
    patterns = (
        r"^quien(?:es)?\s+son\s+mis?\s+",
        r"^quien(?:es)?\s+es\s+mi\s+",
        r"^dime\s+quien(?:es)?\s+son\s+mis?\s+",
        r"^cuales\s+son\s+mis?\s+",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def test_family_questions_do_not_switch_identity():
    phrases = (
        "Quienes son mis primos",
        "Quien son mis primos",
        "Quién es mi madre",
        "Cuáles son mis tíos",
    )
    for phrase in phrases:
        assert is_family_question(phrase)
        assert not is_identity_declaration(phrase)


def test_valid_identity_declarations_still_work():
    assert is_identity_declaration("Soy Zoe")
    assert is_identity_declaration("Sí, soy Juan")
    assert not is_identity_declaration("Soy mis primos")
