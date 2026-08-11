from __future__ import annotations

from types import SimpleNamespace

from ai.models.roles import ModelRoleRegistry
from commands import ai_model, ai_status
from console.command_help import handle_command_help_request, render_help_for_user, search_entries
from conversation.manager import ConversationManager
from core import context
from core.atlas_commands import AtlasCommandsMixin
from telegram_interface.formatter import split_message, TELEGRAM_SAFE_CHUNK
from utils.text_normalizer import normalize_text


class AtlasStub:
    def __init__(self):
        self.current_user_id = "Alex"
        self.conversation_manager = ConversationManager()
        self.conversation_manager.begin_turn(
            channel="cli", session_id="dev", authenticated_identity="Alex"
        )
        self.ai_runtime = SimpleNamespace(registry=ModelRoleRegistry())
        self.last_ai_trace = None
    def get_user(self): return "Alex"
    def get_main_user(self): return "Alex"


def test_selector_supports_all_local_roles_and_rejects_external(capsys):
    atlas = AtlasStub()
    context.atlas = atlas
    for role in ("fast", "reasoning", "deep", "auto"):
        assert ai_model.execute(role) is True
        assert atlas.conversation_manager.get_ai_override() == role
    ai_model.execute("external")
    assert atlas.conversation_manager.get_ai_override() == "auto"
    assert "no válido" in capsys.readouterr().out.casefold()
    assert atlas.ai_runtime.registry.as_dict()["external"]["enabled"] is False


def test_selector_is_scoped_by_channel_session_and_user():
    manager = ConversationManager()
    manager.begin_turn(channel="cli", session_id="one", authenticated_identity="Alex")
    manager.set_ai_override("deep")
    manager.begin_turn(channel="telegram", session_id="two", authenticated_identity="Alex")
    assert manager.get_ai_override() == "auto"
    manager.set_ai_override("fast")
    manager.begin_turn(channel="cli", session_id="one", authenticated_identity="Alex")
    assert manager.get_ai_override() == "deep"


def test_ai_status_reports_trace_without_private_reasoning(capsys):
    atlas = AtlasStub()
    context.atlas = atlas
    atlas.last_ai_trace = SimpleNamespace(
        final_role=SimpleNamespace(value="reasoning"), model="qwen2.5:14b",
        fallback=False, latency_seconds=1.234,
    )
    ai_status.execute()
    output = capsys.readouterr().out.casefold()
    assert "reasoning" in output and "qwen2.5:14b" in output
    assert "fallback: no" in output and "1.234" in output
    assert "chain" not in output and "thinking" not in output


def test_ai_help_topic_command_and_search_are_useful():
    user = {
        "name": "Alex", "role": "owner", "is_admin": True, "is_owner": True,
        "profile_exists": True, "permissions": (), "own_bot": True,
    }
    for request in ("ayuda ia", "ayuda modelo", "ayuda modelo ia"):
        result = render_help_for_user(user, channel="telegram", request_text=request)
        assert "modelo ia" in result.casefold()
        assert "estado ia" in result.casefold()
    detail = render_help_for_user(user, channel="cli", request_text="ayuda estado ia")
    assert "última ruta" in detail.casefold()
    names = {entry.name for entry in search_entries("modelo ia")}
    assert "modelo ia" in names
    index = render_help_for_user(user, channel="telegram", request_text="ayuda")
    assert "categorías" in index.casefold() and "ayuda todo" in index.casefold()
    full = render_help_for_user(user, channel="telegram", request_text="ayuda todo")
    assert "modelo ia" in full.casefold() and "reinicia telegram" in full.casefold()
    chunks = split_message(full)
    assert len(chunks) > 1
    assert all(len(chunk) <= TELEGRAM_SAFE_CHUNK for chunk in chunks)
    assert all("<b>" not in chunk and "<code>" not in chunk for chunk in chunks)


def test_natural_selector_phrases_use_the_same_command_handler():
    class CommandAtlas(AtlasStub, AtlasCommandsMixin):
        def __init__(self):
            AtlasStub.__init__(self)
            self.guest_sessions = SimpleNamespace(get=lambda: None)

    atlas = CommandAtlas()
    context.atlas = atlas
    for phrase, expected in (
        ("modelo ia fast", "fast"),
        ("usar ia reasoning", "reasoning"),
        ("usa modelo deep", "deep"),
        ("cambia ia a fast", "fast"),
        ("vuelve a ia automática", "auto"),
    ):
        assert atlas._handle_command(phrase, normalize_text(phrase)) is True
        assert atlas.conversation_manager.get_ai_override() == expected
