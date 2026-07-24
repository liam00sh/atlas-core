"""Auditoría JSONL inmutable desde la interfaz normal de Atlas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automation.models import AuditEvent


SECRET_KEYS = {
    "password", "contraseña", "token", "api_key", "secret",
    "credential", "authorization", "code", "pin",
}


def _redact(value: Any, key: str | None = None) -> Any:
    if key and key.casefold() in SECRET_KEYS:
        return "[REDACTADO]"
    if isinstance(value, dict):
        return {k: _redact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return [_redact(item) for item in value]
    return value


class AutomationAudit:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, event: AuditEvent) -> None:
        payload = event.to_dict()
        payload["details"] = _redact(payload.get("details", {}))
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events
