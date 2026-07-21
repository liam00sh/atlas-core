"""Pruebas del ciclo de vida controlado de Sprint 13."""

from datetime import UTC, datetime, timedelta

import pytest

from memory.memory_manager import MemoryManager
from memory.workflow.detector import CandidateDetector
from memory.workflow.service import MemoryWorkflowService
from memory.workflow.store import MemoryProposalStore


FULL = {
    "memory.read", "memory.propose", "memory.write", "memory.update",
    "memory.delete", "memory.audit.read",
}


@pytest.fixture
def workflow(tmp_path):
    manager = MemoryManager(tmp_path / "memory")
    return MemoryWorkflowService(manager, data_folder=tmp_path / "workflow")


@pytest.mark.parametrize(
    "text",
    [
        "¿Qué hora es?",
        "Quizá algún día compre otro coche.",
        "Supongamos que vivo en Madrid.",
        "En una película, el protagonista se llama Pedro.",
        "Mi amigo dice que su color favorito es rojo.",
        "Cuéntame una historia.",
    ],
)
def test_detector_avoids_false_positives(text):
    assert CandidateDetector().detect(text) is None


def test_proposal_does_not_write_and_is_isolated(workflow):
    result = workflow.propose(
        user_id="Liam", source_text="Mi color favorito es el azul",
        permissions=FULL, session_id="one",
    )
    assert result["status"] == "pending"
    assert workflow.memory.count_memories("Liam") == 0
    proposal_id = result["proposal"]["proposal_id"]
    assert workflow.proposals.get(proposal_id, user_id="Saray") is None
    assert workflow.proposals.latest_pending("Saray") is None


def test_confirm_is_idempotent_and_preserves_provenance(workflow):
    proposed = workflow.propose(
        user_id="Liam", source_text="Recuerda que mi color favorito es el azul",
        permissions=FULL,
    )
    proposal_id = proposed["proposal"]["proposal_id"]
    first = workflow.confirm(user_id="Liam", proposal_id=proposal_id, permissions=FULL)
    second = workflow.confirm(user_id="Liam", proposal_id=proposal_id, permissions=FULL)
    assert first["status"] == second["status"] == "confirmed"
    assert workflow.memory.count_memories("Liam") == 1
    memory = workflow.memory.list_memories(owner="Liam")[0]
    assert memory["proposal_id"] == proposal_id
    assert memory["source"] == "confirmed_conversation"
    assert workflow.read(user_id="Liam", query="color", permissions=FULL)["memories"]


def test_reject_never_writes(workflow):
    proposed = workflow.propose(
        user_id="Liam", source_text="Trabajo con Linux", permissions=FULL,
    )
    result = workflow.reject(
        user_id="Liam", proposal_id=proposed["proposal"]["proposal_id"], permissions=FULL,
    )
    assert result["status"] == "rejected"
    assert workflow.memory.count_memories("Liam") == 0
    assert workflow.audit.list_for_user("Liam")[-1]["action"] == "rejected"


def test_exact_duplicate_is_not_proposed(workflow):
    workflow.memory.remember("Liam", "Mi color favorito es el azul", "private")
    result = workflow.propose(
        user_id="Liam", source_text="Mi color favorito es el azul", permissions=FULL,
    )
    assert result["status"] == "duplicate"
    assert workflow.proposals.latest_pending("Liam") is None


def test_conflict_becomes_confirmable_update(workflow):
    workflow.memory.remember(
        "Liam", "Mi color favorito es el azul", "private",
        metadata={"memory_key": "favorite_color"},
    )
    proposed = workflow.propose(
        user_id="Liam", source_text="Mi color favorito es el verde", permissions=FULL,
    )
    assert proposed["proposal"]["operation"] == "update"
    assert "azul" in proposed["message"]
    workflow.confirm(
        user_id="Liam", proposal_id=proposed["proposal"]["proposal_id"], permissions=FULL,
    )
    contents = [item["content"] for item in workflow.memory.list_memories(owner="Liam")]
    assert contents == ["Mi color favorito es el verde"]
    assert workflow.audit.list_for_user("Liam")[-1]["action"] == "updated"


def test_update_proposal_changes_only_pending_version(workflow):
    proposed = workflow.propose(
        user_id="Liam", source_text="Mi color favorito es el azul", permissions=FULL,
    )
    updated = workflow.update_proposal(
        user_id="Liam", proposal_id=proposed["proposal"]["proposal_id"],
        content="Mi color favorito es el verde", permissions=FULL,
    )
    assert updated["proposal"]["version"] == 2
    assert workflow.memory.count_memories("Liam") == 0


def test_delete_requires_proposal_and_confirmation(workflow):
    workflow.memory.remember("Liam", "Mi color favorito es el azul", "private")
    proposed = workflow.propose_delete(
        user_id="Liam", query="color favorito", permissions=FULL,
    )
    assert workflow.memory.count_memories("Liam") == 1
    workflow.confirm(
        user_id="Liam", proposal_id=proposed["proposal"]["proposal_id"], permissions=FULL,
    )
    assert workflow.memory.count_memories("Liam") == 0
    assert workflow.audit.list_for_user("Liam")[-1]["action"] == "deleted"


def test_delete_requires_selection_when_multiple(workflow):
    workflow.memory.remember("Liam", "Trabajo con Linux", "private")
    workflow.memory.remember("Liam", "Trabajo con Windows", "private")
    result = workflow.propose_delete(user_id="Liam", query="trabajo", permissions=FULL)
    assert result["status"] == "selection_required"
    assert len(result["candidates"]) == 2
    selection = workflow.proposals.latest_pending("Liam")
    assert selection is not None
    assert selection.operation == "delete_selection"
    assert selection.target_memory_id is None


def test_cross_user_update_and_delete_are_impossible(workflow):
    workflow.memory.remember("Liam", "Vivo en Beneixama", "private")
    memory_id = workflow.memory.list_memories(owner="Liam")[0]["id"]
    assert workflow.memory.update_memory(
        memory_id=memory_id, owner="Saray", content="Vivo en Madrid"
    ) is None
    assert workflow.memory.delete_memory(memory_id=memory_id, owner="Saray") is None


def test_sensitive_memory_needs_permission_and_reinforced_confirmation(workflow):
    proposed = workflow.propose(
        user_id="Liam", source_text="Recuerda que mi diagnóstico es privado", permissions=FULL,
    )
    proposal_id = proposed["proposal"]["proposal_id"]
    with pytest.raises(PermissionError):
        workflow.confirm(
            user_id="Liam", proposal_id=proposal_id,
            permissions=FULL, reinforced=True,
        )
    allowed = FULL | {"memory.sensitive.write"}
    result = workflow.confirm(
        user_id="Liam", proposal_id=proposal_id, permissions=allowed, reinforced=False,
    )
    assert result["status"] == "reinforced_confirmation_required"
    result = workflow.confirm(
        user_id="Liam", proposal_id=proposal_id, permissions=allowed, reinforced=True,
    )
    assert result["status"] == "confirmed"
    audit_text = workflow.audit.path.read_text(encoding="utf-8")
    assert "diagnóstico" not in audit_text
    assert "DATO SENSIBLE OMITIDO" in audit_text


@pytest.mark.parametrize(
    "text", [
        "Recuerda que mi contraseña es atlas123",
        "Guarda que mi token: abc123",
        "Apunta que mi CVV es 999",
    ],
)
def test_secrets_are_never_proposed(workflow, text):
    result = workflow.propose(user_id="Liam", source_text=text, permissions=FULL)
    assert result["status"] == "not_candidate"
    assert not workflow.proposals.path.exists()


def test_expired_proposal_cannot_be_confirmed(tmp_path):
    now = datetime(2026, 7, 19, tzinfo=UTC)
    current = {"value": now}
    store = MemoryProposalStore(
        tmp_path / "proposals.json", expiration_minutes=1,
        clock=lambda: current["value"],
    )
    workflow = MemoryWorkflowService(
        MemoryManager(tmp_path / "memory"), data_folder=tmp_path / "workflow",
        proposal_store=store,
    )
    proposed = workflow.propose(
        user_id="Liam", source_text="Trabajo con Linux", permissions=FULL,
    )
    current["value"] = now + timedelta(minutes=2)
    result = workflow.confirm(
        user_id="Liam", proposal_id=proposed["proposal"]["proposal_id"], permissions=FULL,
    )
    assert result["status"] == "expired"
    assert workflow.memory.count_memories("Liam") == 0


def test_insufficient_permissions_are_enforced(workflow):
    with pytest.raises(PermissionError):
        workflow.propose(
            user_id="Visitante", source_text="Trabajo con Linux", permissions=set(),
        )
    with pytest.raises(PermissionError):
        workflow.read(user_id="Visitante", query="", permissions=set())


@pytest.mark.parametrize("operation", ["confirm", "reject", "update"])
def test_final_operations_enforce_same_session(workflow, operation):
    proposed = workflow.propose(
        user_id="Liam",
        source_text="Mi color favorito es el azul",
        permissions=FULL,
        session_id="session-a",
    )
    proposal_id = proposed["proposal"]["proposal_id"]
    if operation == "confirm":
        result = workflow.confirm(
            user_id="Liam", proposal_id=proposal_id, permissions=FULL,
            session_id="session-b",
        )
    elif operation == "reject":
        result = workflow.reject(
            user_id="Liam", proposal_id=proposal_id, permissions=FULL,
            session_id="session-b",
        )
    else:
        with pytest.raises(LookupError):
            workflow.update_proposal(
                user_id="Liam", proposal_id=proposal_id,
                content="Mi color favorito es el verde", permissions=FULL,
                session_id="session-b",
            )
        result = {"status": "not_found"}
    assert result["status"] == "not_found"
    assert workflow.memory.count_memories("Liam") == 0
    assert workflow.proposals.latest_pending("Liam", "session-a") is not None


def test_general_read_excludes_legacy_sensitive_memory(workflow):
    workflow.memory.remember("Liam", "Mi DNI es 12345678Z", "private")
    workflow.memory.remember("Liam", "Trabajo con Linux", "private")
    result = workflow.read(user_id="Liam", query="", permissions=FULL)
    assert [item["content"] for item in result["memories"]] == ["Trabajo con Linux"]
    assert result["excluded_sensitive"] == 1


def test_sensitive_read_requires_separate_permission_and_masks(workflow):
    workflow.memory.remember("Liam", "Mi diagnóstico es privado", "private")
    with pytest.raises(PermissionError):
        workflow.read(
            user_id="Liam", query="diagnóstico", permissions=FULL,
            allow_sensitive=True,
        )
    result = workflow.read(
        user_id="Liam", query="diagnóstico",
        permissions=FULL | {"memory.sensitive.read"},
        allow_sensitive=True,
    )
    assert result["memories"][0]["content"] == "[DATO SENSIBLE PROTEGIDO]"


def test_confirm_recovers_after_write_before_proposal_result(workflow, monkeypatch):
    proposed = workflow.propose(
        user_id="Liam", source_text="Trabajo con Linux", permissions=FULL,
        session_id="recoverable",
    )
    proposal_id = proposed["proposal"]["proposal_id"]
    original_set_result = workflow.proposals.set_result
    calls = {"count": 0}

    def fail_once(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("simulated crash")
        return original_set_result(*args, **kwargs)

    monkeypatch.setattr(workflow.proposals, "set_result", fail_once)
    with pytest.raises(RuntimeError):
        workflow.confirm(
            user_id="Liam", proposal_id=proposal_id, permissions=FULL,
            session_id="recoverable",
        )
    assert workflow.memory.count_memories("Liam") == 1

    result = workflow.confirm(
        user_id="Liam", proposal_id=proposal_id, permissions=FULL,
        session_id="recoverable",
    )
    assert result["status"] == "confirmed"
    assert workflow.memory.count_memories("Liam") == 1
    events = [
        item for item in workflow.audit.list_for_user("Liam")
        if item["proposal_id"] == proposal_id
    ]
    assert len(events) == 1
