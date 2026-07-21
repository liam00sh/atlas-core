"""
Pruebas del adaptador entre Atlas y el nuevo Tools Framework.
"""

from core.atlas import Atlas
from tools.atlas_adapter import AtlasToolAdapter
from tools.manager import ToolManager
from tools.registry import ToolRegistry
from tools.system_status import SystemStatusTool


class FakeAtlas:
    def __init__(self, tools_enabled: bool = True) -> None:
        self.tools_enabled = tools_enabled

    def get_user(self) -> str:
        return "Liam"

    def get_name(self) -> str:
        return "Daxter"

    def can_use_tools(self) -> bool:
        return self.tools_enabled

    def can_access_internet(self) -> bool:
        return False


class FakePerson:
    def __init__(self, status: str) -> None:
        self.status = status


class FakePeopleManager:
    def __init__(self, status: str | None) -> None:
        self.status = status

    def find_person_by_user_profile(self, user_profile: str):
        assert user_profile == "Liam"
        return FakePerson(self.status) if self.status is not None else None


def build_adapter() -> AtlasToolAdapter:
    registry = ToolRegistry()
    registry.register(SystemStatusTool())
    return AtlasToolAdapter(
        ToolManager(registry)
    )


def test_adapter_builds_safe_context() -> None:
    adapter = build_adapter()

    context = adapter.build_context(
        FakeAtlas(),
        channel="test",
        metadata={"source": "sprint_3"},
    )

    assert context.requested_by == "Liam"
    assert context.channel == "test"
    assert context.has_permission("system.status.read")
    assert context.metadata["assistant_name"] == "Daxter"
    assert context.metadata["source"] == "sprint_3"


def test_adapter_executes_registered_capability() -> None:
    result = build_adapter().execute(
        FakeAtlas(),
        "system.status.read",
        channel="test",
    )

    assert result.success is True
    assert result.tool_id == "system.status"
    assert result.capability == "system.status.read"
    assert result.data["requested_by"] == "Liam"


def test_adapter_blocks_execution_when_tools_are_disabled() -> None:
    result = build_adapter().execute(
        FakeAtlas(tools_enabled=False),
        "system.status.read",
    )

    assert result.success is False
    assert result.error == "tools_disabled"


def test_memory_permissions_require_structured_user_and_never_include_sensitive() -> None:
    adapter = build_adapter()
    registered = FakeAtlas()
    registered.people_manager = FakePeopleManager("user")
    context = adapter.build_context(registered)
    assert context.has_permission("memory.write")
    assert context.has_permission("memory.delete")
    assert not context.has_permission("memory.sensitive.write")

    visitor = FakeAtlas()
    visitor.people_manager = FakePeopleManager("guest")
    visitor_context = adapter.build_context(visitor)
    assert not visitor_context.has_permission("memory.read")
    assert not visitor_context.has_permission("memory.write")


def test_atlas_exposes_framework_adapter_methods() -> None:
    atlas = Atlas(ai_provider=None)

    assert isinstance(
        atlas.framework_tool_adapter,
        AtlasToolAdapter,
    )
    assert atlas.get_framework_tool_count() >= 1

    result = atlas.execute_framework_tool(
        "system.status.read",
        channel="test",
        metadata={"source": "atlas"},
    )

    assert result.success is True
    assert result.data["requested_by"] == atlas.get_user()
    assert result.data["channel"] == "test"
