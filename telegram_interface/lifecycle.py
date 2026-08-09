"""Avisos de disponibilidad del bot Telegram.

Los mensajes se envían solo a cuentas vinculadas. El estado persistente evita
repeticiones idénticas y permite adaptar el saludo cuando cambia el día.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Callable
from uuid import uuid4

from conversation.event_messages import ContextualMessageGenerator

from telegram_interface.client import TelegramClientError

def _display_assistant_name(name: str) -> str:
    """Devuelve el nombre visible del asistente con capitalización correcta."""

    normalized = str(name).strip().casefold()
    if normalized == "coco":
        return "Coco"
    return "Daxter"



def _key(value: str) -> str:
    """Devuelve la clave pública de personalidad."""

    normalized = " ".join(str(value or "").strip().casefold().split())
    if normalized == "coco":
        return "coco"
    if normalized == "daxter":
        return "daxter"
    return "atlas"


class TelegramLifecycleNotifier:
    """Envía avisos de arranque y parada a las cuentas vinculadas."""

    def __init__(
        self,
        storage,
        client,
        personality_resolver: Callable[[str], str] | None = None,
    ) -> None:
        self.storage = storage
        self.client = client
        self.personality_resolver = (
            personality_resolver or (lambda _user: "Daxter")
        )
        self.message_generator = ContextualMessageGenerator()
        # Un mismo proceso conserva el ID; un reinicio real crea otro.
        self._event_ids = {
            "started": f"started:{uuid4().hex}",
            "stopping": f"stopping:{uuid4().hex}",
        }

    def _accounts(self) -> list[dict]:
        result: list[dict] = []

        for account in self.storage.section("accounts").values():
            if (
                isinstance(account, dict)
                and account.get("state") == "linked"
                and account.get("chat_id")
            ):
                result.append(account)

        return result

    def _record(self, event: str, message: str, event_id: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")

        def mutate(data: dict) -> None:
            section = data.setdefault("lifecycle", {})
            last_start_date = section.get("last_start_date")
            recent_messages = list(section.get("recent_messages", ()))
            recent_messages.append(message)

            if event == "started":
                last_start_date = date.today().isoformat()

            section.update(
                {
                    "last_event": event,
                    "last_event_id": event_id,
                    "last_message": message,
                    "last_event_at": now,
                    "last_start_date": last_start_date,
                    "recent_messages": recent_messages[-8:],
                }
            )

        self.storage.update(mutate)

    def notify_started(self) -> int:
        event_id = self._event_ids["started"]
        if self.storage.section("lifecycle").get("last_event_id") == event_id:
            return 0
        prior = self.storage.section("lifecycle").get("last_start_date")
        new_day = prior != date.today().isoformat()

        sent = 0
        final_message = ""

        for account in self._accounts():
            user_id = str(account.get("atlas_user_id", ""))
            assistant_name = _display_assistant_name(self.personality_resolver(user_id))
            personality = assistant_name.casefold()

            recent = tuple(self.storage.section("lifecycle").get("recent_messages", ()))
            message = self.message_generator.generate(
                "started",
                user=user_id or "usuario",
                assistant=assistant_name,
                channel="telegram",
                situation="nuevo día" if new_day else "reinicio completado",
                recent=recent,
            )

            try:
                self.client.send_message(
                    chat_id=str(account["chat_id"]),
                    text=message,
                )
                sent += 1
                final_message = message
            except TelegramClientError:
                continue

        if final_message:
            self._record("started", final_message, event_id)

        return sent

    def notify_stopping(self) -> int:
        event_id = self._event_ids["stopping"]
        if self.storage.section("lifecycle").get("last_event_id") == event_id:
            return 0
        sent = 0
        final_message = ""

        for account in self._accounts():
            user_id = str(account.get("atlas_user_id", ""))
            assistant_name = _display_assistant_name(self.personality_resolver(user_id))
            recent = tuple(self.storage.section("lifecycle").get("recent_messages", ()))
            message = self.message_generator.generate(
                "stopping",
                user=user_id or "usuario",
                assistant=assistant_name,
                channel="telegram",
                situation="apagado solicitado",
                recent=recent,
            )

            try:
                self.client.send_message(
                    chat_id=str(account["chat_id"]),
                    text=message,
                )
                sent += 1
                final_message = message
            except TelegramClientError:
                continue

        if final_message:
            self._record("stopping", final_message, event_id)

        return sent
