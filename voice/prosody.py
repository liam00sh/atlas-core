"""Segmentación de texto y pausas naturales para síntesis de voz."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re


class PauseKind(StrEnum):
    """Tipos de pausa admitidos por la capa de prosodia."""

    COMMA = "comma"
    SEMICOLON = "semicolon"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    ELLIPSIS = "ellipsis"


PAUSE_DURATIONS_MS: dict[PauseKind, int] = {
    PauseKind.COMMA: 150,
    PauseKind.SEMICOLON: 280,
    PauseKind.SENTENCE: 420,
    PauseKind.PARAGRAPH: 760,
    PauseKind.ELLIPSIS: 600,
}


@dataclass(frozen=True, slots=True)
class SpeechSegment:
    """Fragmento de texto y pausa posterior."""

    text: str
    pause_after_ms: int


_ABBREVIATIONS = {
    "sr.",
    "sra.",
    "srta.",
    "dr.",
    "dra.",
    "ud.",
    "uds.",
    "etc.",
    "p. ej.",
}


def _is_abbreviation(text: str, index: int) -> bool:
    start = max(0, index - 12)
    candidate = text[start : index + 1].strip().casefold()
    return any(
        candidate.endswith(abbreviation)
        for abbreviation in _ABBREVIATIONS
    )


def _is_decimal_or_ip(text: str, index: int) -> bool:
    previous_char = text[index - 1] if index > 0 else ""
    next_char = text[index + 1] if index + 1 < len(text) else ""

    return (
        previous_char.isdigit()
        and next_char.isdigit()
    )


def normalize_paragraphs(text: str) -> str:
    """Normaliza espacios sin destruir los saltos de párrafo."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs: list[str] = []

    for paragraph in re.split(r"\n\s*\n+", normalized):
        clean = re.sub(r"[ \t]+", " ", paragraph).strip()
        if clean:
            paragraphs.append(clean)

    return "\n\n".join(paragraphs)


def segment_text(text: str) -> list[SpeechSegment]:
    """Divide el texto conservando pausas y evitando cortes incorrectos."""

    normalized = normalize_paragraphs(text)
    if not normalized:
        return []

    segments: list[SpeechSegment] = []
    buffer: list[str] = []
    index = 0

    def flush(pause_after_ms: int) -> None:
        nonlocal buffer

        current = "".join(buffer).strip()
        if current:
            segments.append(
                SpeechSegment(
                    text=current,
                    pause_after_ms=pause_after_ms,
                )
            )

        buffer = []

    while index < len(normalized):
        if normalized.startswith("\n\n", index):
            if buffer:
                flush(
                    PAUSE_DURATIONS_MS[
                        PauseKind.PARAGRAPH
                    ]
                )
            elif segments:
                previous = segments[-1]
                segments[-1] = SpeechSegment(
                    text=previous.text,
                    pause_after_ms=PAUSE_DURATIONS_MS[
                        PauseKind.PARAGRAPH
                    ],
                )

            index += 2
            continue

        if normalized.startswith("...", index):
            buffer.append("...")
            flush(
                PAUSE_DURATIONS_MS[
                    PauseKind.ELLIPSIS
                ]
            )
            index += 3
            continue

        char = normalized[index]
        buffer.append(char)

        if char == ",":
            # La pausa se representa como silencio; no enviamos el nombre del
            # signo al motor porque algunos tokenizadores llegan a vocalizarlo.
            buffer.pop()
            flush(
                PAUSE_DURATIONS_MS[
                    PauseKind.COMMA
                ]
            )

        elif char in {";", ":"}:
            buffer.pop()
            flush(
                PAUSE_DURATIONS_MS[
                    PauseKind.SEMICOLON
                ]
            )

        elif char in {".", "?", "!"}:
            if (
                char == "."
                and (
                    _is_decimal_or_ip(normalized, index)
                    or _is_abbreviation(normalized, index)
                )
            ):
                index += 1
                continue

            flush(
                PAUSE_DURATIONS_MS[
                    PauseKind.SENTENCE
                ]
            )

        index += 1

    if buffer:
        flush(0)

    if segments:
        last = segments[-1]
        segments[-1] = SpeechSegment(
            text=last.text,
            pause_after_ms=0,
        )

    return segments
