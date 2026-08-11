from __future__ import annotations

from dataclasses import dataclass

import pytest

from automation.stage_e_runtime import build_stage_e_simulation
from core import context
from core.atlas import Atlas
from telegram_interface.core_adapter import AtlasCoreAdapter
from telegram_interface.models import TelegramAccountState, TelegramRequestContext


class NoLLM:
    calls = 0
    def get_model_name(self): return "no-llm"
    def get_provider_name(self): return "fake"
    def is_model_installed(self): return True
    def generate(self, _prompt):
        self.calls += 1
        raise AssertionError("La confirmación administrativa alcanzó el LLM")


@pytest.fixture
def atlas(tmp_path, monkeypatch):
    import core.atlas as atlas_module
    environment = build_stage_e_simulation(tmp_path / "stage_e.json")
    monkeypatch.setattr(atlas_module, "build_stage_e_environment", lambda *a, **k: environment)
    instance = Atlas(ai_provider=NoLLM())
    instance.users.current_user = "Alex"
    context.atlas = instance
    return instance


def _run(atlas, capsys, text):
    capsys.readouterr()
    assert atlas.process(text) is True
    return capsys.readouterr().out


def test_restart_creates_pending_and_exact_confirmation_executes_before_llm(
    atlas, capsys, monkeypatch
):
    launched = []
    monkeypatch.setattr("commands.restart_telegram.execute_confirmed", lambda: launched.append(True) or True)
    first = _run(atlas, capsys, "reinicia telegram")
    assert "confirmo reiniciar telegram" in first.casefold()
    pending = atlas.confirmations.get_confirmation()
    assert pending["action_name"] == "restart_telegram"
    assert pending["user"] == "Alex"

    second = _run(atlas, capsys, "confirmo reiniciar telegram")
    assert launched == [True]
    assert atlas.confirmations.get_confirmation() is None
    assert atlas.ai_provider.calls == 0


def test_restart_can_be_cancelled_and_invalid_phrase_never_executes(
    atlas, capsys, monkeypatch
):
    launched = []
    monkeypatch.setattr("commands.restart_telegram.execute_confirmed", lambda: launched.append(True) or True)
    _run(atlas, capsys, "reinicia telegram")
    invalid = _run(atlas, capsys, "confirmo otra cosa")
    assert "no he entendido" in invalid.casefold()
    assert atlas.confirmations.has_pending_confirmation()
    assert launched == []
    cancelled = _run(atlas, capsys, "cancelar")
    assert "no he ejecutado" in cancelled.casefold()
    assert not atlas.confirmations.has_pending_confirmation()
    assert launched == []


def _telegram_context(user, session):
    from datetime import UTC, datetime
    return TelegramRequestContext(
        channel="telegram", atlas_user_id=user, session_id=session,
        telegram_user_id="100", chat_id="200", message_id=1,
        timestamp=datetime.now(UTC), active_personality="daxter",
        authentication_state=TelegramAccountState.LINKED,
        permissions=frozenset(),
    )


def test_telegram_Alex_can_confirm_but_family_and_claimed_identity_cannot(
    atlas, monkeypatch
):
    launched = []
    monkeypatch.setattr("commands.restart_telegram.execute_confirmed", lambda: launched.append(True) or True)
    adapter = AtlasCoreAdapter(atlas)
    Alex = _telegram_context("Alex", "telegram:Alex")
    assert "confirmo reiniciar telegram" in adapter.process("Reinicia Telegram", Alex).casefold()
    assert adapter.process("confirmo reiniciar telegram", Alex)
    assert launched == [True]

    for family in ("Vega", "Carla", "Carla"):
        request = _telegram_context(family, f"telegram:{family}")
        denied = adapter.process("Reinicia Telegram", request)
        assert "solo alex" in denied.casefold()
        adapter.process("soy Alex", request)
        denied_again = adapter.process("Reinicia Telegram", request)
        assert "solo alex" in denied_again.casefold()
    assert launched == [True]
