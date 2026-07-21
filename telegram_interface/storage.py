"""Persistencia atomica para asociaciones, propuestas y estado Telegram."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import threading
from typing import Any, Callable
from contextlib import contextmanager


class TelegramStorage:
    """Almacen JSON pequeno, tolerante a corrupcion y seguro entre hilos."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self._data = self._load()
        self._mtime_ns = self._current_mtime()

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {"version": 3, "accounts": {}, "link_codes": {}, "sessions": {}, "deliveries": {}, "reply_context": {}, "lifecycle": {}, "offset": 0}

    def _load(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return self._empty()
        if not isinstance(raw, dict):
            return self._empty()
        base = self._empty()
        for key in base:
            if key in raw and isinstance(raw[key], type(base[key])):
                base[key] = raw[key]
        return base

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            self._refresh_locked()
            return deepcopy(self._data)

    def section(self, name: str) -> dict[str, Any]:
        with self._lock:
            self._refresh_locked()
            value = self._data.get(name, {})
            return deepcopy(value if isinstance(value, dict) else {})

    def update(self, mutator: Callable[[dict[str, Any]], Any]) -> Any:
        with self._lock:
            with self._process_lock():
                self._data = self._load()
                result = mutator(self._data)
                self._save_locked()
                return result

    def get_offset(self) -> int:
        with self._lock:
            self._refresh_locked()
            return int(self._data.get("offset", 0))

    def set_offset(self, offset: int) -> None:
        def mutate(data: dict[str, Any]) -> None:
            data["offset"] = max(int(data.get("offset", 0)), int(offset))
        self.update(mutate)

    def _save_locked(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        payload = json.dumps(self._data, ensure_ascii=False, indent=2, sort_keys=True)
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.path)
        self._mtime_ns = self._current_mtime()

    def _current_mtime(self) -> int | None:
        try:
            return self.path.stat().st_mtime_ns
        except OSError:
            return None

    def _refresh_locked(self) -> None:
        current = self._current_mtime()
        if current != self._mtime_ns:
            self._data = self._load()
            self._mtime_ns = current

    @contextmanager
    def _process_lock(self):
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        stream = lock_path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                stream.seek(0, os.SEEK_END)
                if stream.tell() == 0:
                    stream.write(b"0")
                    stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            try:
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            finally:
                stream.close()


def utc_now_text() -> str:
    return datetime.now(UTC).isoformat()
