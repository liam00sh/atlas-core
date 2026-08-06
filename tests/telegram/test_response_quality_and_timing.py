from __future__ import annotations

import json
from datetime import UTC, datetime
from time import sleep

from telegram_interface.audit import TelegramAuditLogger
from telegram_interface.core_adapter import AtlasCoreAdapter
from telegram_interface.models import GatewayResponse, TelegramMessage, TelegramUser
from telegram_interface.polling import TelegramPoller


def test_clean_response_removes_only_a_leading_literal_prompt_echo():
    response = AtlasCoreAdapter._clean_response(
        "Nora: ¿Dónde estoy ahora?\nTu ubicación temporal es Puerto Azul.",
        "¿Dónde estoy ahora?",
        "Nora",
    )
    assert response == "Tu ubicación temporal es Puerto Azul."


def test_clean_response_keeps_non_echo_factual_content():
    response = AtlasCoreAdapter._clean_response(
        "Según tu perfil, tu domicilio habitual es Villa Norte.",
        "¿Dónde vivo?",
        "Nora",
    )
    assert response.startswith("Según tu perfil")


def test_audit_accepts_only_named_numeric_timing_stages(tmp_path):
    path = tmp_path / "audit.jsonl"
    TelegramAuditLogger(path).record(
        action="message",
        result="ok",
        telegram_user_id="private-user",
        chat_id="private-chat",
        atlas_user_id="private-profile",
        stage_timings_ms={"model_call": 12.25, "message_content": 99, "weather_call": -1},
    )
    event = json.loads(path.read_text(encoding="utf-8"))
    assert event["stage_timings_ms"] == {"model_call": 12.25}
    assert "private-user" not in path.read_text(encoding="utf-8")
    assert "private-profile" not in path.read_text(encoding="utf-8")


class _SlowGateway:
    def handle(self, _message):
        sleep(0.03)
        return GatewayResponse("final")


class _Client:
    def __init__(self):
        self.sent = []

    def send_message(self, *, chat_id, text, parse_mode=None):
        self.sent.append((chat_id, text, parse_mode))
        return {}


class _Storage:
    pass


def _message(text="consulta compleja"):
    return TelegramMessage(
        update_id=1,
        message_id=2,
        user=TelegramUser(telegram_user_id="user", chat_id="chat"),
        text=text,
        timestamp=datetime.now(UTC),
    )


def test_progress_is_once_after_threshold_and_adds_no_artificial_delay():
    client = _Client()
    artificial_sleeps = []
    poller = TelegramPoller(
        client=client,
        gateway=_SlowGateway(),
        storage=_Storage(),
        sleeper=artificial_sleeps.append,
        progress_delay_seconds=0.005,
        progress_message_factory=lambda _item: "procesando",
    )
    try:
        response = poller._handle_with_ordered_progress(_message())
    finally:
        poller.stop()
    assert response.text == "final"
    assert [item[1] for item in client.sent] == ["procesando"]
    assert artificial_sleeps == []


def test_fast_command_never_emits_progress():
    client = _Client()
    poller = TelegramPoller(
        client=client,
        gateway=_SlowGateway(),
        storage=_Storage(),
        progress_delay_seconds=0.001,
        progress_message_factory=lambda _item: "procesando",
    )
    try:
        response = poller._handle_with_ordered_progress(_message("/status"))
    finally:
        poller.stop()
    assert response.text == "final"
    assert client.sent == []
