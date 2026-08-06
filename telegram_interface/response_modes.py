"""Preferencia de entrega Telegram persistente y aislada por usuario Atlas."""
from __future__ import annotations

from enum import StrEnum
import re
import unicodedata
from typing import Any

from telegram_interface.storage import TelegramStorage


class TelegramResponseMode(StrEnum):
    AUTOMATIC = "automatic"
    TEXT_ONLY = "text_only"
    AUDIO_ONLY = "audio_only"


_ALIASES = {
    "modo texto": TelegramResponseMode.TEXT_ONLY,
    "modo voz": TelegramResponseMode.AUDIO_ONLY,
    "modo audio": TelegramResponseMode.AUDIO_ONLY,
    "modo automatico": TelegramResponseMode.AUTOMATIC,
    "responde por texto": TelegramResponseMode.TEXT_ONLY,
    "responde por voz": TelegramResponseMode.AUDIO_ONLY,
    "responde por audio": TelegramResponseMode.AUDIO_ONLY,
    "responde por automatico": TelegramResponseMode.AUTOMATIC,
}


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text).casefold())
    value = "".join(character for character in value if not unicodedata.combining(character))
    return " ".join(re.sub(r"[^\w]+", " ", value).split())


def detect_response_mode_directive(text: str) -> TelegramResponseMode | None:
    normalized = _normalize(text)
    direct = _ALIASES.get(normalized)
    if direct is not None:
        return direct
    patterns = (
        (r"(?:a partir de ahora )?(?:responde|respondeme|contesta|contestame) .*\b(?:solo|solamente|unicamente)\b.*\btexto", TelegramResponseMode.TEXT_ONLY),
        (r"(?:a partir de ahora )?(?:responde|respondeme|contesta|contestame) .*\b(?:solo|solamente|unicamente)\b.*\b(?:audio|voz)", TelegramResponseMode.AUDIO_ONLY),
        (r"(?:vuelve (?:al )?)?modo automatico", TelegramResponseMode.AUTOMATIC),
        (r"responde como antes", TelegramResponseMode.AUTOMATIC),
        (r"(?:cancela|deja) .*\bmodo\b.*\b(?:texto|audio|voz)", TelegramResponseMode.AUTOMATIC),
    )
    for pattern, mode in patterns:
        if re.fullmatch(pattern, normalized):
            return mode
    return None


class TelegramResponseModeStore:
    SECTION = "response_modes"

    def __init__(self, storage: TelegramStorage) -> None:
        self.storage = storage

    def get(self, atlas_user_id: str) -> TelegramResponseMode:
        raw = self.storage.section(self.SECTION).get(atlas_user_id.casefold())
        try:
            return TelegramResponseMode(str(raw))
        except ValueError:
            return TelegramResponseMode.AUTOMATIC

    def set(self, atlas_user_id: str, mode: TelegramResponseMode | str) -> TelegramResponseMode:
        resolved = TelegramResponseMode(mode)

        def mutate(data: dict[str, Any]) -> None:
            section = data.setdefault(self.SECTION, {})
            if not isinstance(section, dict):
                section = {}
                data[self.SECTION] = section
            section[atlas_user_id.casefold()] = resolved.value

        self.storage.update(mutate)
        return resolved


def resolve_delivery_mode(*, configured_mode: TelegramResponseMode | str, incoming_media_type: str | None, audio_available: bool) -> str:
    mode = TelegramResponseMode(configured_mode)
    if mode is TelegramResponseMode.TEXT_ONLY:
        return "text"
    if mode is TelegramResponseMode.AUDIO_ONLY:
        return "audio" if audio_available else "text"
    return "audio" if incoming_media_type in {"voice", "audio"} and audio_available else "text"


def confirmation_text(mode: TelegramResponseMode | str) -> str:
    resolved = TelegramResponseMode(mode)
    if resolved is TelegramResponseMode.TEXT_ONLY:
        return "De acuerdo. Te responderé por texto hasta que cambies el modo."
    if resolved is TelegramResponseMode.AUDIO_ONLY:
        return "De acuerdo. Te responderé por voz cuando esté disponible; si falla, usaré texto como respaldo."
    return "He restaurado el modo automático: texto para mensajes escritos y voz para notas de voz cuando esté disponible."
