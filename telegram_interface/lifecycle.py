"""Avisos de disponibilidad del bot Telegram.

Los mensajes se envían solo a cuentas vinculadas. El estado persistente evita
repeticiones idénticas y permite adaptar el saludo cuando cambia el día.
"""

from __future__ import annotations

from datetime import date, datetime
import random
from typing import Callable

from telegram_interface.client import TelegramClientError

def _display_assistant_name(name: str) -> str:
    """Devuelve el nombre visible del asistente con capitalización correcta."""

    normalized = str(name).strip().casefold()
    if normalized == "coco":
        return "Coco"
    return "Daxter"



START_DAXTER = (
    "¡Ya estoy operativo otra vez! ⚡",
    "{assistant} vuelve a estar por aquí. ¿Qué hacemos? 😄",
    "Todo listo de nuevo. {assistant} está en marcha 🚀",
)

START_COCO = (
    "Ya estoy disponible de nuevo 🌿",
    "{assistant} vuelve a estar operativo. Aquí estoy para ayudarte 😊",
    "Todo preparado otra vez. Podemos continuar cuando quieras.",
)

START_NEW_DAY = (
    "¡Preparado para un nuevo día! {assistant} vuelve a estar operativo ☀️",
    "Nuevo día, todo listo. Ya puedes contar conmigo 😊",
)

STOP_DAXTER = (
    "Voy a desconectarme un rato. Volveré pronto con las pilas cargadas ⚡",
    "{assistant} se apaga por ahora. Nos vemos en un rato 👋",
    "Me retiro un momento. En cuanto vuelva el equipo, estaré por aquí.",
)

STOP_COCO = (
    "Voy a estar desconectada un rato. Volveré pronto 🌙",
    "{assistant} se apaga de forma segura. Hablamos luego 😊",
    "Me despido por ahora. Cuando el equipo vuelva, continuaré aquí.",
)


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

    def _last_message(self) -> str:
        section = self.storage.section("lifecycle")
        return str(section.get("last_message", ""))

    def _choose(self, choices: tuple[str, ...]) -> str:
        previous = self._last_message()
        available = [
            message
            for message in choices
            if message != previous
        ] or list(choices)
        return random.choice(available)

    def _record(self, event: str, message: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")

        def mutate(data: dict) -> None:
            section = data.setdefault("lifecycle", {})
            last_start_date = section.get("last_start_date")

            if event == "started":
                last_start_date = date.today().isoformat()

            section.update(
                {
                    "last_event": event,
                    "last_message": message,
                    "last_event_at": now,
                    "last_start_date": last_start_date,
                }
            )

        self.storage.update(mutate)

    def notify_started(self) -> int:
        prior = self.storage.section("lifecycle").get("last_start_date")
        new_day = prior != date.today().isoformat()

        sent = 0
        final_message = ""

        for account in self._accounts():
            user_id = str(account.get("atlas_user_id", ""))
            assistant_name = _display_assistant_name(self.personality_resolver(user_id))
            personality = assistant_name.casefold()

            choices = (
                START_NEW_DAY
                if new_day
                else START_COCO
                if "coco" in personality
                else START_DAXTER
            )
            message = self._choose(choices).format(assistant=assistant_name)

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
            self._record("started", final_message)

        return sent

    def notify_stopping(self) -> int:
        sent = 0
        final_message = ""

        for account in self._accounts():
            user_id = str(account.get("atlas_user_id", ""))
            personality = self.personality_resolver(user_id).casefold()
            choices = (
                STOP_COCO
                if "coco" in personality
                else STOP_DAXTER
            )
            message = self._choose(choices).format(assistant=assistant_name)

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
            self._record("stopping", final_message)

        return sent
