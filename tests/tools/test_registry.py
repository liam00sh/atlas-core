import pytest

from tools.registry import ToolRegistry
from tools.system_status import SystemStatusTool
from tools.exceptions import ToolRegistrationError


def test_registry_registers_and_finds_tool() -> None:
    registry = ToolRegistry()
    tool = SystemStatusTool()

    registry.register(tool)

    assert registry.count == 1
    assert registry.get("system.status") is tool
    assert registry.find_by_capability("system.status.read") == [tool]


def test_registry_rejects_duplicates() -> None:
    registry = ToolRegistry()
    registry.register(SystemStatusTool())

    with pytest.raises(ToolRegistrationError):
        registry.register(SystemStatusTool())
