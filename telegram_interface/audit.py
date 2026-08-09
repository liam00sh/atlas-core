"""Auditoria minimizada de la interfaz Telegram."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import threading
from typing import Any, Mapping


_TIMING_STAGES = frozenset({
    "receive_validation_linking", "context_memory", "tool_selection",
    "weather_call", "model_call", "core_processing", "composition",
    "telegram_send", "total",
    "media.download", "media.validation", "audio.convert", "stt.transcribe",
    "image.analyze", "face.detect", "face.compare", "document.extract",
    "tts.prepare", "tts.synthesize", "tts.convert", "tts.playback",
    "tts.total", "telegram.upload",
})


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
        stage_timings_ms: Mapping[str, float] | None = None,
        media_type: str | None = None,
        byte_size: int | None = None,
    ) -> None:
        event: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "channel": "telegram",
            "telegram_user_id": anonymize_id(telegram_user_id),
            "chat_id": anonymize_id(chat_id),
            "atlas_user_id": anonymize_id(atlas_user_id) if atlas_user_id else None,
            "action": action,
            "result": result,
            "personality": personality,
            "duration_ms": duration_ms,
            "error_code": error_code,
            "stage_timings_ms": {
                key: round(float(value), 3)
                for key, value in (stage_timings_ms or {}).items()
                if key in _TIMING_STAGES and isinstance(value, (int, float)) and value >= 0
            },
            "media_type": media_type if media_type in {"voice", "audio", "photo", "document"} else None,
            "byte_size": int(byte_size) if isinstance(byte_size, int) and byte_size >= 0 else None,
        }
        line = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(self.path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
            try:
                os.write(descriptor, line.encode("utf-8"))
            finally:
                os.close(descriptor)
