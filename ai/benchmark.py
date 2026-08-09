"""Registros de benchmark de IA sin razonamiento privado del modelo."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BenchmarkRecord:
    input: str
    mode: str
    route: str
    model: str
    fallback: bool
    latency_seconds: float
    success: bool
    selection_reason: str
    memory_used: bool = False
    tools_used: tuple[str, ...] = ()
    web_search: bool = False
    expected: str = ""
    obtained: str = ""


class BenchmarkRecorder:
    def __init__(self) -> None:
        self.records: list[BenchmarkRecord] = []

    def add(self, record: BenchmarkRecord) -> None:
        self.records.append(record)

    def write(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "contains_chain_of_thought": False,
            "records": [asdict(item) for item in self.records],
        }
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(target)
        return target

