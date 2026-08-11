"""Enrutamiento de avisos técnicos por usuario, presencia y permisos."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from monitoring.models import Incident


@dataclass(slots=True)
class AffectedUserPolicy:
    administrator_user_id: str = "Alex"
    home_assistant_user_ids: tuple[str, ...] = ("Alex", "Vega")


class NotificationRouter:
    def __init__(
        self,
        *,
        send_private: Callable[[str, str, str], bool],
        is_user_at_home: Callable[[str], bool] | None = None,
        has_capability: Callable[[str, str], bool] | None = None,
        policy: AffectedUserPolicy | None = None,
    ) -> None:
        self.send_private = send_private
        self.is_user_at_home = is_user_at_home or (lambda user_id: True)
        self.has_capability = has_capability or (lambda user_id, capability: user_id == "Alex")
        self.policy = policy or AffectedUserPolicy()

    def affected_users_for(self, source_id: str) -> set[str]:
        users = {self.policy.administrator_user_id}
        if source_id in {"home_assistant", "raspberry", "docker"}:
            for user_id in self.policy.home_assistant_user_ids:
                if (
                    self.has_capability(user_id, "home_assistant.use")
                    and self.is_user_at_home(user_id)
                ):
                    users.add(user_id)
        return users

    def notify_opened(self, incident: Incident) -> None:
        for user_id in sorted(incident.affected_users):
            self.send_private(
                user_id,
                f"⚠ {incident.title}",
                (
                    f"{incident.message}\n"
                    f"Estado: abierta\n"
                    f"Gravedad: {incident.severity.value}\n"
                    f"Acción automática: ninguna"
                ),
            )

    def notify_resolved(self, incident: Incident) -> None:
        for user_id in sorted(incident.affected_users):
            self.send_private(
                user_id,
                f"✅ Recuperado: {incident.title}",
                "El servicio vuelve a funcionar correctamente.",
            )

    def notify_user_joined_incident(
        self,
        incident: Incident,
        user_id: str,
    ) -> None:
        self.send_private(
            user_id,
            f"⚠ Incidencia activa: {incident.title}",
            incident.message,
        )
