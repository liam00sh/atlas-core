"""Auditoria minimizada de la interfaz Telegram."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import threading
from typing import Any


def anonymize_id(value: object) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]


class TelegramAuditLogger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def record(
        self,
        *,
        action: str,
        result: str,
        telegram_user_id: object,
        chat_id: object,
        atlas_user_id: str | None = None,
        personality: str | None = None,
        duration_ms: float | None = None,
        error_code: str | None = None,
    ) -> None:
        event: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "channel": "telegram",
            "telegram_user_id": anonymize_id(telegram_user_id),
            "chat_id": anonymize_id(chat_id),
            "atlas_user_id": atlas_user_id,
            "action": action,
            "result": result,
            "personality": personality,
            "duration_ms": duration_ms,
            "error_code": error_code,
        }
        line = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
            try:
                os.write(descriptor, line.encode("utf-8"))
            finally:
                os.close(descriptor)
