"""Pruebas del controlador conversacional por usuario."""

import pytest

from memory.memory_manager import MemoryManager
from memory.workflow.conversation import MemoryWorkflowConversation
from memory.workflow.service import MemoryWorkflowService
from tools.capability import Capability
from tools.context import ToolContext
from tools.memory_write import MemoryWorkflowTool


PERMISSIONS = {
    "memory.read", "memory.propose", "memory.write", "memory.update",
    "memory.delete", "memory.audit.read",
}


class FakeAtlas:
    def __init__(self, service):
        self.memory_workflow_service = service
        self.memory = service.memory
        self.controller = MemoryWorkflowConversation()
        self.user = "Liam"
        self.session_id = "session-1"
        self.tool = MemoryWorkflowTool(service)

    def get_user(self):
        return self.user

    def execute_framework_tool(self, capability, *, arguments):
        return self.tool.execute(
            Capability(capability), arguments,
            ToolContext(requested_by=self.user, permissions=PERMISSIONS),
        )


def build(tmp_path):
    service = MemoryWorkflowService(
        MemoryManager(tmp_path / "memory"), data_folder=tmp_path / "workflow"
    )
    return FakeAtlas(service)


def test_explicit_request_and_exact_confirmation(tmp_path):
    atlas = build(tmp_path)
    proposed = atlas.controller.handle(atlas, "Recuerda que mi color favorito es el azul")
    assert proposed["handled"] and "¿" in proposed["message"]
    assert atlas.memory.count_memories("Liam") == 0
    confirmed = atlas.controller.handle(atlas, "Sí, guárdalo")
    assert confirmed["handled"]
    assert atlas.memory.count_memories("Liam") == 1


def test_ambiguous_answer_does_not_confirm(tmp_path):
    atlas = build(tmp_path)
    atlas.controller.handle(atlas, "Trabajo con Linux")
    result = atlas.controller.handle(atlas, "Puede ser")
    assert not result["handled"]
    assert atlas.memory.count_memories("Liam") == 0


def test_rejection_and_correction_before_save(tmp_path):
    atlas = build(tmp_path)
    atlas.controller.handle(atlas, "Mi color favorito es el azul")
    corrected = atlas.controller.handle(atlas, "Sí, pero cambia azul por verde")
    assert "verde" in corrected["message"]
    atlas.controller.handle(atlas, "Correcto")
    assert atlas.memory.list_memories(owner="Liam")[0]["content"].endswith("verde")

    atlas.controller.handle(atlas, "Trabajo con Linux")
    atlas.controller.handle(atlas, "No lo guardes")
    assert atlas.memory.count_memories("Liam") == 1


def test_pending_proposal_does_not_cross_users(tmp_path):
    atlas = build(tmp_path)
    atlas.controller.handle(atlas, "Trabajo con Linux")
    atlas.user = "Saray"
    result = atlas.controller.handle(atlas, "Sí")
    assert not result["handled"]
    assert atlas.memory.count_memories("Liam") == 0
    atlas.user = "Liam"
    atlas.controller.handle(atlas, "Sí")
    assert atlas.memory.count_memories("Liam") == 1


def test_pending_proposal_survives_controller_restart(tmp_path):
    atlas = build(tmp_path)
    atlas.controller.handle(atlas, "Vivo en Beneixama")
    atlas.controller = MemoryWorkflowConversation()
    atlas.controller.handle(atlas, "Sí")
    assert atlas.memory.count_memories("Liam") == 1


def test_natural_read_and_confirmed_delete(tmp_path):
    atlas = build(tmp_path)
    atlas.controller.handle(atlas, "Mi color favorito es el azul")
    atlas.controller.handle(atlas, "Sí")
    read = atlas.controller.handle(atlas, "¿Qué recuerdas sobre mi color?")
    assert "[MEMORIA]" in read["message"]
    proposed = atlas.controller.handle(atlas, "Olvida color favorito")
    assert "eliminarlo" in proposed["message"]
    atlas.controller.handle(atlas, "Sí")
    assert atlas.memory.count_memories("Liam") == 0


def test_existing_memory_correction_is_confirmable(tmp_path):
    atlas = build(tmp_path)
    atlas.memory.remember("Liam", "Mi color favorito es el azul", "private")
    proposed = atlas.controller.handle(
        atlas, "Mi color favorito ya no es azul, ahora es verde"
    )
    assert "Cambiaré" in proposed["message"]
    assert atlas.memory.list_memories(owner="Liam")[0]["content"].endswith("azul")
    atlas.controller.handle(atlas, "Sí")
    assert atlas.memory.list_memories(owner="Liam")[0]["content"].endswith("verde")


@pytest.mark.parametrize(
    ("answer", "expected"),
    [("El primero", "Linux"), ("Borra el número 2", "Windows"), ("Me refiero al tercero", "macOS")],
)
def test_multiple_delete_selection_has_natural_continuation(tmp_path, answer, expected):
    atlas = build(tmp_path)
    for content in ("Trabajo con Linux", "Trabajo con Windows", "Trabajo con macOS"):
        atlas.memory.remember("Liam", content, "private")
    choices = atlas.controller.handle(atlas, "Borra lo que recuerdas sobre trabajo")
    assert "1." in choices["message"] and "3." in choices["message"]
    selected = atlas.controller.handle(atlas, answer)
    assert expected in selected["message"]
    assert atlas.memory.count_memories("Liam") == 3
    atlas.controller.handle(atlas, "Sí")
    assert atlas.memory.count_memories("Liam") == 2


def test_provenance_uses_last_results_from_same_session(tmp_path):
    atlas = build(tmp_path)
    atlas.memory.remember(
        "Liam", "Trabajo con Linux", "private",
        metadata={"source": "confirmed_conversation"},
    )
    atlas.memory.remember(
        "Liam", "Mi coche es azul", "private",
        metadata={"source": "legacy_import"},
    )
    atlas.controller.handle(atlas, "¿Qué recuerdas sobre trabajo?")
    provenance = atlas.controller.handle(atlas, "¿De dónde recuerdas eso?")
    assert "Trabajo con Linux" in provenance["message"]
    assert "confirmed_conversation" in provenance["message"]
    assert "coche" not in provenance["message"]

    atlas.session_id = "other-session"
    other = atlas.controller.handle(atlas, "¿De dónde recuerdas eso?")
    assert "No hay un recuerdo concreto" in other["message"]
