"""Evaluación centralizada de permisos para automatizaciones."""

from __future__ import annotations

from dataclasses import dataclass, field

from automation.models import (
    ActionDefinition,
    Automation,
    ConfirmationLevel,
    PermissionDecision,
    Visibility,
)


@dataclass(slots=True)
class UserAccess:
    user_id: str
    roles: set[str] = field(default_factory=set)
    permissions: set[str] = field(default_factory=set)
    groups: set[str] = field(default_factory=set)
    active: bool = True

    @property
    def is_admin(self) -> bool:
        return "owner" in self.roles or "administrator" in self.roles


class AutomationPermissions:
    def __init__(self, users: dict[str, UserAccess] | None = None) -> None:
        self._users: dict[str, UserAccess] = {}
        for key, access in (users or {}).items():
            if not isinstance(access, UserAccess):
                raise TypeError("Cada usuario debe ser una instancia de UserAccess.")
            # Conserva la clave del diccionario como alias de registro y
            # normaliza siempre el identificador efectivo.
            if not str(access.user_id).strip():
                access.user_id = str(key)
            self.set_user(access)

    @staticmethod
    def _normalize_user_id(user_id: str) -> str:
        return str(user_id).strip().casefold()

    def set_user(self, access: UserAccess) -> None:
        normalized = self._normalize_user_id(access.user_id)
        access.user_id = normalized
        self._users[normalized] = access

    def get_user(self, user_id: str) -> UserAccess:
        normalized = self._normalize_user_id(user_id)
        return self._users.get(
            normalized,
            UserAccess(user_id=normalized, active=False),
        )

    def can_view(self, user_id: str, automation: Automation) -> bool:
        user = self.get_user(user_id)
        if not user.active:
            return False
        normalized_user_id = self._normalize_user_id(user_id)
        owner_user_id = self._normalize_user_id(automation.owner_user_id)
        if user.is_admin or normalized_user_id == owner_user_id:
            return True
        if automation.visibility == Visibility.TECHNICAL:
            return False
        shared_user_ids = {self._normalize_user_id(item) for item in automation.shared_user_ids}
        if normalized_user_id in shared_user_ids:
            return True
        return bool(user.groups.intersection(automation.shared_group_ids))

    def can_manage(self, user_id: str, automation: Automation) -> bool:
        user = self.get_user(user_id)
        normalized_user_id = self._normalize_user_id(user_id)
        owner_user_id = self._normalize_user_id(automation.owner_user_id)
        return user.active and (user.is_admin or normalized_user_id == owner_user_id)

    def evaluate(
        self,
        user_id: str,
        action: ActionDefinition,
        automation: Automation,
    ) -> PermissionDecision:
        user = self.get_user(user_id)
        if not user.active:
            return PermissionDecision.DENY
        if action.technical_only and not user.is_admin:
            return PermissionDecision.DENY
        if (
            action.required_permission
            and action.required_permission not in user.permissions
            and not user.is_admin
        ):
            return PermissionDecision.DENY
        if not self.can_view(user_id, automation):
            return PermissionDecision.DENY
        if action.confirmation != ConfirmationLevel.NONE:
            return PermissionDecision.REQUIRE_CONFIRMATION
        return PermissionDecision.ALLOW
