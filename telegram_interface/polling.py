"""Ciclo long polling robusto con planificación conversacional multiusuario."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
import hashlib
import mimetypes
import os
import random
import threading
from time import sleep, monotonic
from typing import Callable

from telegram_interface.client import TelegramClientError, TelegramClientProtocol
from telegram_interface.formatter import split_message
from telegram_interface.gateway import TelegramGateway
from telegram_interface.models import TelegramMessage
from telegram_interface.storage import TelegramStorage
from telegram_interface.progress import progress_delay_for
from telegram_interface.scheduler import ConversationScheduler


class TelegramWebhookConfiguredError(RuntimeError):
    pass


class TelegramPoller:
    def __init__(
        self,
        *,
        client: TelegramClientProtocol,
        gateway: TelegramGateway,
        storage: TelegramStorage,
        poll_timeout: int = 30,
        sleeper: Callable[[float], None] = sleep,
        random_source: Callable[[], float] = random.random,
        progress_delay_seconds: float = 4.0,
        progress_message_factory: Callable[[TelegramMessage], str] | None = None,
        delivery_dispatcher=None,
        scheduler: ConversationScheduler | None = None,
        owner_user_id: str = "Liam",
        lifecycle_notifier=None,
    ) -> None:
        self.client = client
        self.gateway = gateway
        self.storage = storage
        self.poll_timeout = poll_timeout
        self.sleeper = sleeper
        self.random_source = random_source
        self.progress_delay_seconds = max(0.0, float(progress_delay_seconds))
        self.progress_message_factory = progress_message_factory
        self.delivery_dispatcher = delivery_dispatcher
        self._stop = threading.Event()
        self._recent_updates: set[int] = set()
        self._send_lock = threading.RLock()
        # Worker auxiliar únicamente para medir el umbral de progreso dentro de
        # cada trabajo. El orden global lo decide ConversationScheduler.
        self._message_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="atlas-progress")
        self.scheduler = scheduler or ConversationScheduler(owner_user_id=owner_user_id)
        self.lifecycle_notifier = lifecycle_notifier
        root = Path(__file__).resolve().parents[1]
        self.media_root = root / "data" / "telegram_media" / "quarantine"
        self.media_max_bytes = int(os.getenv("ATLAS_TELEGRAM_MEDIA_MAX_BYTES", str(25 * 1024 * 1024)))
        self.media_ttl_hours = int(os.getenv("ATLAS_TELEGRAM_MEDIA_TTL_HOURS", "24"))

    def validate_long_polling(self) -> None:
        info = self.client.get_webhook_info()
        if str(info.get("url", "")).strip():
            raise TelegramWebhookConfiguredError(
                "El bot tiene un webhook configurado. Atlas no lo eliminara automaticamente; "
                "retiralo de forma explicita antes de iniciar long polling."
            )

    def stop(self) -> None:
        self._stop.set()
        self.scheduler.stop()
        self._message_executor.shutdown(wait=False, cancel_futures=True)

    def run(self, *, max_cycles: int | None = None) -> None:
        self.validate_long_polling()
        if self.lifecycle_notifier is not None:
            self.lifecycle_notifier.notify_start()
        offset = self.storage.get_offset()
        failures = 0
        cycles = 0
        try:
            while not self._stop.is_set() and (max_cycles is None or cycles < max_cycles):
                cycles += 1
                try:
                    if self.delivery_dispatcher is not None:
                        self.delivery_dispatcher.deliver_due()
                    updates = self.client.get_updates(offset=offset, timeout=self.poll_timeout)
                    failures = 0
                    for update in sorted(updates, key=lambda item: int(item.get("update_id", -1))):
                        update_id = int(update.get("update_id", -1))
                        if update_id < offset or update_id in self._recent_updates:
                            continue
                        message = TelegramMessage.from_update(update)
                        offset = update_id + 1
                        # Confirmar antes de procesar evita repetir acciones tras reinicio.
                        self.storage.set_offset(offset)
                        self._recent_updates.add(update_id)
                        if message is not None:
                            message = self._prepare_media(message)
                            self._submit_message(message)
                        if len(self._recent_updates) > 2048:
                            self._recent_updates = set(sorted(self._recent_updates)[-1024:])
                    if self.delivery_dispatcher is not None:
                        self.delivery_dispatcher.deliver_due()
                except TelegramClientError as exc:
                    if not exc.retryable:
                        raise
                    failures += 1
                    delay = min(60.0, 1.0 * (2 ** min(failures - 1, 6)))
                    delay += self.random_source() * min(1.0, delay / 4)
                    self.sleeper(delay)
        finally:
            if self.lifecycle_notifier is not None:
                self.lifecycle_notifier.notify_stop()
    def _prepare_media(self, message: TelegramMessage) -> TelegramMessage:
        if not message.media_type or not message.file_id:
            return message
        if message.file_size and message.file_size > self.media_max_bytes:
            return replace(message, media_status="rejected_too_large")
        allowed = {
            "photo": {"image/jpeg", "image/png", "image/webp"},
            "voice": {"audio/ogg", "audio/opus"},
            "audio": {"audio/mpeg", "audio/mp4", "audio/ogg", "audio/wav", "audio/x-wav"},
            "video": {"video/mp4", "video/webm"},
            "document": {"application/pdf", "text/plain", "text/csv", "application/json", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.openxmlformats-officedocument.presentationml.presentation"},
            "animation": {"video/mp4", "image/gif"},
        }
        mime = (message.mime_type or mimetypes.guess_type(message.file_name or "")[0] or "application/octet-stream").casefold()
        if mime not in allowed.get(message.media_type, set()):
            return replace(message, media_status="rejected_type")
        try:
            metadata = self.client.get_file(file_id=message.file_id)
            remote_path = str(metadata.get("file_path") or "").strip()
            if not remote_path:
                return replace(message, media_status="metadata_missing")
            extension = Path(message.file_name or remote_path).suffix[:10] or mimetypes.guess_extension(mime) or ".bin"
            digest = hashlib.sha256(f"{message.user.telegram_user_id}:{message.message_id}:{message.file_id}".encode()).hexdigest()[:24]
            day = datetime.now(UTC).strftime("%Y-%m-%d")
            destination = self.media_root / day / f"{digest}{extension}"
            path = self.client.download_file(file_path=remote_path, destination=destination, max_bytes=self.media_max_bytes)
            return replace(message, local_path=str(path), media_status="quarantined")
        except TelegramClientError as exc:
            return replace(message, media_status=exc.code)

    def _submit_message(self, message: TelegramMessage) -> None:
        account = self.gateway.linker.get_account(message.user.telegram_user_id)
        atlas_user_id = str(account.get("atlas_user_id") or message.user.telegram_user_id)
        session_id = f"telegram:{message.user.telegram_user_id}:{message.user.chat_id}"

        def run():
            return self._handle_with_ordered_progress(message)

        def done(response) -> None:
            if response is not None:
                self._send_chunks(message.user.chat_id, response.text, response.parse_mode)

        def failed(_exc: BaseException) -> None:
            self._send_chunks(
                message.user.chat_id,
                "Atlas no pudo procesar el mensaje de forma segura. Inténtalo de nuevo.",
                None,
            )

        self.scheduler.submit(
            user_id=atlas_user_id,
            session_id=session_id,
            text=message.text,
            run=run,
            on_done=done,
            on_error=failed,
        )

    def _handle_with_ordered_progress(self, message: TelegramMessage):
        if self.progress_message_factory is None or self.progress_delay_seconds <= 0:
            return self.gateway.handle(message)
        if message.text.lstrip().startswith("/"):
            return self.gateway.handle(message)

        delay = progress_delay_for(message.text, self.progress_delay_seconds)
        if delay < 0:
            return self.gateway.handle(message)

        future = self._message_executor.submit(self.gateway.handle, message)
        try:
            return future.result(timeout=delay)
        except FutureTimeout:
            sent_at = monotonic()
            self._send_progress_now(message)
            result = future.result()
            # Separación visual mínima para evitar que Telegram agrupe ambos envíos.
            remaining = 0.35 - (monotonic() - sent_at)
            if remaining > 0:
                self.sleeper(remaining)
            return result

    def _send_progress_now(self, message: TelegramMessage) -> None:
        try:
            text = str(self.progress_message_factory(message)).strip()
            if text:
                with self._send_lock:
                    self.client.send_message(chat_id=message.user.chat_id, text=text, parse_mode=None)
        except (TelegramClientError, RuntimeError, ValueError):
            return

    def _send_chunks(self, chat_id: str, text: str, parse_mode: str | None) -> None:
        with self._send_lock:
            for chunk in split_message(text):
                selected_mode = parse_mode
                attempts = 0
                while True:
                    try:
                        self.client.send_message(chat_id=chat_id, text=chunk, parse_mode=selected_mode)
                        break
                    except TelegramClientError as exc:
                        if selected_mode is not None and not exc.retryable:
                            selected_mode = None
                            continue
                        attempts += 1
                        if not exc.retryable or attempts >= 3:
                            raise
                        self.sleeper(float(2 ** (attempts - 1)))
