from __future__ import annotations

import pytest

from telegram_interface.audit import TelegramAuditLogger, anonymize_id
from telegram_interface.config import TelegramConfig, TelegramConfigError
from telegram_interface.models import TelegramAccountState, TelegramRequestContext
from datetime import UTC, datetime


VALID_TOKEN = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcd"


def test_missing_token_disables_telegram():
    config = TelegramConfig.from_env({})
    assert config.enabled is False
    assert config.token is None


def test_empty_token_disables_telegram():
    assert TelegramConfig.from_env({"ATLAS_TELEGRAM_BOT_TOKEN": "  "}).enabled is False


def test_valid_simulated_token_enables_telegram():
    config = TelegramConfig.from_env({"ATLAS_TELEGRAM_BOT_TOKEN": VALID_TOKEN})
    assert config.enabled is True
    assert config.safe_summary()["token_present"] is True
    assert VALID_TOKEN not in str(config.safe_summary())
    assert VALID_TOKEN not in repr(config)


def test_explicit_disable_wins_over_token():
    config = TelegramConfig.from_env({"ATLAS_TELEGRAM_BOT_TOKEN": VALID_TOKEN, "ATLAS_TELEGRAM_ENABLED": "false"})
    assert config.enabled is False


@pytest.mark.parametrize("name,value", [
    ("ATLAS_TELEGRAM_POLL_TIMEOUT", "0"),
    ("ATLAS_TELEGRAM_RATE_LIMIT_PER_MINUTE", "no-number"),
    ("ATLAS_TELEGRAM_LINK_CODE_TTL_SECONDS", "20"),
    ("ATLAS_TELEGRAM_ENABLED", "perhaps"),
])
def test_invalid_values_are_rejected_without_token(name, value):
    with pytest.raises(TelegramConfigError) as caught:
        TelegramConfig.from_env({"ATLAS_TELEGRAM_BOT_TOKEN": VALID_TOKEN, name: value})
    assert VALID_TOKEN not in str(caught.value)


def test_invalid_token_error_does_not_echo_secret():
    secret = "not-a-valid-secret-token"
    with pytest.raises(TelegramConfigError) as caught:
        TelegramConfig.from_env({"ATLAS_TELEGRAM_BOT_TOKEN": secret})
    assert secret not in str(caught.value)


def test_audit_anonymizes_ids_and_omits_content(tmp_path):
    audit = TelegramAuditLogger(tmp_path / "audit.jsonl")
    audit.record(action="message", result="ok", telegram_user_id="123", chat_id="456", atlas_user_id="Liam")
    content = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    assert "123" not in content
    assert "456" not in content
    assert anonymize_id("123") in content
    assert "message_text" not in content


def test_atlas_core_log_omits_telegram_message_content(monkeypatch):
    from core.atlas import Atlas
    import core.atlas as atlas_module
    recorded = []
    atlas = Atlas(ai_provider=None)
    atlas.channel_request_context = TelegramRequestContext(
        channel="telegram", atlas_user_id=atlas.get_user(), session_id="telegram:test",
        telegram_user_id="1", chat_id="2", message_id=3,
        timestamp=datetime.now(UTC), active_personality="daxter",
        authentication_state=TelegramAccountState.LINKED,
        permissions=frozenset({"telegram.use"}),
    )
    monkeypatch.setattr(atlas_module, "info", recorded.append)
    atlas.process("¿Qué hora es?")
    assert any("CONTENIDO TELEGRAM OMITIDO" in entry for entry in recorded)
    assert all("que hora es" not in entry.casefold() for entry in recorded)
