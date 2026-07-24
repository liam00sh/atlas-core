"""Registro cerrado de acciones de automatización."""

from collections.abc import Iterable

from automation.models import ActionDefinition


class ActionNotFoundError(LookupError):
    pass


class ActionRegistrationError(ValueError):
    pass


class AutomationRegistry:
    def __init__(self) -> None:
        self._actions: dict[str, ActionDefinition] = {}

    def register(self, action: ActionDefinition) -> None:
        if not action.action_id.strip():
            raise ActionRegistrationError("action_id no puede estar vacío.")
        if action.action_id in self._actions:
            raise ActionRegistrationError(
                f"La acción '{action.action_id}' ya está registrada."
            )
        self._actions[action.action_id] = action

    def register_many(self, actions: Iterable[ActionDefinition]) -> None:
        for action in actions:
            self.register(action)

    def unregister(self, action_id: str) -> ActionDefinition:
        try:
            return self._actions.pop(action_id)
        except KeyError as exc:
            raise ActionNotFoundError(
                f"No existe la acción '{action_id}'."
            ) from exc

    def get(self, action_id: str) -> ActionDefinition:
        try:
            return self._actions[action_id]
        except KeyError as exc:
            raise ActionNotFoundError(
                f"No existe la acción '{action_id}'."
            ) from exc

    def list_actions(self) -> list[ActionDefinition]:
        return sorted(self._actions.values(), key=lambda item: item.action_id)

    @property
    def count(self) -> int:
        return len(self._actions)
