"""Convierte la respuesta visual en texto natural y seguro para TTS."""

from __future__ import annotations

import re
import unicodedata


_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\((?:https?://|www\.)[^)]+\)", re.IGNORECASE)
_URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_VOCATIVE_COMMA = re.compile(
    r",\s+([A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ'-]{1,40})(?=\s*[.!?]|$)"
)


def normalize_for_tts(text: str) -> str:
    """Elimina marcas visuales sin destruir la prosodia de las frases."""

    value = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"```(?:\w+)?\s*([\s\S]*?)```", r" \1 ", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    value = _MARKDOWN_LINK.sub(r"\1", value)
    value = _URL.sub(" enlace web ", value)
    value = re.sub(r"(?m)^\s{0,3}(?:#{1,6}|>|[-*+]\s+)\s*", "", value)
    value = re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__", lambda m: m.group(1) or m.group(2), value)
    value = value.replace("&", " y ")
    value = re.sub(r"(?<=\d)\s*%", " por ciento", value)
    value = re.sub(r"[()\[\]{}<>|*_~]", " ", value)
    value = re.sub(r"\s+[—–-]\s+", ", ", value)
    value = "".join(
        character
        for character in value
        if unicodedata.category(character) not in {"So", "Sk", "Cc"}
        or character in {"\n", "\t"}
    )
    # La coma vocativa es correcta al escribir, pero esta voz introduce una
    # pausa artificial antes del nombre. Solo se retira en la copia hablada.
    value = _VOCATIVE_COMMA.sub(r" \1", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = re.sub(r"([,;:]){2,}", r"\1", value)
    value = re.sub(r"\n\s*\n+", "\n\n", value)
    return value.strip()


__all__ = ["normalize_for_tts"]
