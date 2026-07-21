"""Mensajes y recordatorios entre usuarios Atlas mediante Telegram."""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path

from telegram_interface.interuser_delivery import InteruserRequestParser, TelegramDeliveryQueue
from telegram_interface.storage import TelegramStorage


class AtlasInteruserMixin:
    """Permite usar las mismas frases desde la CLI y desde Telegram."""

    def _interuser_queue(self) -> TelegramDeliveryQueue:
        existing = getattr(self, "_atlas_interuser_queue", None)
        if existing is not None:
            return existing
        data_dir = Path(os.environ.get("ATLAS_TELEGRAM_DATA_DIR", "data/integrations/telegram"))
        storage = getattr(self, "telegram_storage", None)
        if storage is None or Path(storage.path).resolve() != (data_dir / "state.json").resolve():
            storage = TelegramStorage(data_dir / "state.json")
        queue = TelegramDeliveryQueue(storage)
        setattr(self, "_atlas_interuser_queue", queue)
        return queue

    def _handle_interuser_request(self, text: str) -> bool:
        queue = self._interuser_queue()
        linked_users = queue.linked_users()
        parser = InteruserRequestParser(os.environ.get("ATLAS_TELEGRAM_TIMEZONE", "Europe/Madrid"))
        request = parser.parse(text, linked_user_ids=linked_users)
        if request is None:
            return False
        sender = self.get_user()
        if request.target_user_id.casefold() == sender.casefold():
            print("Ese mensaje va dirigido a tu propio usuario. Indica otra persona vinculada a Telegram.")
            return True
        result = queue.enqueue(sender, request)
        if not result.get("ok"):
            print(f"No encuentro una cuenta de Telegram activa vinculada a {request.target_user_id}.")
            return True
        if request.scheduled:
            timezone_name = os.environ.get("ATLAS_TELEGRAM_TIMEZONE", "Europe/Madrid")
            try:
                local = request.due_at_utc.astimezone(parser.timezone)
                moment = local.strftime("%d/%m/%Y a las %H:%M")
            except Exception:
                moment = "la hora indicada"
            print(
                f"He programado el recordatorio para {request.target_user_id} el {moment}. "
                f"Identificador: {result['id']}."
            )
        else:
            print(f"Se lo he enviado a {request.target_user_id} por Telegram.")
        return True
