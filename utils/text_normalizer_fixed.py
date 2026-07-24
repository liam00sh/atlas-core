"""Utilidades de normalización de texto para Atlas."""

import re
import unicodedata


def normalize_text(text: str, vocabulary=None) -> str:
    """Normaliza texto de forma estable y mantiene compatibilidad histórica.

    ``vocabulary`` es opcional porque varios subsistemas antiguos de Atlas
    todavía lo pasan como segundo argumento.
    """
    value = unicodedata.normalize("NFD", str(text).strip().casefold())
    value = "".join(
        character
        for character in value
        if unicodedata.category(character) != "Mn"
    )
    value = re.sub(r"[^a-z0-9\s]+", " ", value)
    value = " ".join(value.split())

    corrections = {
        "xambia": "cambia",
        "quieb": "quien",
    }
    value = " ".join(
        corrections.get(word, word)
        for word in value.split()
    )

    # Compatibilidad: aceptar vocabulario sin introducir correcciones
    # agresivas que puedan alterar nombres propios o comandos válidos.
    if vocabulary:
        normalized_candidates = {
            normalize_text(candidate)
            for candidate in vocabulary
            if str(candidate).strip()
        }
        if value in normalized_candidates:
            return value

    return value
