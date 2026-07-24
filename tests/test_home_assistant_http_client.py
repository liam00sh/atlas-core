import io
import json
from urllib import error

import pytest

from automation.home_assistant_client import (
    HomeAssistantClientError,
    HomeAssistantErrorCode,
    HomeAssistantHttpClient,
)


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_connection_and_state(monkeypatch):
    responses = iter([
        FakeResponse({"message": "API running."}),
        FakeResponse({"entity_id": "sensor.atlas_temperature_lab", "state": "22.5", "attributes": {}}),
    ])
    monkeypatch.setattr("automation.home_assistant_client.request.urlopen", lambda *a, **k: next(responses))
    client = HomeAssistantHttpClient("http://ha:8123", "secret")
    assert client.is_available() is True
    assert client.get_state("sensor.atlas_temperature_lab").state == "22.5"


@pytest.mark.parametrize(
    "status, code",
    [
        (401, HomeAssistantErrorCode.UNAUTHORIZED),
        (403, HomeAssistantErrorCode.FORBIDDEN),
        (404, HomeAssistantErrorCode.NOT_FOUND),
        (500, HomeAssistantErrorCode.SERVER),
    ],
)
def test_http_errors_are_structured(monkeypatch, status, code):
    def fail(*_args, **_kwargs):
        raise error.HTTPError("http://ha", status, "failed", {}, io.BytesIO())

    monkeypatch.setattr("automation.home_assistant_client.request.urlopen", fail)
    client = HomeAssistantHttpClient("http://ha:8123", "super-secret", read_attempts=1)
    with pytest.raises(HomeAssistantClientError) as captured:
        client.get_state("sensor.atlas_temperature_lab")
    assert captured.value.code == str(code)
    assert "super-secret" not in str(captured.value)


def test_invalid_json(monkeypatch):
    class BadResponse(FakeResponse):
        def read(self):
            return b"not-json"

    monkeypatch.setattr("automation.home_assistant_client.request.urlopen", lambda *a, **k: BadResponse({}))
    client = HomeAssistantHttpClient("http://ha:8123", "secret", read_attempts=1)
    with pytest.raises(HomeAssistantClientError) as captured:
        client.get_state("sensor.atlas_temperature_lab")
    assert captured.value.code == str(HomeAssistantErrorCode.INVALID_JSON)


def test_read_retries_once(monkeypatch):
    calls = {"count": 0}

    def flaky(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise error.URLError(TimeoutError("timed out"))
        return FakeResponse({"entity_id": "sensor.atlas_temperature_lab", "state": "23", "attributes": {}})

    monkeypatch.setattr("automation.home_assistant_client.request.urlopen", flaky)
    client = HomeAssistantHttpClient(
        "http://ha:8123",
        "secret",
        sleep=lambda _: None,
    )
    assert client.get_state("sensor.atlas_temperature_lab").state == "23"
    assert calls["count"] == 2


def test_action_is_not_retried(monkeypatch):
    calls = {"count": 0}

    def fail(*_args, **_kwargs):
        calls["count"] += 1
        raise error.URLError("connection refused")

    monkeypatch.setattr("automation.home_assistant_client.request.urlopen", fail)
    client = HomeAssistantHttpClient("http://ha:8123", "secret", sleep=lambda _: None)
    with pytest.raises(HomeAssistantClientError):
        client.call_service("light", "turn_on", entity_id="light.atlas_light_lab")
    assert calls["count"] == 1
