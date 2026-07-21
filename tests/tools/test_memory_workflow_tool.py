"""Contrato de la herramienta de memoria controlada."""

from memory.memory_manager import MemoryManager
from memory.workflow.service import MemoryWorkflowService
from tools.capability import Capability
from tools.context import ToolContext
from tools.memory_write import MemoryWorkflowTool


PERMISSIONS = {
    "memory.read", "memory.propose", "memory.write", "memory.update", "memory.delete",
}


def test_tool_proposes_then_confirms_without_double_write(tmp_path):
    service = MemoryWorkflowService(
        MemoryManager(tmp_path / "memory"), data_folder=tmp_path / "workflow"
    )
    tool = MemoryWorkflowTool(service)
    context = ToolContext(requested_by="Liam", permissions=PERMISSIONS)
    proposed = tool.execute(
        Capability("memory.propose"), {"text": "Mi color favorito es el azul"}, context
    )
    assert proposed.success
    assert service.memory.count_memories("Liam") == 0
    proposal_id = proposed.data["proposal"]["proposal_id"]
    first = tool.execute(
        Capability("memory.confirm"), {"proposal_id": proposal_id}, context
    )
    second = tool.execute(
        Capability("memory.confirm"), {"proposal_id": proposal_id}, context
    )
    assert first.success and second.success
    assert service.memory.count_memories("Liam") == 1


def test_tool_converts_permission_failure_to_structured_result(tmp_path):
    service = MemoryWorkflowService(
        MemoryManager(tmp_path / "memory"), data_folder=tmp_path / "workflow"
    )
    tool = MemoryWorkflowTool(service)
    result = tool.execute(
        Capability("memory.propose"),
        {"text": "Trabajo con Linux"},
        ToolContext(requested_by="Visitante", permissions=set()),
    )
    assert not result.success
    assert result.error == "permission_denied"
    assert "Linux" not in result.message

