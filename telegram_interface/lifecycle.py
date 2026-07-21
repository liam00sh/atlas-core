"""Avisos de disponibilidad del bot Telegram.

Los mensajes se envían solo a cuentas vinculadas. El estado persistente evita
repeticiones idénticas y permite adaptar el saludo cuando cambia el día.
"""
from __future__ import annotations

from datetime import date, datetime
import random
from typing import Callable

from telegram_interface.client import TelegramClientError

START_DAXTER = (
    "¡Ya estoy operativo otra vez! ⚡",
    "Daxter vuelve a estar por aquí. ¿Qué hacemos? 😄",
    "Todo listo de nuevo. Atlas está en marcha 🚀",
)
START_COCO = (
    "Ya estoy disponible de nuevo 🌿",
    "Atlas vuelve a estar operativo. Aquí estoy para ayudarte 😊",
    "Todo preparado otra vez. Podemos continuar cuando quieras.",
)
START_NEW_DAY = (
    "¡Preparado para un nuevo día! Atlas vuelve a estar operativo ☀️",
    "Nuevo día, todo listo. Ya puedes contar conmigo 😊",
)
STOP_DAXTER = (
    "Voy a desconectarme un rato. Volveré pronto con las pilas cargadas ⚡",
    "Atlas se apaga por ahora. Nos vemos en un rato 👋",
    "Me retiro un momento. En cuanto vuelva el equipo, estaré por aquí.",
)
STOP_COCO = (
    "Voy a estar desconectada un rato. Volveré pronto 🌙",
    "Atlas se apaga de forma segura. Hablamos luego 😊",
    "Me despido por ahora. Cuando el equipo vuelva, continuaré aquí.",
)


class TelegramLifecycleNotifier:
    def __init__(self, storage, client, personality_resolver: Callable[[str], str] | None = None) -> None:
        self.storage = storage
        self.client = client
        self.personality_resolver = personality_resolver or (lambda _user: "Daxter")

    def _accounts(self) -> list[dict]:
        result = []
        for account in self.storage.section("accounts").values():
            if isinstance(account, dict) and account.get("state") == "linked" and account.get("chat_id"):
                result.append(account)
        return result

    def _last_message(self) -> str:
        section = self.storage.section("lifecycle")
        return str(section.get("last_message", ""))

    def _choose(self, choices: tuple[str, ...]) -> str:
        previous = self._last_message()
        available = [message for message in choices if message != previous] or list(choices)
        return random.choice(available)

    def _record(self, event: str, message: str) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        def mutate(data: dict) -> None:
            section = data.setdefault("lifecycle", {})
            section.update({"last_event": event, "last_message": message, "last_event_at": now, "last_start_date": date.today().isoformat() if event == "started" else section.get("last_start_date")})
        self.storage.update(mutate)

    def notify_started(self) -> int:
        prior = self.storage.section("lifecycle").get("last_start_date")
        new_day = prior != date.today().isoformat()
        sent = 0
        final_message = ""
        for account in self._accounts():
            user_id = str(account.get("atlas_user_id", ""))
            personality = self.personality_resolver(user_id).casefold()
            choices = START_NEW_DAY if new_day else (START_COCO if "coco" in personality else START_DAXTER)
            message = self._choose(choices)
            try:
                self.client.send_message(chat_id=str(account["chat_id"]), text=message)
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
            choices = STOP_COCO if "coco" in personality else STOP_DAXTER
            message = self._choose(choices)
            try:
                self.client.send_message(chat_id=str(account["chat_id"]), text=message)
                sent += 1
                final_message = message
            except TelegramClientError:
                continue
        if final_message:
            self._record("stopping", final_message)
        return sent
