"""Listas personales sencillas."""
from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from daily_life.storage import DailyLifeStorage


class PersonalListService:
    def __init__(self, storage: DailyLifeStorage) -> None:
        self.storage = storage

    @staticmethod
    def normalize_name(name: str) -> str:
        clean = " ".join(name.strip().casefold().split())
        clean = re.sub(r"^(?:la|el)\s+", "", clean)
        return clean or "compra"

    def create(self, owner: str, name: str) -> bool:
        list_name = self.normalize_name(name)
        def mutate(data: dict[str, Any]) -> bool:
            user = data.setdefault("users", {}).setdefault(owner.casefold(), {"display_name": owner, "lists": {}})
            lists = user.setdefault("lists", {})
            if list_name in lists:
                return False
            lists[list_name] = {"name": list_name, "items": [], "updated_at": datetime.now().isoformat(timespec="seconds")}
            return True
        return bool(self.storage.update(mutate))

    def add(self, owner: str, list_name: str, items: list[str]) -> list[str]:
        name = self.normalize_name(list_name)
        clean_items = [" ".join(item.strip().split()) for item in items if item.strip()]
        def mutate(data: dict[str, Any]) -> list[str]:
            user = data.setdefault("users", {}).setdefault(owner.casefold(), {"display_name": owner, "lists": {}})
            record = user.setdefault("lists", {}).setdefault(name, {"name": name, "items": [], "updated_at": None})
            current = record.setdefault("items", [])
            added = []
            existing = {str(item.get("text", "")).casefold() for item in current if isinstance(item, dict)}
            for item in clean_items:
                if item.casefold() in existing:
                    continue
                current.append({"text": item, "done": False})
                existing.add(item.casefold())
                added.append(item)
            record["updated_at"] = datetime.now().isoformat(timespec="seconds")
            return added
        return list(self.storage.update(mutate))

    def remove(self, owner: str, list_name: str, item_text: str) -> bool:
        name = self.normalize_name(list_name)
        expected = item_text.strip().casefold()
        def mutate(data: dict[str, Any]) -> bool:
            record = data.get("users", {}).get(owner.casefold(), {}).get("lists", {}).get(name)
            if not isinstance(record, dict):
                return False
            items = record.get("items", [])
            before = len(items)
            record["items"] = [item for item in items if str(item.get("text", "")).casefold() != expected]
            record["updated_at"] = datetime.now().isoformat(timespec="seconds")
            return len(record["items"]) != before
        return bool(self.storage.update(mutate))

    def get(self, owner: str, list_name: str) -> dict[str, Any] | None:
        name = self.normalize_name(list_name)
        return self.storage.snapshot().get("users", {}).get(owner.casefold(), {}).get("lists", {}).get(name)

    def names(self, owner: str) -> list[str]:
        lists = self.storage.snapshot().get("users", {}).get(owner.casefold(), {}).get("lists", {})
        return sorted(str(name) for name in lists)
