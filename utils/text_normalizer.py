"""Utilidades de normalización y aproximación de texto para Atlas."""

from __future__ import annotations

from difflib import SequenceMatcher
import re
import unicodedata
from collections.abc import Iterable


def normalize_text(text: str, vocabulary: Iterable[str] | None = None) -> str:
    """Normaliza texto y mantiene compatibilidad con llamadas históricas."""
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

    if vocabulary:
        normalized_candidates = {
            normalize_text(candidate)
            for candidate in vocabulary
            if str(candidate).strip()
        }
        if value in normalized_candidates:
            return value

    return value


def find_closest_phrase(
    text: str,
    phrases: Iterable[str] | None = None,
    *,
    candidates: Iterable[str] | None = None,
    threshold: float = 0.78,
    cutoff: float | None = None,
) -> str | None:
    """Devuelve la frase más próxima cuando supera el umbral indicado.

    Acepta ``phrases``/``candidates`` y ``threshold``/``cutoff`` para conservar
    compatibilidad con las distintas llamadas existentes en Atlas.
    """
    available = candidates if candidates is not None else phrases
    if not available:
        return None

    effective_threshold = threshold if cutoff is None else cutoff

    normalized_text = normalize_text(text)
    if not normalized_text:
        return None

    best_phrase: str | None = None
    best_score = 0.0

    for phrase in available:
        normalized_phrase = normalize_text(phrase)
        if not normalized_phrase:
            continue

        if normalized_text == normalized_phrase:
            return str(phrase)

        score = SequenceMatcher(
            None,
            normalized_text,
            normalized_phrase,
        ).ratio()

        if score > best_score:
            best_score = score
            best_phrase = str(phrase)

    if best_phrase is not None and best_score >= effective_threshold:
        return best_phrase

    return None
