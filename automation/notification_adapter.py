"""Adaptador de notificaciones desacoplado del proveedor real."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


class NotificationProvider(Protocol):
    def send(self, recipient_user_id: str, message: str) -> bool:
        ...


@dataclass(slots=True, frozen=True)
class NotificationReceipt:
    recipient_user_id: str
    delivered: bool
    channel: str
    sent_at: str


class NotificationAdapter:
    def __init__(
        self,
        provider: NotificationProvider,
        channel: str = "telegram",
    ) -> None:
        self.provider = provider
        self.channel = channel

    def send(
        self,
        recipient_user_id: str,
        title: str,
        message: str,
    ) -> NotificationReceipt:
        clean_title = title.strip()
        clean_message = message.strip()
        if not recipient_user_id.strip():
            raise ValueError("El destinatario no puede estar vacío.")
        if not clean_title:
            raise ValueError("El título no puede estar vacío.")
        if not clean_message:
            raise ValueError("El mensaje no puede estar vacío.")
        if len(clean_message) > 1000:
            raise ValueError("La notificación supera el límite permitido.")

        body = f"{clean_title}\n\n{clean_message}"
        delivered = bool(self.provider.send(recipient_user_id, body))
        return NotificationReceipt(
            recipient_user_id=recipient_user_id,
            delivered=delivered,
            channel=self.channel,
            sent_at=datetime.now(timezone.utc).isoformat(),
        )
