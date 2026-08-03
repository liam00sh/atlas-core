"""Preferencias persistentes del formato de respuesta en Telegram."""

from __future__ import annotations

from enum import StrEnum
import re
from typing import Any

from telegram_interface.storage import TelegramStorage


class TelegramResponseMode(StrEnum):
    """Modos de respuesta disponibles para cada usuario."""

    AUTOMATIC = "automatic"
    TEXT_ONLY = "text_only"
    AUDIO_ONLY = "audio_only"


_ACTIVATE_TEXT = (
    r"\b(?:responde|respondeme|contesta|contestame)\b.*\b(?:solo|solamente|unicamente)\b.*\btexto\b",
    r"\bno me respondas\b.*\baudio\b",
)
_ACTIVATE_AUDIO = (
    r"\b(?:responde|respondeme|contesta|contestame)\b.*\b(?:solo|solamente|unicamente)\b.*\b(?:audio|voz)\b",
    r"\b(?:siempre|únicamente|unicamente)\b.*\baudio\b",
)
_CANCEL_TEXT = (
    r"\bdeja de responder\b.*\bsolo\b.*\btexto\b",
    r"\bcancela\b.*\bmodo\b.*\btexto\b",
)
_CANCEL_AUDIO = (
    r"\bdeja de responder\b.*\bsolo\b.*\baudio\b",
    r"\bcancela\b.*\bmodo\b.*\baudio\b",
)
_AUTOMATIC = (
    r"\bvuelve\b.*\bmodo automatico\b",
    r"\bmodo automatico\b",
    r"\bresponde como antes\b",
)


def _normalize(text: str) -> str:
    normalized = text.casefold()
    normalized = (
        normalized.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ü", "u")
    )
    return " ".join(normalized.strip().split())


def detect_response_mode_directive(
    text: str,
) -> TelegramResponseMode | None:
    """Detecta una orden explícita de cambio de modo."""

    normalized = _normalize(text)
    if not normalized:
        return None

    for pattern in _AUTOMATIC:
        if re.search(pattern, normalized):
            return TelegramResponseMode.AUTOMATIC

    for pattern in _CANCEL_TEXT + _CANCEL_AUDIO:
        if re.search(pattern, normalized):
            return TelegramResponseMode.AUTOMATIC

    for pattern in _ACTIVATE_TEXT:
        if re.search(pattern, normalized):
            return TelegramResponseMode.TEXT_ONLY

    for pattern in _ACTIVATE_AUDIO:
        if re.search(pattern, normalized):
            return TelegramResponseMode.AUDIO_ONLY

    return None


class TelegramResponseModeStore:
    """Guarda el modo por usuario de Atlas dentro del estado Telegram."""

    SECTION = "response_modes"

    def __init__(self, storage: TelegramStorage) -> None:
        self.storage = storage

    def get(
        self,
        atlas_user_id: str,
    ) -> TelegramResponseMode:
        values = self.storage.section(self.SECTION)
        raw = values.get(atlas_user_id.casefold())
        try:
            return TelegramResponseMode(str(raw))
        except ValueError:
            return TelegramResponseMode.AUTOMATIC

    def set(
        self,
        atlas_user_id: str,
        mode: TelegramResponseMode | str,
    ) -> TelegramResponseMode:
        resolved = TelegramResponseMode(mode)
        key = atlas_user_id.casefold()

        def mutate(data: dict[str, Any]) -> None:
            section = data.setdefault(self.SECTION, {})
            if not isinstance(section, dict):
                section = {}
                data[self.SECTION] = section
            section[key] = resolved.value

        self.storage.update(mutate)
        return resolved


def resolve_delivery_mode(
    *,
    configured_mode: TelegramResponseMode | str,
    incoming_media_type: str | None,
    audio_available: bool,
) -> str:
    """Decide si la salida debe ser texto o audio."""

    mode = TelegramResponseMode(configured_mode)

    if mode is TelegramResponseMode.TEXT_ONLY:
        return "text"

    if mode is TelegramResponseMode.AUDIO_ONLY:
        return "audio" if audio_available else "text"

    incoming_audio = incoming_media_type in {"voice", "audio"}
    if incoming_audio and audio_available:
        return "audio"

    return "text"


def confirmation_text(mode: TelegramResponseMode | str) -> str:
    resolved = TelegramResponseMode(mode)

    if resolved is TelegramResponseMode.TEXT_ONLY:
        return (
            "De acuerdo. A partir de ahora te responderé solo por texto "
            "hasta que canceles este modo."
        )

    if resolved is TelegramResponseMode.AUDIO_ONLY:
        return (
            "De acuerdo. A partir de ahora te responderé solo por audio "
            "cuando las voces estén disponibles. Si fallan, usaré texto "
            "como respaldo sin borrar tu preferencia."
        )

    return (
        "He restaurado el modo automático: texto para mensajes escritos "
        "y audio para mensajes de voz cuando la voz esté disponible."
    )
