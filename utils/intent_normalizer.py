"""Normalización conservadora para errores humanos de escritura.

Conserva el texto original y solo corrige palabras funcionales cuando la
confianza es alta. Los nombres propios, códigos y términos desconocidos no se
modifican automáticamente.
"""
from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import unicodedata


@dataclass(frozen=True, slots=True)
class Interpretation:
    original: str
    interpreted: str
    corrections: tuple[tuple[str, str, float], ...]


FUNCTION_WORDS = {
    "a", "al", "algo", "anade", "añade", "archiva", "avisa", "avisame",
    "avísame", "busca", "cambia", "cancela", "como", "cómo", "con", "corrige",
    "cuando", "cuándo", "cuanto", "cuánto", "cuantos", "cuántos", "de", "del",
    "dile", "dime", "donde", "dónde", "el", "ella", "en", "es", "esta", "está",
    "estas", "estás", "esto", "haz", "hoy", "la", "las", "le", "lo", "los",
    "manana", "mañana", "me", "mi", "mis", "no", "olvida", "para", "por",
    "pregunta", "puede", "puedes", "que", "qué", "quien", "quién", "quienes",
    "recuerda", "recuerdame", "recuérdame", "recupera", "responde", "responder",
    "si", "sí", "sobre", "te", "tengo", "tiene", "todo", "un", "una", "vive",
    "viven", "y", "yo",
}

COMMON = {
    "com": "con",
    "qe": "que",
    "q": "que",
    "k": "que",
    "dnde": "donde",
    "dnd": "donde",
    "kien": "quien",
    "kienes": "quienes",
    "recuerdame": "recuérdame",
    "avisame": "avísame",
    "manana": "mañana",
    "ppsible": "posible",
    "posble": "posible",
    "tngo": "tengo",
    "tienees": "tienes",
}

TOKEN_RE = re.compile(r"\w+|[^\w\s]+|\s+", re.UNICODE)


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold())
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _score(left: str, right: str) -> float:
    return SequenceMatcher(None, _fold(left), _fold(right)).ratio()


def interpret_text(text: str) -> Interpretation:
    tokens = TOKEN_RE.findall(text)
    corrections: list[tuple[str, str, float]] = []
    word_positions = [i for i, token in enumerate(tokens) if token.isalpha()]

    for index in word_positions:
        token = tokens[index]
        folded = _fold(token)
        # Los nombres propios no se tocan, salvo la primera palabra cuando hay
        # un error común inequívoco como "Com quien...".
        is_capitalized = token[:1].isupper()
        first_word = index == word_positions[0]
        replacement = COMMON.get(folded)

        # Corrección contextual de "pam" -> "pan" solo alrededor de comprar.
        if folded == "pam":
            nearby = " ".join(_fold(tokens[pos]) for pos in word_positions if abs(pos - index) <= 4)
            if any(item in nearby for item in ("compr", "anade", "lista")):
                replacement = "pan"

        if replacement is None and (not is_capitalized or first_word):
            candidates = sorted(
                ((candidate, _score(folded, candidate)) for candidate in FUNCTION_WORDS),
                key=lambda item: item[1],
                reverse=True,
            )
            if candidates and candidates[0][1] >= 0.90:
                replacement = candidates[0][0]

        if replacement and _fold(replacement) != folded:
            if token[:1].isupper():
                replacement = replacement[:1].upper() + replacement[1:]
            confidence = max(_score(token, replacement), 0.95 if folded in COMMON else 0.0)
            tokens[index] = replacement
            corrections.append((token, replacement, confidence))

    return Interpretation(text, "".join(tokens), tuple(corrections))
