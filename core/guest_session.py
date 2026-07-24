"""Sesiones temporales de invitado para Atlas.

Una sesión de invitado mantiene:
- cuenta/bot autenticado original;
- interlocutor temporal;
- permisos mínimos de invitado;
- asistente heredado del bot;
- modo temporal independiente, inicialmente Clásico.
"""
from __future__ import annotations

from dataclasses import dataclass, field


GUEST_ALLOWED_CAPABILITIES = frozenset({
    "conversation",
    "assistant_identity_info",
    "assistant_switch",
    "mode_info",
    "mode_switch",
    "weather",
    "internet_lookup",
    "games",
    "jokes",
    "public_family_relationships",
})

GUEST_DENIED_CAPABILITIES = frozenset({
    "home_assistant",
    "memory_read",
    "memory_write",
    "files",
    "atlas_admin",
    "reminders",
    "telegram_linking",
    "user_management",
    "device_control",
    "backups",
})


@dataclass(slots=True)
class GuestSession:
    host_user: str
    guest_name: str
    assistant_name: str
    mode_name: str = "Clásico"
    active: bool = True
    allowed_capabilities: frozenset[str] = field(
        default_factory=lambda: GUEST_ALLOWED_CAPABILITIES
    )

    def can(self, capability: str) -> bool:
        return capability in self.allowed_capabilities

    def close(self) -> None:
        self.active = False


class GuestSessionManager:
    def __init__(self) -> None:
        self._session: GuestSession | None = None
        self._pending_guest_name: str | None = None

    def get(self) -> GuestSession | None:
        if self._session is None or not self._session.active:
            return None
        return self._session

    def is_active(self) -> bool:
        return self.get() is not None

    def set_pending_guest(self, name: str | None) -> None:
        self._pending_guest_name = (
            str(name).strip() if name is not None else None
        )

    def get_pending_guest(self) -> str | None:
        return self._pending_guest_name

    def clear_pending_guest(self) -> None:
        self._pending_guest_name = None

    def start(
        self,
        *,
        host_user: str,
        guest_name: str,
        assistant_name: str,
    ) -> GuestSession:
        self._session = GuestSession(
            host_user=str(host_user).strip(),
            guest_name=str(guest_name).strip(),
            assistant_name=str(assistant_name).strip(),
            mode_name="Clásico",
        )
        self.clear_pending_guest()
        return self._session

    def close(self) -> GuestSession | None:
        session = self.get()
        if session is not None:
            session.close()
        self._session = None
        self.clear_pending_guest()
        return session
