from __future__ import annotations

from datetime import UTC, datetime

import pytest

from telegram_interface.audit import TelegramAuditLogger
from telegram_interface.config import TelegramConfig
from telegram_interface.core_adapter import CallableCoreAdapter
from telegram_interface.gateway import TelegramGateway
from telegram_interface.identity_linker import TelegramIdentityLinker
from telegram_interface.models import TelegramMessage, TelegramUser
from telegram_interface.session_manager import TelegramSessionManager
from telegram_interface.storage import TelegramStorage


@pytest.fixture
def config(tmp_path):
    return TelegramConfig(
        enabled=True,
        token="123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcd",
        data_dir=tmp_path,
        processing_timeout_seconds=5,
    )


@pytest.fixture
def storage(tmp_path):
    return TelegramStorage(tmp_path / "state.json")


@pytest.fixture
def linker(storage):
    return TelegramIdentityLinker(storage, ttl_seconds=600)


@pytest.fixture
def personalities():
    return {"Liam": "daxter", "Saray": "coco"}


@pytest.fixture
def gateway(config, storage, linker, tmp_path, personalities):
    core = CallableCoreAdapter(
        lambda text, context: f"{context.atlas_user_id}:{text}",
        personality_getter=lambda user: personalities.get(user, "daxter"),
        personality_setter=lambda user, value: not personalities.__setitem__(user, value),
    )
    instance = TelegramGateway(
        config=config,
        linker=linker,
        sessions=TelegramSessionManager(storage),
        core=core,
        audit=TelegramAuditLogger(tmp_path / "audit.jsonl"),
        permission_resolver=lambda _user: {"telegram.use", "memory.read"},
    )
    yield instance
    instance.close()


def make_message(text, *, user_id="100", chat_id="200", update_id=1, message_id=10, username="ignored"):
    return TelegramMessage(
        update_id=update_id,
        message_id=message_id,
        user=TelegramUser(user_id, chat_id, username=username, first_name="Visible"),
        text=text,
        timestamp=datetime.now(UTC),
    )


def link_user(linker, *, user_id="100", chat_id="200", atlas_user="Liam"):
    user = TelegramUser(user_id, chat_id, username=atlas_user.casefold())
    code = linker.request_code(user)
    linker.confirm_code(code, atlas_user, user_exists=lambda candidate: candidate in {"Liam", "Saray"})
    return code
