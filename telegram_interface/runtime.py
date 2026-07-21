"""Composicion de la interfaz Telegram sin efectos al importar."""

from __future__ import annotations

from dataclasses import dataclass

from telegram_interface.audit import TelegramAuditLogger
from telegram_interface.client import TelegramBotClient
from telegram_interface.config import TelegramConfig
from telegram_interface.core_adapter import AtlasCoreAdapter
from telegram_interface.gateway import TelegramGateway
from telegram_interface.identity_linker import TelegramIdentityLinker
from telegram_interface.interuser_delivery import TelegramDeliveryDispatcher, TelegramDeliveryQueue
from telegram_interface.polling import TelegramPoller
from telegram_interface.progress import build_progress_message
from telegram_interface.rate_limiter import TelegramRateLimiter
from telegram_interface.session_manager import TelegramSessionManager
from telegram_interface.storage import TelegramStorage
from telegram_interface.lifecycle import TelegramLifecycleNotifier


TELEGRAM_CHANNEL_ALLOWED_PERMISSIONS = frozenset(
    {
        "filesystem.read",
        "google.drive.read",
        "knowledge.read",
        "system.status.read",
        "memory.read",
        "memory.propose",
        "memory.write",
        "memory.update",
        "memory.delete",
        "memory.audit.read",
    }
)


@dataclass(slots=True)
class TelegramRuntime:
    config: TelegramConfig
    storage: TelegramStorage
    linker: TelegramIdentityLinker
    sessions: TelegramSessionManager
    gateway: TelegramGateway
    poller: TelegramPoller
    lifecycle: TelegramLifecycleNotifier | None = None

    def close(self) -> None:
        if self.lifecycle is not None:
            self.lifecycle.notify_stopping()
        self.poller.stop()
        self.gateway.close()


def build_runtime(atlas, config: TelegramConfig) -> TelegramRuntime:
    config.validate()
    if not config.enabled or not config.token:
        raise RuntimeError("Telegram esta desactivado o no tiene token configurado.")
    state_path = config.data_dir / "state.json"
    existing_storage = getattr(atlas, "telegram_storage", None)
    if (
        existing_storage is not None
        and existing_storage.path.resolve() == state_path.resolve()
    ):
        storage = existing_storage
        linker = getattr(atlas, "telegram_identity_linker")
        linker.ttl_seconds = config.link_code_ttl_seconds
    else:
        storage = TelegramStorage(state_path)
        linker = TelegramIdentityLinker(storage, ttl_seconds=config.link_code_ttl_seconds)
        try:
            account_tool = atlas.framework_tool_registry.get("atlas.telegram.accounts")
            account_tool.linker = linker
            account_tool.audit = TelegramAuditLogger(config.data_dir / "audit.jsonl")
        except Exception:
            pass
    sessions = TelegramSessionManager(storage, ttl_seconds=config.session_ttl_seconds)
    gateway = TelegramGateway(
        config=config,
        linker=linker,
        sessions=sessions,
        core=AtlasCoreAdapter(atlas),
        audit=TelegramAuditLogger(config.data_dir / "audit.jsonl"),
        rate_limiter=TelegramRateLimiter(config.rate_limit_per_minute),
        permission_resolver=lambda user: _telegram_permissions(atlas, user),
    )
    def progress_message(message) -> str:
        account = linker.get_account(message.user.telegram_user_id)
        atlas_user_id = account.get("atlas_user_id") if isinstance(account, dict) else None
        personality = gateway.core.active_personality(atlas_user_id) if atlas_user_id else "Daxter"
        return build_progress_message(message.text, personality)

    client = TelegramBotClient(config.token)
    lifecycle = TelegramLifecycleNotifier(
        storage,
        client,
        personality_resolver=lambda user_id: gateway.core.active_personality(user_id) if user_id else "Daxter",
    )
    lifecycle.notify_started()
    delivery_dispatcher = TelegramDeliveryDispatcher(
        TelegramDeliveryQueue(storage),
        client,
    )
    poller = TelegramPoller(
        client=client,
        gateway=gateway,
        storage=storage,
        poll_timeout=config.poll_timeout,
        progress_delay_seconds=4.0,
        progress_message_factory=progress_message,
        delivery_dispatcher=delivery_dispatcher,
        owner_user_id="Liam",
    )
    return TelegramRuntime(config, storage, linker, sessions, gateway, poller, lifecycle)


def _telegram_permissions(atlas, atlas_user_id: str) -> frozenset[str]:
    previous = atlas.get_user()
    try:
        if previous.casefold() != atlas_user_id.casefold():
            atlas.change_user(atlas_user_id)
        base = atlas.framework_tool_adapter.permission_resolver(atlas)
        # Interseccion explicita: Telegram solo permite los permisos que ya
        # posee el usuario y el permiso de acceso al canal.
        allowed = {
            permission
            for permission in base
            if permission in TELEGRAM_CHANNEL_ALLOWED_PERMISSIONS
        }
        return frozenset(allowed | {"telegram.use", "telegram.unlink"})
    finally:
        if atlas.get_user().casefold() != previous.casefold():
            atlas.change_user(previous)
