"""Registro cerrado de entidades de Home Assistant autorizadas por Atlas."""

from __future__ import annotations

from collections.abc import Iterable

from automation.home_assistant_models import HomeEntityDefinition


class HomeEntityNotFoundError(LookupError):
    pass


class HomeEntityRegistrationError(ValueError):
    pass


class HomeDeviceRegistry:
    def __init__(self) -> None:
        self._entities: dict[str, HomeEntityDefinition] = {}

    def register(self, entity: HomeEntityDefinition) -> None:
        entity.validate()
        key = entity.entity_id.strip().casefold()
        if key in self._entities:
            raise HomeEntityRegistrationError(
                f"La entidad '{entity.entity_id}' ya está registrada."
            )
        self._entities[key] = entity

    def register_many(self, entities: Iterable[HomeEntityDefinition]) -> None:
        for entity in entities:
            self.register(entity)

    def get(self, entity_id: str) -> HomeEntityDefinition:
        key = str(entity_id).strip().casefold()
        try:
            return self._entities[key]
        except KeyError as exc:
            raise HomeEntityNotFoundError(
                f"La entidad '{entity_id}' no está autorizada."
            ) from exc

    def list_entities(self) -> list[HomeEntityDefinition]:
        return sorted(self._entities.values(), key=lambda item: item.entity_id)

    @property
    def count(self) -> int:
        return len(self._entities)
