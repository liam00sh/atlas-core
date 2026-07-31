"""Historial acotado y tolerante a corrupción para resultados de salud."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Iterable

from monitoring.models import HealthCheckResult


class HealthHistoryStore:
    """Persiste observaciones; no avisa ni ejecuta recuperaciones."""

    def __init__(self, path: str | Path, *, max_entries: int = 2000) -> None:
        self.path = Path(path)
        self.max_entries = max(1, int(max_entries))

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return payload if isinstance(payload, list) else []

    def append_many(self, results: Iterable[HealthCheckResult]) -> None:
        items = self.read()
        for result in results:
            item = asdict(result)
            item["state"] = result.state.value
            if result.severity is not None:
                item["severity"] = result.severity.value
            item["status"] = result.status
            items.append(item)
        items = items[-self.max_entries:]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
