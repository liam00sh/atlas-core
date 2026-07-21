from __future__ import annotations

import threading

from telegram_interface.formatter import escape_markdown_v2, split_message
from telegram_interface.rate_limiter import TelegramRateLimiter
from telegram_interface.session_manager import TelegramSessionManager


def test_short_message_is_unchanged():
    assert split_message("hola") == ["hola"]


def test_long_response_is_fragmented_and_numbered():
    chunks = split_message("palabra " * 2000, limit=300)
    assert len(chunks) > 2
    assert chunks[0].startswith(f"[1/{len(chunks)}]")
    assert all(len(chunk) < 330 for chunk in chunks)


def test_empty_response_has_safe_fallback():
    assert split_message("  ") == ["Atlas no ha generado una respuesta."]


def test_code_block_is_closed_and_reopened_when_fragmented():
    chunks = split_message("```python\n" + ("print('x')\n" * 80) + "```", limit=180)
    assert len(chunks) > 1
    assert all(chunk.count("```") % 2 == 0 for chunk in chunks)


def test_markdown_special_characters_are_escaped():
    assert escape_markdown_v2("a_b[c].") == r"a\_b\[c\]\."


def test_rate_limit_isolated_by_user_and_chat():
    clock = [0.0]
    limiter = TelegramRateLimiter(2, window_seconds=60, clock=lambda: clock[0])
    assert limiter.allow("u1", "c1")
    assert limiter.allow("u1", "c1")
    assert not limiter.allow("u1", "c1")
    assert limiter.allow("u2", "c1")
    assert limiter.allow("u1", "c2")
    clock[0] = 61
    assert limiter.allow("u1", "c1")


def test_sessions_are_isolated_and_persistent(storage):
    manager = TelegramSessionManager(storage)
    manager.set("u1", "c1", pending_action="unlink")
    manager.set("u1", "c2", pending_action="other")
    restored = TelegramSessionManager(storage)
    assert restored.get("u1", "c1")["pending_action"] == "unlink"
    assert restored.get("u1", "c2")["pending_action"] == "other"


def test_same_session_lock_serializes(storage):
    manager = TelegramSessionManager(storage)
    assert manager.lock_for("u", "c") is manager.lock_for("u", "c")
    assert isinstance(manager.lock_for("u", "c"), type(threading.RLock()))
