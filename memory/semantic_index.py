"""Índice semántico local e independiente para recuerdos personales."""

import hashlib
import json
import math
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from knowledge.fragment import KnowledgeFragment
from knowledge.privacy import KnowledgePrivacyFilter, Sensitivity
from memory.memory_manager import MemoryManager


@dataclass(frozen=True, slots=True)
class PersonalMemoryMatch:
    memory: dict[str, Any]
    semantic_score: float
    lexical_score: float
    score: float


class PersonalMemorySemanticIndex:
    """Sincroniza vectores por recuerdo con aislamiento estricto por usuario."""

    VERSION = 1

    def __init__(self, path: Path | str, memory: MemoryManager, embedder=None) -> None:
        self.path = Path(path)
        self.memory = memory
        self.embedder = embedder
        self.privacy = KnowledgePrivacyFilter()
        memory.register_change_listener(self.on_memory_change)

    def _empty(self) -> dict:
        return {"version": self.VERSION, "updated_at": None, "model": getattr(self.embedder, "model_name", None), "entries": {}}

    def load(self) -> dict:
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if data.get("version") == self.VERSION and isinstance(data.get("entries"), dict) else self._empty()
        except (OSError, json.JSONDecodeError, AttributeError):
            return self._empty()

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, self.path)

    @staticmethod
    def _hash(memory: dict) -> str:
        value = f"{memory.get('owner')}\0{memory.get('content')}\0{memory.get('updated_at', memory.get('created_at'))}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        if not left or len(left) != len(right):
            return 0.0
        denominator = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(x * x for x in right))
        return sum(a * b for a, b in zip(left, right)) / denominator if denominator else 0.0

    def sync(self, *, user_id: str | None = None, force: bool = False) -> dict[str, int]:
        data = self.load()
        previous = data["entries"]
        memories = self.memory.list_memories(owner=user_id)
        active_ids = {str(item["id"]) for item in memories}
        entries = {
            key: value for key, value in previous.items()
            if (user_id is not None and value.get("owner", "").casefold() != user_id.casefold()) or key in active_ids
        }
        pending = [
            item for item in memories
            if force or str(item["id"]) not in previous
            or previous[str(item["id"])].get("content_hash") != self._hash(item)
            or previous[str(item["id"])].get("model") != getattr(self.embedder, "model_name", None)
        ]
        if pending and self.embedder is not None:
            vectors = self.embedder.embed_many([str(item["content"]) for item in pending])
            for memory, vector in zip(pending, vectors):
                entries[str(memory["id"])] = {
                    "owner": memory["owner"], "content": memory["content"],
                    "content_hash": self._hash(memory), "model": self.embedder.model_name,
                    "vector": vector, "metadata": {
                        key: memory.get(key) for key in (
                            "visibility", "sensitivity", "confirmed", "category",
                            "created_at", "updated_at", "proposal_id",
                        )
                    },
                }
        elif pending:
            for memory in pending:
                entries.pop(str(memory["id"]), None)
        removed = len(set(previous) - set(entries))
        self.save({
            "version": self.VERSION, "updated_at": datetime.now(UTC).isoformat(),
            "model": getattr(self.embedder, "model_name", None), "entries": entries,
        })
        return {"embedded": len(pending) if self.embedder is not None else 0, "removed": removed, "total": len(entries)}

    def on_memory_change(self, action: str, memory: dict) -> None:
        if action == "deleted":
            data = self.load()
            data["entries"].pop(str(memory.get("id")), None)
            data["updated_at"] = datetime.now(UTC).isoformat()
            self.save(data)
        else:
            self.sync(user_id=str(memory.get("owner", "")))

    def _sensitive(self, memory_id: str, entry: dict) -> bool:
        fragment = KnowledgeFragment(
            "memory", memory_id, "Memoria personal", entry["content"], 1.0,
            metadata=entry.get("metadata", {}),
            sensitive=str(entry.get("metadata", {}).get("sensitivity", "normal")) != "normal",
        )
        return self.privacy.classify(fragment) is not Sensitivity.NONE

    def search(self, query: str, *, user_id: str, limit: int = 8, allow_sensitive: bool = False, has_sensitive_permission: bool = False) -> list[PersonalMemoryMatch]:
        if not query.strip() or self.embedder is None:
            return []
        data = self.load()
        if not data["entries"]:
            return []
        query_vector = self.embedder.embed_many([query.strip()])[0]
        query_terms = set(MemoryManager._normalize_search_text(query).split())
        matches = []
        for memory_id, entry in data["entries"].items():
            if str(entry.get("owner", "")).casefold() != user_id.casefold():
                continue
            if self._sensitive(memory_id, entry) and not (allow_sensitive and has_sensitive_permission):
                continue
            semantic = max(0.0, self._cosine(query_vector, [float(value) for value in entry.get("vector", [])]))
            terms = set(MemoryManager._normalize_search_text(entry["content"]).split())
            lexical = len(query_terms & terms) / max(1, len(query_terms))
            combined = 0.75 * semantic + 0.25 * lexical
            memory = {"id": memory_id, "owner": entry["owner"], "content": entry["content"], **entry.get("metadata", {})}
            matches.append(PersonalMemoryMatch(memory, semantic, lexical, combined))
        selected = sorted(matches, key=lambda item: (-item.score, item.memory["id"]))[:limit]
        self.memory.record_access(
            owner=user_id,
            memory_ids=[str(item.memory["id"]) for item in selected],
        )
        return selected
