"""Modelos de transporte de la interfaz Telegram."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class TelegramAccountState(StrEnum):
    UNLINKED = "unlinked"
    LINK_PENDING = "link_pending"
    LINKED = "linked"
    BLOCKED = "blocked"
    REVOKED = "revoked"


@dataclass(frozen=True, slots=True)
class TelegramUser:
    telegram_user_id: str
    chat_id: str
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


@dataclass(frozen=True, slots=True)
class TelegramMessage:
    update_id: int
    message_id: int
    user: TelegramUser
    text: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    chat_type: str = "private"
    media_type: str | None = None
    file_id: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    file_size: int | None = None

    @classmethod
    def from_update(cls, update: dict[str, Any]) -> TelegramMessage | None:
        message = update.get("message")
        if not isinstance(message, dict):
            return None
        sender = message.get("from")
        chat = message.get("chat")
        if not isinstance(sender, dict) or not isinstance(chat, dict):
            return None
        if "id" not in sender or "id" not in chat or "message_id" not in message:
            return None

        text = message.get("text")
        caption = message.get("caption")
        content = text if isinstance(text, str) else caption if isinstance(caption, str) else ""
        media_type = None
        media: dict[str, Any] | None = None
        photos = message.get("photo")
        if isinstance(photos, list) and photos:
            candidates = [item for item in photos if isinstance(item, dict)]
            if candidates:
                media_type = "photo"
                media = max(candidates, key=lambda item: int(item.get("file_size") or 0))
        for candidate_type in ("voice", "audio", "video", "document", "animation"):
            candidate = message.get(candidate_type)
            if media is None and isinstance(candidate, dict):
                media_type = candidate_type
                media = candidate
        if not content and media is None:
            return None

        timestamp = datetime.fromtimestamp(int(message.get("date", 0)), tz=UTC)
        return cls(
            update_id=int(update["update_id"]),
            message_id=int(message["message_id"]),
            user=TelegramUser(
                telegram_user_id=str(sender["id"]),
                chat_id=str(chat["id"]),
                username=_optional_text(sender.get("username")),
                first_name=_optional_text(sender.get("first_name")),
                last_name=_optional_text(sender.get("last_name")),
            ),
            text=content,
            timestamp=timestamp,
            chat_type=str(chat.get("type", "private")),
            media_type=media_type,
            file_id=_optional_text(media.get("file_id")) if media else None,
            file_name=_optional_text(media.get("file_name")) if media else None,
            mime_type=_optional_text(media.get("mime_type")) if media else None,
            file_size=int(media.get("file_size") or 0) if media and media.get("file_size") else None,
        )



@dataclass(frozen=True, slots=True)
class TelegramRequestContext:
    channel: str
    atlas_user_id: str | None
    session_id: str
    telegram_user_id: str
    chat_id: str
    message_id: int
    timestamp: datetime
    active_personality: str
    authentication_state: TelegramAccountState
    permissions: frozenset[str]


@dataclass(frozen=True, slots=True)
class GatewayResponse:
    text: str
    parse_mode: str | None = None
    close_session: bool = False


def _optional_text(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None
