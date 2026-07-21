from __future__ import annotations

from collections import deque

import pytest

from telegram_interface.client import TelegramClientError
from telegram_interface.polling import TelegramPoller, TelegramWebhookConfiguredError


def update(update_id, text="hola", user_id=100, chat_id=200):
    return {
        "update_id": update_id,
        "message": {
            "message_id": update_id + 10,
            "date": 1,
            "from": {"id": user_id, "username": "ignored"},
            "chat": {"id": chat_id, "type": "private"},
            "text": text,
        },
    }


class FakeClient:
    def __init__(self, batches=(), webhook=""):
        self.batches = deque(batches)
        self.webhook = webhook
        self.offsets = []
        self.sent = []

    def get_updates(self, *, offset, timeout):
        self.offsets.append((offset, timeout))
        if not self.batches:
            return []
        item = self.batches.popleft()
        if isinstance(item, Exception):
            raise item
        return item

    def send_message(self, **kwargs):
        self.sent.append(kwargs)
        return {}

    def get_webhook_info(self):
        return {"url": self.webhook}

    def get_me(self):
        return {"id": 1}


class FakeGateway:
    def __init__(self):
        self.messages = []
    def handle(self, message):
        self.messages.append(message)
        return type("Response", (), {"text": f"ok:{message.text}", "parse_mode": None})()


def test_polling_processes_updates_and_persists_offset(storage):
    client = FakeClient([[update(2), update(3)]])
    gateway = FakeGateway()
    TelegramPoller(client=client, gateway=gateway, storage=storage, poll_timeout=1).run(max_cycles=1)
    assert [message.update_id for message in gateway.messages] == [2, 3]
    assert storage.get_offset() == 4
    assert len(client.sent) == 2


def test_restart_uses_persisted_offset(storage):
    storage.set_offset(10)
    client = FakeClient([[]])
    TelegramPoller(client=client, gateway=FakeGateway(), storage=storage).run(max_cycles=1)
    assert client.offsets[0][0] == 10


def test_duplicate_or_old_update_is_ignored(storage):
    storage.set_offset(5)
    client = FakeClient([[update(4), update(5), update(5)]])
    gateway = FakeGateway()
    TelegramPoller(client=client, gateway=gateway, storage=storage).run(max_cycles=1)
    assert [item.update_id for item in gateway.messages] == [5]


def test_timeout_empty_batch_is_normal(storage):
    client = FakeClient([[]])
    TelegramPoller(client=client, gateway=FakeGateway(), storage=storage).run(max_cycles=1)
    assert storage.get_offset() == 0


def test_temporary_error_uses_bounded_backoff(storage):
    delays = []
    client = FakeClient([
        TelegramClientError("offline", retryable=True),
        TelegramClientError("offline", retryable=True),
        [],
    ])
    TelegramPoller(
        client=client, gateway=FakeGateway(), storage=storage,
        sleeper=delays.append, random_source=lambda: 0,
    ).run(max_cycles=3)
    assert delays == [1.0, 2.0]


def test_non_retryable_error_escapes_controlled(storage):
    client = FakeClient([TelegramClientError("bad", retryable=False)])
    with pytest.raises(TelegramClientError):
        TelegramPoller(client=client, gateway=FakeGateway(), storage=storage).run(max_cycles=1)


def test_webhook_is_detected_but_not_removed(storage):
    client = FakeClient(webhook="https://example.invalid/hook")
    with pytest.raises(TelegramWebhookConfiguredError):
        TelegramPoller(client=client, gateway=FakeGateway(), storage=storage).run(max_cycles=1)
    assert client.offsets == []


def test_stop_prevents_polling(storage):
    client = FakeClient([[update(1)]])
    poller = TelegramPoller(client=client, gateway=FakeGateway(), storage=storage)
    poller.stop()
    poller.run()
    assert client.offsets == []


def test_invalid_markdown_falls_back_to_plain_text(storage):
    class FormattingClient(FakeClient):
        def send_message(self, **kwargs):
            self.sent.append(kwargs)
            if kwargs.get("parse_mode"):
                raise TelegramClientError("bad format", retryable=False)
            return {}
    client = FormattingClient()
    poller = TelegramPoller(client=client, gateway=FakeGateway(), storage=storage)
    poller._send_chunks("200", "texto", "MarkdownV2")
    assert [call["parse_mode"] for call in client.sent] == ["MarkdownV2", None]


def test_send_failure_does_not_reprocess_core_action(storage):
    class OfflineSendClient(FakeClient):
        def send_message(self, **kwargs):
            raise TelegramClientError("offline", retryable=True)
    client = OfflineSendClient([[update(8)], []])
    gateway = FakeGateway()
    TelegramPoller(
        client=client, gateway=gateway, storage=storage,
        sleeper=lambda _delay: None, random_source=lambda: 0,
    ).run(max_cycles=2)
    assert len(gateway.messages) == 1
    assert storage.get_offset() == 9


def test_temporary_send_failure_retries_response_without_reprocessing(storage):
    class RecoveringClient(FakeClient):
        def __init__(self):
            super().__init__([[update(9)]])
            self.send_attempts = 0
        def send_message(self, **kwargs):
            self.send_attempts += 1
            if self.send_attempts < 3:
                raise TelegramClientError("offline", retryable=True)
            return {}
    delays = []
    client = RecoveringClient()
    gateway = FakeGateway()
    TelegramPoller(
        client=client, gateway=gateway, storage=storage,
        sleeper=delays.append, random_source=lambda: 0,
    ).run(max_cycles=1)
    assert client.send_attempts == 3
    assert delays == [1.0, 2.0]
    assert len(gateway.messages) == 1
