"""Infraestructura no destructiva de memoria a largo plazo."""

import json
import os
from datetime import UTC, datetime
from difflib import SequenceMatcher
from pathlib import Path


class LongTermMemoryService:
    def __init__(self, path: Path | str, memory_manager) -> None:
        self.path = Path(path)
        self.memory = memory_manager

    def _load(self) -> dict:
        if not self.path.exists():
            return {"summaries": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data.get("summaries"), dict) else {"summaries": {}}
        except (OSError, json.JSONDecodeError, AttributeError):
            return {"summaries": {}}

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.flush(); os.fsync(file.fileno())
        os.replace(temporary, self.path)

    def regenerate_summary(self, *, user_id: str, context: str, memory_ids: list[str]) -> dict:
        memories = [self.memory.get_memory_by_id(item, owner=user_id) for item in memory_ids]
        memories = [item for item in memories if item is not None]
        summary = " ".join(item["content"].rstrip(".") + "." for item in memories)
        data = self._load()
        key = f"{user_id.casefold()}:{context.casefold()}"
        record = {"user_id": user_id, "context": context, "content": summary, "source_memory_ids": [item["id"] for item in memories], "updated_at": datetime.now(UTC).isoformat()}
        data["summaries"][key] = record; self._save(data)
        return record

    def consolidation_candidates(self, *, user_id: str, threshold: float = 0.86) -> list[dict]:
        memories = self.memory.list_memories(owner=user_id)
        candidates = []
        for index, left in enumerate(memories):
            for right in memories[index + 1:]:
                similarity = SequenceMatcher(None, left["content"].casefold(), right["content"].casefold()).ratio()
                if similarity >= threshold:
                    candidates.append({"memory_ids": [left["id"], right["id"]], "similarity": similarity, "action": "propose_merge"})
        return candidates

