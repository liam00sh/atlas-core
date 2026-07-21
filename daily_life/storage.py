"""Persistencia atómica para listas y estado cotidiano."""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import threading
from typing import Any, Callable


class DailyLifeStorage:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self._data = self._load()

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {"version": 1, "users": {}}

    def _load(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return self._empty()
        return raw if isinstance(raw, dict) and isinstance(raw.get("users"), dict) else self._empty()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            self._data = self._load()
            return deepcopy(self._data)

    def update(self, mutator: Callable[[dict[str, Any]], Any]) -> Any:
        with self._lock:
            self._data = self._load()
            result = mutator(self._data)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            with temporary.open("w", encoding="utf-8", newline="\n") as stream:
                json.dump(self._data, stream, ensure_ascii=False, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            return result
