from __future__ import annotations

import json
from urllib.error import URLError

import pytest

from telegram_interface.client import TelegramBotClient, TelegramClientError
from telegram_interface.instance_lock import TelegramInstanceLock, TelegramInstanceLockedError
from telegram_interface.storage import TelegramStorage


TOKEN = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcd"


class Response:
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return None
    def read(self):
        return json.dumps(self.payload).encode()


def test_client_decodes_success_without_exposing_token():
    requests = []
    def opener(request, timeout):
        requests.append((request, timeout))
        return Response({"ok": True, "result": {"id": 1}})
    client = TelegramBotClient(TOKEN, opener=opener)
    assert client.get_me() == {"id": 1}
    assert TOKEN not in repr(client)


def test_client_network_error_is_redacted_even_if_reason_contains_token():
    def opener(_request, timeout):
        raise URLError(f"failure {TOKEN}")
    client = TelegramBotClient(TOKEN, opener=opener)
    with pytest.raises(TelegramClientError) as caught:
        client.get_me()
    assert TOKEN not in str(caught.value)
    assert caught.value.retryable is True


def test_storage_recovers_from_incomplete_json(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("{incomplete", encoding="utf-8")
    storage = TelegramStorage(path)
    assert storage.get_offset() == 0
    assert storage.section("accounts") == {}


def test_storage_offset_is_monotonic_and_survives_restart(tmp_path):
    path = tmp_path / "state.json"
    storage = TelegramStorage(path)
    storage.set_offset(10)
    storage.set_offset(4)
    assert TelegramStorage(path).get_offset() == 10
    assert not list(tmp_path.glob("*.tmp"))


def test_two_storage_instances_observe_each_others_atomic_updates(tmp_path):
    path = tmp_path / "state.json"
    first = TelegramStorage(path)
    second = TelegramStorage(path)
    first.update(lambda data: data["accounts"].update({"1": {"state": "linked"}}))
    assert second.section("accounts")["1"]["state"] == "linked"
    second.set_offset(7)
    assert first.get_offset() == 7


def test_instance_lock_prevents_second_process_and_releases(tmp_path):
    path = tmp_path / "polling.lock"
    first = TelegramInstanceLock(path)
    second = TelegramInstanceLock(path)
    first.acquire()
    with pytest.raises(TelegramInstanceLockedError):
        second.acquire()
    first.release()
    second.acquire()
    second.release()
    assert not path.exists()
