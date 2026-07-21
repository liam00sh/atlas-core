"""Relaciones verificables y auditables entre recuerdos personales."""

import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


LINK_TYPES = frozenset({"related_to", "part_of", "belongs_to_project", "supports", "contradicts", "supersedes", "derived_from"})


@dataclass(frozen=True, slots=True)
class MemoryLink:
    link_id: str
    user_id: str
    source_memory_id: str
    target_memory_id: str
    link_type: str
    explanation: str
    evidence: dict
    created_at: str
    verified: bool = True


class MemoryLinkStore:
    """No infiere enlaces con IA; solo persiste evidencia suministrada."""

    def __init__(self, path: Path | str, memory_manager) -> None:
        self.path = Path(path)
        self.memory = memory_manager

    def _load(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _save(self, data: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.flush(); os.fsync(file.fileno())
        os.replace(temporary, self.path)

    def create(self, *, user_id: str, source_memory_id: str, target_memory_id: str, link_type: str, explanation: str, evidence: dict) -> MemoryLink:
        if link_type not in LINK_TYPES:
            raise ValueError("Tipo de enlace de memoria no válido.")
        if not explanation.strip() or not evidence:
            raise ValueError("Todo enlace requiere explicación y evidencia.")
        if source_memory_id == target_memory_id:
            raise ValueError("Un recuerdo no puede enlazarse consigo mismo.")
        for memory_id in (source_memory_id, target_memory_id):
            if self.memory.get_memory_by_id(memory_id, owner=user_id) is None:
                raise PermissionError("El recuerdo no existe o pertenece a otro usuario.")
        data = self._load()
        for item in data:
            if item["user_id"].casefold() == user_id.casefold() and item["source_memory_id"] == source_memory_id and item["target_memory_id"] == target_memory_id and item["link_type"] == link_type:
                return MemoryLink(**item)
        link = MemoryLink(uuid4().hex, user_id, source_memory_id, target_memory_id, link_type, explanation.strip(), evidence, datetime.now(UTC).isoformat())
        data.append(asdict(link)); self._save(data)
        return link

    def list_for_user(self, user_id: str) -> list[MemoryLink]:
        return [MemoryLink(**item) for item in self._load() if item.get("user_id", "").casefold() == user_id.casefold()]

    def context(self, *, user_id: str, query: str, limit: int = 20) -> list[dict]:
        seeds = self.memory.find_memories(owner=user_id, query=query, limit=limit)
        ids = {str(item["id"]) for item in seeds}
        links = self.list_for_user(user_id)
        changed = True
        while changed and len(ids) < limit:
            changed = False
            for link in links:
                if link.source_memory_id in ids and link.target_memory_id not in ids:
                    ids.add(link.target_memory_id); changed = True
                elif link.target_memory_id in ids and link.source_memory_id not in ids:
                    ids.add(link.source_memory_id); changed = True
        results = [self.memory.get_memory_by_id(item, owner=user_id) for item in ids]
        return [item for item in results if item is not None][:limit]

    def contradiction_candidates(self, *, user_id: str) -> list[dict]:
        by_key: dict[str, list[dict]] = {}
        for memory in self.memory.list_memories(owner=user_id):
            key = memory.get("memory_key")
            if key:
                by_key.setdefault(str(key), []).append(memory)
        return [
            {"memory_key": key, "memory_ids": [item["id"] for item in values], "action": "propose_review"}
            for key, values in by_key.items()
            if len({item["content"].casefold() for item in values}) > 1
        ]

    def groups(self, *, user_id: str, dimension: str = "topic") -> dict[str, list[dict]]:
        """Agrupa por tema, proyecto o entidad declarados en metadatos."""

        fields = {"topic": "topic", "project": "project", "entity": "entities"}
        if dimension not in fields:
            raise ValueError("Dimensión de agrupación no válida.")
        field = fields[dimension]
        grouped: dict[str, list[dict]] = {}
        for memory in self.memory.list_memories(owner=user_id):
            values = memory.get(field, [])
            if isinstance(values, str):
                values = [values]
            for value in values or []:
                grouped.setdefault(str(value), []).append(memory)
        return grouped
