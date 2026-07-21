"""Continuidad conversacional mínima y compartida entre interfaces de Atlas."""
from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import threading
from typing import Any


class ConversationContinuityStore:
    """Guarda un contexto breve por usuario para compartirlo entre procesos.

    No sustituye la memoria persistente ni conserva historiales completos. Solo
    mantiene unos pocos intercambios recientes, truncados y separados por usuario.
    """

    def __init__(self, path: str | Path, *, max_exchanges: int = 6, max_chars: int = 500) -> None:
        self.path = Path(path)
        self.max_exchanges = max(1, int(max_exchanges))
        self.max_chars = max(80, int(max_chars))
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _key(user: str) -> str:
        return str(user).strip().casefold()

    def _read(self) -> dict[str, Any]:
        try:
            raw = self.path.read_text(encoding="utf-8").strip()
            data = json.loads(raw) if raw else {}
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write(self, data: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def _clean(self, text: str) -> str:
        value = re.sub(r"\s+", " ", str(text)).strip()
        return value[: self.max_chars]

    def append_exchange(self, user: str, user_text: str, assistant_text: str, *, channel: str = "unknown") -> None:
        key = self._key(user)
        if not key:
            return
        exchange = {
            "at": datetime.now(UTC).isoformat(),
            "channel": str(channel or "unknown"),
            "user": self._clean(user_text),
            "assistant": self._clean(assistant_text),
        }
        with self._lock:
            data = self._read()
            items = data.get(key, [])
            if not isinstance(items, list):
                items = []
            items.append(exchange)
            data[key] = items[-self.max_exchanges :]
            self._write(data)

    def format_for_prompt(self, user: str) -> str:
        key = self._key(user)
        if not key:
            return ""
        with self._lock:
            items = self._read().get(key, [])
        if not isinstance(items, list) or not items:
            return ""
        lines = [
            "CONTINUIDAD RECIENTE COMPARTIDA ENTRE INTERFACES",
            "Usa este bloque solo para mantener el hilo. No lo trates como memoria permanente ni inventes datos.",
        ]
        for item in items[-self.max_exchanges :]:
            if not isinstance(item, dict):
                continue
            channel = item.get("channel", "unknown")
            lines.append(f"[{channel}] Usuario: {item.get('user', '')}")
            lines.append(f"[{channel}] Asistente: {item.get('assistant', '')}")
        return "\n".join(lines)

    def clear_user(self, user: str) -> None:
        key = self._key(user)
        with self._lock:
            data = self._read()
            data.pop(key, None)
            self._write(data)
