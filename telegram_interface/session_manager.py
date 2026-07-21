"""Sesiones minimas, aisladas por usuario y chat."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import threading
from typing import Any

from telegram_interface.storage import TelegramStorage


class TelegramSessionManager:
    def __init__(self, storage: TelegramStorage, *, ttl_seconds: int = 86400) -> None:
        self.storage = storage
        self.ttl_seconds = ttl_seconds
        self._locks: dict[str, threading.RLock] = {}
        self._guard = threading.Lock()

    @staticmethod
    def key(telegram_user_id: object, chat_id: object) -> str:
        return f"{telegram_user_id}:{chat_id}"

    def lock_for(self, telegram_user_id: object, chat_id: object) -> threading.RLock:
        key = self.key(telegram_user_id, chat_id)
        with self._guard:
            return self._locks.setdefault(key, threading.RLock())

    def get(self, telegram_user_id: object, chat_id: object) -> dict[str, Any]:
        key = self.key(telegram_user_id, chat_id)
        session = self.storage.section("sessions").get(key, {})
        expires = session.get("expires_at") if isinstance(session, dict) else None
        if expires:
            try:
                if datetime.fromisoformat(expires) <= datetime.now(UTC):
                    self.clear(telegram_user_id, chat_id)
                    return {}
            except ValueError:
                self.clear(telegram_user_id, chat_id)
                return {}
        return session if isinstance(session, dict) else {}

    def set(self, telegram_user_id: object, chat_id: object, **values: Any) -> dict[str, Any]:
        key = self.key(telegram_user_id, chat_id)
        def mutate(data: dict[str, Any]) -> dict[str, Any]:
            session = data["sessions"].setdefault(key, {})
            session.update(values)
            session["expires_at"] = (datetime.now(UTC) + timedelta(seconds=self.ttl_seconds)).isoformat()
            return dict(session)
        return self.storage.update(mutate)

    def clear(self, telegram_user_id: object, chat_id: object) -> None:
        key = self.key(telegram_user_id, chat_id)
        self.storage.update(lambda data: data["sessions"].pop(key, None))
