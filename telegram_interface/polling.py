"""Ciclo long polling robusto con planificación conversacional multiusuario."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import replace
from pathlib import Path
import random
import threading
from time import sleep, monotonic, perf_counter, time as wall_time
from typing import Callable

from telegram_interface.client import TelegramClientError, TelegramClientProtocol
from telegram_interface.formatter import split_message
from telegram_interface.gateway import TelegramGateway
from telegram_interface.models import TelegramMessage
from telegram_interface.media import (
    TelegramMediaDownloader,
    TelegramMediaError,
    TelegramMediaLimits,
    TelegramMediaPipeline,
    TelegramMediaQuarantine,
    TelegramMediaValidator,
)
from telegram_interface.storage import TelegramStorage
from telegram_interface.progress import progress_delay_for
from telegram_interface.scheduler import ConversationScheduler
from telegram_interface.response_modes import resolve_delivery_mode


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
        media_limits: TelegramMediaLimits | None = None,
        media_ttl_hours: int | None = None,
        wall_clock: Callable[[], float] = wall_time,
        voice_renderer=None,
        response_mode_store=None,
        audio_max_duration_seconds: float = 180.0,
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
        self.media_max_bytes = int(media_max_bytes or 25 * 1024 * 1024)
        self.media_ttl_hours = int(media_ttl_hours or 24)
        self.wall_clock = wall_clock
        self.voice_renderer = voice_renderer
        self.response_mode_store = response_mode_store
        self.audio_max_duration_seconds = float(audio_max_duration_seconds)
        if media_limits is not None:
            limits = media_limits
        elif media_max_bytes is not None:
            limits = TelegramMediaLimits(*([int(media_max_bytes)] * 4))
        else:
            limits = TelegramMediaLimits()
        self.media_quarantine = TelegramMediaQuarantine(self.media_root, clock=wall_clock)
        self.media_pipeline = TelegramMediaPipeline(
            TelegramMediaDownloader(self.client, self.media_quarantine, TelegramMediaValidator(), limits)
        )

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
        if (
            message.media_type in {"voice", "audio"}
            and message.media_duration_seconds is not None
            and message.media_duration_seconds > self.audio_max_duration_seconds
        ):
            return replace(message, media_status="audio_too_long")
        try:
            self.media_pipeline.downloader.client = self.client
            envelope = self.media_pipeline.receive(
                media_type=message.media_type,
                file_id=message.file_id,
                declared_size=message.file_size,
                declared_mime=message.mime_type,
            )
            return replace(
                message,
                local_path=str(envelope.quarantine_path),
                media_status="quarantined",
                detected_mime=envelope.detected_mime,
                media_byte_size=envelope.byte_size,
                media_sha256=envelope.sha256,
                media_timings_ms=dict(envelope.timings_ms),
            )
        except TelegramMediaError as exc:
            return replace(message, media_status=exc.code)
        except TelegramClientError as exc:
            return replace(message, media_status=exc.code)

    def _cleanup_message_media(self, message: TelegramMessage) -> None:
        if not message.local_path:
            return
        self.media_quarantine.cleanup(message.local_path)

    def _cleanup_expired_media(self) -> None:
        self.media_quarantine.cleanup_expired(
            ttl_hours=self.media_ttl_hours,
            now=self.wall_clock(),
        )

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
                    stages = dict(getattr(response, "stage_timings_ms", {}) or {})
                    sent_audio = False
                    mode = "text"
                    delivery_hint = getattr(response, "delivery_hint", None)
                    if delivery_hint in {"text", "audio"}:
                        mode = delivery_hint
                    elif self.response_mode_store is not None and atlas_user_id:
                        mode = resolve_delivery_mode(
                            configured_mode=self.response_mode_store.get(atlas_user_id),
                            incoming_media_type=message.media_type,
                            audio_available=bool(self.voice_renderer and self.voice_renderer.is_available()),
                        )
                    if mode == "audio" and self.voice_renderer is not None and atlas_user_id:
                        rendered = self.voice_renderer.render(response.text, user_id=atlas_user_id)
                        stages.update(rendered.timings_ms)
                        try:
                            if rendered.success and rendered.ogg_path is not None:
                                upload_started = perf_counter()
                                with self._send_lock:
                                    self.client.send_voice(chat_id=message.user.chat_id, path=rendered.ogg_path)
                                stages["telegram.upload"] = round((perf_counter() - upload_started) * 1000, 3)
                                sent_audio = True
                        except TelegramClientError:
                            sent_audio = False
                        finally:
                            self.voice_renderer.cleanup(rendered)
                    if not sent_audio:
                        send_started = perf_counter()
                        self._send_chunks(message.user.chat_id, response.text, response.parse_mode)
                        stages["telegram_send"] = round((perf_counter() - send_started) * 1000, 3)
                    audit = getattr(self.gateway, "audit", None)
                    if audit is not None:
                        audit.record(
                            action="message_timing",
                            result="ok",
                            telegram_user_id=message.user.telegram_user_id,
                            chat_id=message.user.chat_id,
                            atlas_user_id=atlas_user_id,
                            stage_timings_ms=stages,
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
            self._send_progress_now(message)
            return future.result()

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
