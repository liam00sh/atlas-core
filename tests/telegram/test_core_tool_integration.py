from __future__ import annotations

from datetime import UTC, datetime

from telegram_interface.core_adapter import AtlasCoreAdapter
from telegram_interface.identity_linker import TelegramIdentityLinker
from telegram_interface.models import TelegramAccountState, TelegramRequestContext, TelegramUser
from telegram_interface.storage import TelegramStorage
from tools.context import ToolContext
from tools.atlas_adapter import AtlasToolAdapter
from tools.manager import ToolManager
from tools.registry import ToolRegistry
from tools.telegram_accounts import TelegramAccountTool
from core.atlas_users import AtlasUsersMixin
from ai.context.context_manager import AIContextManager


class FakeIdentityManager:
    def __init__(self, owner):
        self.owner = owner
        self.values = {"Liam": "daxter", "Saray": "coco"}
    def get_active_identity_name(self):
        return self.values[self.owner.user]
    def change_identity(self, value, save_preference=True):
        if value not in {"daxter", "coco"}:
            return False
        self.values[self.owner.user] = value
        return True


class FakeAtlas:
    def __init__(self):
        self.user = "Liam"
        self.session_id = "cli:default"
        self.identity_manager = FakeIdentityManager(self)
    def get_user(self):
        return self.user
    def change_user(self, user):
        self.user = user
        return True
    def process(self, text):
        print(f"{self.user}|{self.session_id}|{text}")
        return True


def context(user="Saray", session_id="telegram:1:2"):
    return TelegramRequestContext(
        channel="telegram", atlas_user_id=user, session_id=session_id,
        telegram_user_id="1", chat_id="2", message_id=3,
        timestamp=datetime.now(UTC), active_personality="coco",
        authentication_state=TelegramAccountState.LINKED,
        permissions=frozenset({"telegram.use"}),
    )


def test_core_adapter_uses_normal_process_and_restores_global_state():
    atlas = FakeAtlas()
    adapter = AtlasCoreAdapter(atlas)
    response = adapter.process("hola", context())
    assert response == "Saray|telegram:1:2|hola"
    assert atlas.user == "Liam"
    assert atlas.session_id == "cli:default"
    assert atlas.channel_request_context is None


def test_personality_change_is_persistent_per_user_and_restores_current_user():
    atlas = FakeAtlas()
    adapter = AtlasCoreAdapter(atlas)
    assert adapter.change_personality("Saray", "daxter") is True
    assert atlas.identity_manager.values["Saray"] == "daxter"
    assert atlas.identity_manager.values["Liam"] == "daxter"
    assert atlas.user == "Liam"


def test_local_tool_requires_permission_and_explicit_confirmation(tmp_path):
    storage = TelegramStorage(tmp_path / "state.json")
    linker = TelegramIdentityLinker(storage)
    code = linker.request_code(TelegramUser("1", "2"))
    tool = TelegramAccountTool(linker, user_exists=lambda user: user == "Liam")
    denied = tool.execute(
        tool.capabilities[0],
        {"code": code, "atlas_user_id": "Liam", "confirmed": True},
        ToolContext(requested_by="Saray", permissions=set()),
    )
    assert denied.success is False
    allowed = tool.execute(
        tool.capabilities[0],
        {"code": code, "atlas_user_id": "Liam", "confirmed": True},
        ToolContext(requested_by="Liam", permissions={"telegram.admin_link"}),
    )
    assert allowed.success is True
    assert allowed.data == {"atlas_user_id": "Liam", "linked": True}


def test_local_tool_rejects_missing_confirmation(tmp_path):
    tool = TelegramAccountTool(
        TelegramIdentityLinker(TelegramStorage(tmp_path / "state.json")),
        user_exists=lambda _: True,
    )
    try:
        tool.validate_arguments({})
    except ValueError as exc:
        assert "confirmacion explicita" in str(exc)
    else:
        raise AssertionError("Debia exigir confirmacion")


def test_tool_context_uses_telegram_channel_and_permission_intersection():
    atlas = FakeAtlas()
    atlas.get_name = lambda: "Daxter"
    atlas.can_use_tools = lambda: True
    atlas.can_access_internet = lambda: False
    atlas.channel_request_context = context("Liam")
    adapter = AtlasToolAdapter(
        ToolManager(ToolRegistry()),
        permission_resolver=lambda _atlas: {"telegram.use", "memory.read", "google.drive.read"},
    )
    built = adapter.build_context(atlas)
    assert built.channel == "telegram"
    assert built.permissions == {"telegram.use"}
    assert built.metadata["session_id"] == "telegram:1:2"


def test_telegram_authenticated_identity_cannot_switch_atlas_user():
    class GuardedAtlas(AtlasUsersMixin):
        channel_request_context = context("Liam")
        def get_user(self): return "Liam"
        def get_main_user(self): return "Liam"
    atlas = GuardedAtlas()
    assert atlas.change_user("Saray") is False


def test_telegram_non_main_user_cannot_return_to_main_user():
    class GuardedAtlas(AtlasUsersMixin):
        channel_request_context = context("Saray")
        def get_user(self): return "Saray"
        def get_main_user(self): return "Liam"
    atlas = GuardedAtlas()
    assert atlas.return_to_main_user() is None
    assert atlas.get_user() == "Saray"


def test_pending_confirmations_are_isolated_by_telegram_session():
    class State:
        pending_confirmation = None
    class SessionAtlas(FakeAtlas):
        def __init__(self):
            super().__init__()
            self.confirmations = State()
        def process(self, text):
            if text == "create":
                self.confirmations.pending_confirmation = {"action": "private"}
                print("created")
            else:
                print("pending" if self.confirmations.pending_confirmation else "empty")
    adapter = AtlasCoreAdapter(SessionAtlas())
    assert adapter.process("create", context("Liam", "telegram:a")) == "created"
    assert adapter.process("check", context("Liam", "telegram:b")) == "empty"
    assert adapter.process("check", context("Liam", "telegram:a")) == "pending"


def test_ai_context_is_isolated_from_cli_and_other_telegram_sessions():
    class SessionAtlas(FakeAtlas):
        def __init__(self):
            super().__init__()
            self.ai_contexts = {"liam": AIContextManager()}
            self.ai_context_max_messages = 10
        def process(self, text):
            current = self.ai_contexts[self.user.casefold()]
            print(len(current.messages))
            current.add_message("user", text)
    atlas = SessionAtlas()
    cli_context = atlas.ai_contexts["liam"]
    adapter = AtlasCoreAdapter(atlas)
    assert adapter.process("one", context("Liam", "telegram:a")) == "0"
    assert adapter.process("two", context("Liam", "telegram:a")) == "1"
    assert adapter.process("other", context("Liam", "telegram:b")) == "0"
    assert atlas.ai_contexts["liam"] is cli_context
    assert cli_context.messages == []
