"""Ciclo long polling robusto con planificación conversacional multiusuario."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
import hashlib
import os
import random
import threading
from time import sleep, monotonic, time as wall_time
from typing import Callable

from telegram_interface.client import TelegramClientError, TelegramClientProtocol
from telegram_interface.formatter import split_message
from telegram_interface.gateway import TelegramGateway
from telegram_interface.models import TelegramMessage
from telegram_interface.response_modes import resolve_delivery_mode
from telegram_interface.voice_delivery import TelegramVoiceRenderer
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
        owner_user_id: str = "REDACTED_2c7b6821719d",
        lifecycle_notifier=None,
        media_root: str | Path | None = None,
        media_max_bytes: int | None = None,
        media_ttl_hours: int | None = None,
        wall_clock: Callable[[], float] = wall_time,
        voice_renderer: TelegramVoiceRenderer | None = None,
        response_mode_store=None,
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
        self._pending_condition = threading.Condition()
        self._pending_jobs = 0
        # Worker auxiliar únicamente para medir el umbral de progreso dentro de
        # cada trabajo. El orden global lo decide ConversationScheduler.
        self._message_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="atlas-progress")
        self.scheduler = scheduler or ConversationScheduler(owner_user_id=owner_user_id)
        self.lifecycle_notifier = lifecycle_notifier
        root = Path(__file__).resolve().parents[1]
        self.media_root = Path(media_root) if media_root is not None else root / "data" / "telegram_media" / "quarantine"
        self.media_max_bytes = int(media_max_bytes if media_max_bytes is not None else os.getenv("ATLAS_TELEGRAM_MEDIA_MAX_BYTES", str(25 * 1024 * 1024)))
        self.media_ttl_hours = int(media_ttl_hours if media_ttl_hours is not None else os.getenv("ATLAS_TELEGRAM_MEDIA_TTL_HOURS", "24"))
        self.wall_clock = wall_clock
        self.voice_renderer = voice_renderer
        self.response_mode_store = response_mode_store

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
        self._cleanup_expired_media()
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
                    delay = (
                        min(60.0, exc.retry_after)
                        if exc.kind == "rate_limit" and exc.retry_after is not None
                        else min(60.0, 1.0 * (2 ** min(failures - 1, 6)))
                    )
                    if exc.kind != "rate_limit":
                        delay += self.random_source() * min(1.0, delay / 4)
                    self.sleeper(delay)
        finally:
            if max_cycles is not None:
                with self._pending_condition:
                    self._pending_condition.wait_for(
                        lambda: self._pending_jobs == 0,
                        timeout=max(5.0, float(self.poll_timeout) + 5.0),
                    )
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
        inferred_transport_mime = {
            "photo": "image/jpeg",
            "voice": "audio/ogg",
        }.get(message.media_type)
        # Para documentos y audios no se confía en el sufijo aportado por el
        # remitente. El tipo debe venir en los metadatos de Telegram.
        mime = (message.mime_type or inferred_transport_mime or "application/octet-stream").casefold()
        if mime not in allowed.get(message.media_type, set()):
            return replace(message, media_status="rejected_type")
        try:
            metadata = self.client.get_file(file_id=message.file_id)
            remote_path = str(metadata.get("file_path") or "").strip()
            remote_parts = PurePosixPath(remote_path).parts
            if (
                not remote_path
                or "://" in remote_path
                or ".." in remote_parts
                or remote_path.startswith(("/", "\\"))
            ):
                return replace(message, media_status="metadata_missing")
            declared_size = int(metadata.get("file_size") or 0)
            if declared_size and declared_size > self.media_max_bytes:
                return replace(message, media_status="rejected_too_large")
            extension = {
                "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
                "audio/ogg": ".ogg", "audio/opus": ".opus", "audio/mpeg": ".mp3",
                "audio/mp4": ".m4a", "audio/wav": ".wav", "audio/x-wav": ".wav",
                "video/mp4": ".mp4", "video/webm": ".webm", "image/gif": ".gif",
                "application/pdf": ".pdf", "text/plain": ".txt", "text/csv": ".csv",
                "application/json": ".json",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
            }.get(mime, ".bin")
            digest = hashlib.sha256(f"{message.user.telegram_user_id}:{message.message_id}:{message.file_id}".encode()).hexdigest()[:24]
            day = datetime.now(UTC).strftime("%Y-%m-%d")
            destination = self.media_root / day / f"{digest}{extension}"
            path = self.client.download_file(file_path=remote_path, destination=destination, max_bytes=self.media_max_bytes)
            return replace(message, local_path=str(path), media_status="quarantined")
        except TelegramClientError as exc:
            return replace(message, media_status=exc.code)

    def _cleanup_message_media(self, message: TelegramMessage) -> None:
        if not message.local_path:
            return
        path = Path(message.local_path)
        try:
            path.resolve().relative_to(self.media_root.resolve())
        except (OSError, ValueError):
            return
        try:
            path.unlink(missing_ok=True)
        except OSError:
            return

    def _cleanup_expired_media(self) -> None:
        if not self.media_root.exists():
            return
        cutoff = self.wall_clock() - max(0, self.media_ttl_hours) * 3600
        for path in self.media_root.rglob("*"):
            if not path.is_file():
                continue
            try:
                if path.stat().st_mtime <= cutoff:
                    path.unlink(missing_ok=True)
            except OSError:
                continue

    def _submit_message(self, message: TelegramMessage) -> None:
        linker = getattr(self.gateway, "linker", None)
        account = linker.get_account(message.user.telegram_user_id) if linker is not None else {}
        atlas_user_id = str((account or {}).get("atlas_user_id") or message.user.telegram_user_id)
        session_id = f"telegram:{message.user.telegram_user_id}:{message.user.chat_id}"

        def run():
            return self._handle_with_ordered_progress(message)

        def finish_pending() -> None:
            with self._pending_condition:
                self._pending_jobs = max(0, self._pending_jobs - 1)
                self._pending_condition.notify_all()

        def done(response) -> None:
            try:
                if response is not None:
                    delivered = self._send_response(
                        message=message,
                        atlas_user_id=atlas_user_id,
                        text=response.text,
                        parse_mode=response.parse_mode,
                    )
                    if not delivered:
                        self._send_chunks(
                            message.user.chat_id,
                            response.text,
                            response.parse_mode,
                        )
            finally:
                self._cleanup_message_media(message)
                finish_pending()

        def failed(_exc: BaseException) -> None:
            try:
                assistant_name = "El asistente"
                try:
                    if atlas_user_id and hasattr(self.gateway.core, "active_personality"):
                        assistant_name = str(
                            self.gateway.core.active_personality(atlas_user_id)
                        ).strip().capitalize() or assistant_name
                except Exception:
                    pass
                self._send_chunks(
                    message.user.chat_id,
                    f"{assistant_name} no pudo procesar el mensaje de forma segura. Inténtalo de nuevo.",
                    None,
                )
            finally:
                self._cleanup_message_media(message)
                finish_pending()

        with self._pending_condition:
            self._pending_jobs += 1

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


    def _send_response(
        self,
        *,
        message: TelegramMessage,
        atlas_user_id: str,
        text: str,
        parse_mode: str | None,
    ) -> bool:
        mode = (
            self.response_mode_store.get(atlas_user_id)
            if self.response_mode_store is not None
            else "automatic"
        )
        audio_available = (
            self.voice_renderer is not None
            and self.voice_renderer.is_available()
        )
        delivery = resolve_delivery_mode(
            configured_mode=mode,
            incoming_media_type=message.media_type,
            audio_available=audio_available,
        )

        if delivery != "audio" or self.voice_renderer is None:
            return False

        self.voice_renderer._current_user = atlas_user_id
        result = self.voice_renderer.render(text)
        if not result.success or result.ogg_path is None:
            return False

        try:
            with self._send_lock:
                self.client.send_voice(
                    chat_id=message.user.chat_id,
                    voice_path=result.ogg_path,
                )
            return True
        except TelegramClientError:
            return False
        finally:
            self.voice_renderer.cleanup(result)

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
