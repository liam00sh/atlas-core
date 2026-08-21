"""Segmentación lingüística conservadora para TTS continuo."""

from __future__ import annotations

import re

DEFAULT_MAX_SPEECH_CHARS = 120


def split_for_speech(
    text: str, *, max_chars: int = DEFAULT_MAX_SPEECH_CHARS
) -> tuple[str, ...]:
    value = " ".join(str(text).split()).strip()
    if not value:
        return ()
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", value) if part.strip()]
    segments: list[str] = []
    current = ""
    for sentence in sentences:
        if len(sentence) > max_chars:
            pieces = [part.strip() for part in re.split(r"(?<=[,;:])\s+", sentence) if part.strip()]
        else:
            pieces = [sentence]
        for piece in pieces:
            candidate = f"{current} {piece}".strip()
            if current and len(candidate) > max_chars:
                segments.append(current)
                current = piece
            else:
                current = candidate
    if current:
        segments.append(current)
    return tuple(segments)
