"""Orquestación segura de propuestas y escrituras confirmadas de memoria."""

from dataclasses import replace
from pathlib import Path
from typing import Any

from identity.relationship import PERSON_ENTITY
from knowledge.fragment import KnowledgeFragment
from knowledge.privacy import KnowledgePrivacyFilter, Sensitivity
from memory.memory_manager import MemoryManager
from memory.workflow.audit import MemoryAuditLog
from memory.workflow.detector import CandidateDetector, normalize
from memory.workflow.models import CandidateResult, MemoryProposal
from memory.workflow.store import MemoryProposalStore


class MemoryWorkflowService:
    """Coordina detección, permisos, confirmación, persistencia y auditoría."""

    def __init__(
        self,
        memory_manager: MemoryManager,
        *,
        data_folder: Path | str,
        detector: CandidateDetector | None = None,
        proposal_store: MemoryProposalStore | None = None,
        audit_log: MemoryAuditLog | None = None,
        people_manager=None,
        relationship_engine=None,
    ) -> None:
        root = Path(data_folder)
        self.memory = memory_manager
        self.detector = detector or CandidateDetector()
        self.proposals = proposal_store or MemoryProposalStore(root / "proposals.json")
        self.audit = audit_log or MemoryAuditLog(root / "audit.jsonl")
        self.people_manager = people_manager
        self.relationship_engine = relationship_engine
        self.privacy_filter = KnowledgePrivacyFilter()

    @staticmethod
    def _has(permissions: set[str] | frozenset[str], permission: str) -> bool:
        return permission.casefold() in {item.casefold() for item in permissions}

    def _require(self, permissions: set[str] | frozenset[str], permission: str) -> None:
        if not self._has(permissions, permission):
            raise PermissionError(f"Falta el permiso {permission}.")

    def _same_key_memory(self, user_id: str, candidate: CandidateResult) -> dict | None:
        key = candidate.metadata.get("memory_key")
        if not key:
            return None
        for memory in reversed(self.memory.list_memories(owner=user_id)):
            if memory.get("memory_key") == key:
                return memory
        return None

    def _memory_sensitivity(self, memory: dict) -> str:
        normalized_content = normalize(memory.get("content", ""))
        if any(
            marker in normalized_content
            for marker in (
                "dni", "nie", "direccion", "telefono", "correo", "iban",
                "nomina", "diagnostico", "historial medico", "medicacion",
                "password", "contrasena", "token", "api key", "cvv",
            )
        ):
            return "sensitive"
        fragment = KnowledgeFragment(
            source_type="memory",
            source_id=str(memory.get("id", "unknown")),
            title="Memoria personal",
            content=str(memory.get("content", "")) or "[sin contenido]",
            score=1.0,
            metadata={"sensitivity": memory.get("sensitivity", "")},
            sensitive=str(memory.get("sensitivity", "normal")) != "normal",
        )
        return (
            "normal"
            if self.privacy_filter.classify(fragment) is Sensitivity.NONE
            else "sensitive"
        )

    def propose(
        self,
        *,
        user_id: str,
        source_text: str,
        permissions: set[str] | frozenset[str],
        session_id: str | None = None,
        channel: str = "cli",
    ) -> dict[str, Any]:
        self._require(permissions, "memory.propose")
        candidate = self.detector.detect(source_text)
        if candidate is None:
            return {"status": "not_candidate", "message": "No se ha creado ninguna propuesta."}

        duplicate = self.memory.find_exact_memory(owner=user_id, content=candidate.content)
        if duplicate is not None:
            return {
                "status": "duplicate",
                "message": "Eso ya está guardado en tu memoria.",
                "memory_id": duplicate["id"],
            }

        target = self._same_key_memory(user_id, candidate)
        operation = "update" if target else (
            "relationship" if candidate.category == "relationship" else "create"
        )
        proposal = self.proposals.create(
            user_id=user_id,
            source_text=source_text,
            candidate=candidate,
            operation=operation,
            session_id=session_id,
            target_memory_id=target.get("id") if target else None,
            metadata={"channel": channel, "previous_value": target.get("content") if target else None},
        )
        if target:
            message = (
                f"Ya tengo guardado: «{target['content']}». "
                f"¿Quieres sustituirlo por «{candidate.content}»?"
            )
        elif candidate.reinforced_confirmation:
            message = (
                "Esto contiene información sensible. ¿Confirmas expresamente que quieres "
                f"guardar «{candidate.content}» en tu memoria privada?"
            )
        else:
            message = f"Parece útil recordar: «{candidate.content}». ¿Quieres que lo guarde?"
        return {"status": "pending", "message": message, "proposal": proposal.to_dict()}

    def propose_update(
        self,
        *,
        user_id: str,
        memory_id: str,
        new_content: str,
        source_text: str,
        permissions: set[str] | frozenset[str],
        session_id: str | None = None,
    ) -> dict[str, Any]:
        self._require(permissions, "memory.update")
        current = self.memory.get_memory_by_id(memory_id, owner=user_id)
        if current is None:
            return {"status": "not_found", "message": "No se ha encontrado ese recuerdo."}
        detected = self.detector.detect(f"Recuerda que {new_content}")
        if detected is None:
            detected = CandidateResult(new_content.strip(), "other", 1.0)
        proposal = self.proposals.create(
            user_id=user_id,
            source_text=source_text,
            candidate=detected,
            operation="update",
            session_id=session_id,
            target_memory_id=memory_id,
            metadata={"previous_value": current["content"]},
        )
        return {
            "status": "pending",
            "message": f"Cambiaré «{current['content']}» por «{new_content.strip()}». ¿Confirmas?",
            "proposal": proposal.to_dict(),
        }

    def propose_delete(
        self,
        *,
        user_id: str,
        query: str,
        permissions: set[str] | frozenset[str],
        session_id: str | None = None,
    ) -> dict[str, Any]:
        self._require(permissions, "memory.delete")
        matches = self.memory.find_memories(owner=user_id, query=query, limit=10)
        if not matches:
            return {"status": "not_found", "message": "No he encontrado un recuerdo coincidente."}
        if len(matches) > 1:
            selection = self.proposals.create(
                user_id=user_id,
                source_text="delete_selection",
                candidate=CandidateResult(
                    content="Selección pendiente de recuerdo",
                    category="other",
                    confidence=1.0,
                ),
                operation="delete_selection",
                session_id=session_id,
                metadata={"candidate_ids": [item["id"] for item in matches]},
            )
            return {
                "status": "selection_required",
                "message": "Hay varios recuerdos. Indica uno antes de eliminar nada.",
                "candidates": [
                    {
                        "number": index,
                        "memory_id": item["id"],
                        "content": (
                            "[DATO SENSIBLE PROTEGIDO]"
                            if self._memory_sensitivity(item) != "normal"
                            else item["content"]
                        ),
                    }
                    for index, item in enumerate(matches, 1)
                ],
                "selection_id": selection.proposal_id,
            }
        target = matches[0]
        sensitivity = self._memory_sensitivity(target)
        candidate = CandidateResult(
            target["content"],
            target.get("category", "other"),
            1.0,
            sensitivity=sensitivity,
            reinforced_confirmation=sensitivity != "normal",
        )
        proposal = self.proposals.create(
            user_id=user_id,
            source_text=f"delete:{query}",
            candidate=candidate,
            operation="delete",
            session_id=session_id,
            target_memory_id=target["id"],
        )
        return {
            "status": "pending",
            "message": f"He encontrado «{target['content']}». ¿Confirmas que quieres eliminarlo?",
            "proposal": proposal.to_dict(),
        }

    def select_delete_candidate(
        self,
        *,
        user_id: str,
        proposal_id: str,
        selection: int,
        permissions: set[str] | frozenset[str],
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Convierte una selección múltiple en una propuesta de borrado concreta."""

        self._require(permissions, "memory.delete")
        proposal = self.proposals.get(
            proposal_id,
            user_id=user_id,
            session_id=session_id,
            include_closed=False,
        )
        if proposal is None or proposal.operation != "delete_selection":
            return {"status": "not_found", "message": "No hay una selección de borrado pendiente."}
        candidate_ids = list(proposal.metadata.get("candidate_ids", []))
        if selection < 1 or selection > len(candidate_ids):
            return {"status": "invalid_selection", "message": "La selección no corresponde a ningún recuerdo."}
        target = self.memory.get_memory_by_id(candidate_ids[selection - 1], owner=user_id)
        if target is None:
            return {"status": "not_found", "message": "Ese recuerdo ya no existe."}
        sensitivity = self._memory_sensitivity(target)
        selected = replace(
            proposal,
            operation="delete",
            target_memory_id=str(target["id"]),
            content=str(target["content"]),
            category=str(target.get("category", "other")),
            sensitivity=sensitivity,
            reinforced_confirmation=sensitivity != "normal",
            metadata={"selected_number": selection},
            version=proposal.version + 1,
        )
        self.proposals.replace(selected)
        shown = "[DATO SENSIBLE PROTEGIDO]" if sensitivity != "normal" else selected.content
        return {
            "status": "pending",
            "message": f"Has seleccionado «{shown}». ¿Confirmas que quieres eliminarlo?",
            "proposal": selected.to_dict(),
        }

    def update_proposal(
        self,
        *,
        user_id: str,
        proposal_id: str,
        content: str,
        permissions: set[str] | frozenset[str],
        session_id: str | None = None,
    ) -> dict[str, Any]:
        self._require(permissions, "memory.propose")
        if not content.strip():
            return {"status": "invalid", "message": "El contenido final no puede estar vacío."}
        proposal = self.proposals.update_content(
            proposal_id,
            user_id=user_id,
            session_id=session_id,
            content=content,
        )
        return {
            "status": "pending",
            "message": f"La versión final será «{proposal.content}». ¿Quieres guardarla?",
            "proposal": proposal.to_dict(),
        }

    def reject(
        self,
        *,
        user_id: str,
        proposal_id: str,
        permissions: set[str] | frozenset[str],
        session_id: str | None = None,
    ) -> dict[str, Any]:
        self._require(permissions, "memory.propose")
        proposal = self.proposals.get(
            proposal_id,
            user_id=user_id,
            session_id=session_id,
        )
        if proposal is None:
            return {"status": "not_found", "message": "La propuesta no existe."}
        if proposal.status != "pending":
            return {"status": proposal.status, "message": "La propuesta ya estaba cerrada."}
        self.proposals.close(
            proposal_id,
            user_id=user_id,
            session_id=session_id,
            status="rejected",
            minimize_content=proposal.sensitivity != "normal",
        )
        self.audit.record(
            user_id=user_id,
            action="rejected",
            memory_id=None,
            proposal_id=proposal_id,
            sensitive=proposal.sensitivity != "normal",
        )
        return {"status": "rejected", "message": "No guardaré esa información."}

    def _write_relationship(self, proposal: MemoryProposal) -> str:
        if self.people_manager is None or self.relationship_engine is None:
            raise RuntimeError("El sistema estructurado de relaciones no está disponible.")
        owner = self.people_manager.find_person_by_user_profile(proposal.user_id)
        target = self.people_manager.find_person_by_name(str(proposal.metadata.get("target_name", "")))
        if owner is None or target is None:
            raise LookupError("No se han podido resolver las personas de la relación.")
        relationship, _ = self.relationship_engine.create_relationship(
            source_entity_id=owner.id,
            source_entity_type=PERSON_ENTITY,
            relationship_type=str(proposal.metadata["relationship_type"]),
            target_entity_id=target.id,
            target_entity_type=PERSON_ENTITY,
            confirmed=True,
            information_source="confirmed_conversation",
            registered_by=proposal.user_id,
            notes=f"proposal:{proposal.proposal_id}",
        )
        if relationship is None:
            raise RuntimeError("No se pudo guardar la relación verificada.")
        return relationship.id

    def confirm(
        self,
        *,
        user_id: str,
        proposal_id: str,
        permissions: set[str] | frozenset[str],
        reinforced: bool = False,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        proposal = self.proposals.get(
            proposal_id,
            user_id=user_id,
            session_id=session_id,
            include_closed=True,
        )
        if proposal is None:
            return {
                "status": "not_found",
                "message": "La propuesta no existe en esta sesión o pertenece a otro usuario.",
            }
        if proposal.status == "confirmed":
            return {
                "status": "confirmed",
                "message": "La propuesta ya estaba confirmada; no se ha duplicado.",
                "result_id": proposal.result_id,
            }
        if proposal.status not in {"pending", "processing"}:
            return {"status": proposal.status, "message": "La propuesta ya no está pendiente."}
        if proposal.operation == "delete_selection":
            return {
                "status": "selection_required",
                "message": "Debes seleccionar un recuerdo antes de confirmar el borrado.",
            }

        required = {
            "create": "memory.write",
            "relationship": "memory.write",
            "update": "memory.update",
            "delete": "memory.delete",
        }[proposal.operation]
        self._require(permissions, required)
        if proposal.reinforced_confirmation:
            self._require(permissions, "memory.sensitive.write")
            if not reinforced:
                return {
                    "status": "reinforced_confirmation_required",
                    "message": "Se necesita una confirmación expresa reforzada.",
                }

        proposal = self.proposals.mark_processing(
            proposal_id,
            user_id=user_id,
            session_id=session_id,
        )

        sensitive = proposal.sensitivity != "normal"
        previous = proposal.metadata.get("previous_value")
        result_id = proposal.result_id
        action = "created"

        # Recupera una operación terminada si el proceso falló antes de cerrar
        # la propuesta. proposal_id funciona como clave idempotente.
        if result_id is None and proposal.operation == "create":
            stored = next(
                (
                    item
                    for item in self.memory.list_memories(owner=user_id)
                    if item.get("proposal_id") == proposal.proposal_id
                ),
                None,
            )
            if stored is not None:
                result_id = str(stored["id"])
        elif result_id is None and proposal.operation == "update":
            stored = self.memory.get_memory_by_id(
                str(proposal.target_memory_id),
                owner=user_id,
            )
            if stored is not None and stored.get("proposal_id") == proposal.proposal_id:
                result_id = str(stored["id"])
            action = "updated"
        elif result_id is None and proposal.operation == "delete":
            stored = self.memory.get_memory_by_id(
                str(proposal.target_memory_id),
                owner=user_id,
            )
            if stored is None:
                result_id = str(proposal.target_memory_id)
            action = "deleted"

        if result_id is None and proposal.operation == "relationship":
            result_id = self._write_relationship(proposal)
            action = "created"
        elif result_id is None and proposal.operation == "create":
            metadata = {
                "category": proposal.category,
                "sensitivity": proposal.sensitivity,
                "temporal_scope": proposal.temporal_scope,
                "proposal_id": proposal.proposal_id,
                "confirmed": True,
                "source": "confirmed_conversation",
                "source_text": "[DATO SENSIBLE OMITIDO]" if sensitive else proposal.source_text,
                **proposal.metadata,
            }
            if not self.memory.remember(user_id, proposal.content, "private", metadata=metadata):
                raise RuntimeError("No se pudo persistir el recuerdo.")
            stored = self.memory.find_exact_memory(owner=user_id, content=proposal.content)
            result_id = str(stored["id"])
            action = "created"
        elif result_id is None and proposal.operation == "update":
            old = self.memory.update_memory(
                memory_id=str(proposal.target_memory_id),
                owner=user_id,
                content=proposal.content,
                metadata={
                    "proposal_id": proposal.proposal_id,
                    "category": proposal.category,
                    "sensitivity": proposal.sensitivity,
                    "temporal_scope": proposal.temporal_scope,
                    "source": "confirmed_conversation",
                },
            )
            if old is None:
                raise LookupError("El recuerdo que se quería actualizar ya no existe.")
            previous = old.get("content")
            result_id = str(proposal.target_memory_id)
            action = "updated"
        elif result_id is None:
            old = self.memory.delete_memory(memory_id=str(proposal.target_memory_id), owner=user_id)
            if old is None:
                raise LookupError("El recuerdo que se quería eliminar ya no existe.")
            previous = old.get("content")
            result_id = str(proposal.target_memory_id)
            action = "deleted"

        self.proposals.set_result(
            proposal_id,
            user_id=user_id,
            session_id=session_id,
            result_id=result_id,
        )
        if not self.audit.has_event(
            user_id=user_id,
            proposal_id=proposal_id,
            action=action,
        ):
            self.audit.record(
                user_id=user_id,
                action=action,
                memory_id=result_id,
                proposal_id=proposal_id,
                previous_value=str(previous) if previous else None,
                new_value=None if action == "deleted" else proposal.content,
                sensitive=sensitive,
                metadata={"category": proposal.category, "operation": proposal.operation},
            )
        self.proposals.close(
            proposal_id,
            user_id=user_id,
            session_id=session_id,
            status="confirmed",
            result_id=result_id,
            minimize_content=sensitive or proposal.operation == "delete",
        )
        return {"status": "confirmed", "message": "Cambio de memoria confirmado.", "result_id": result_id}

    def read(
        self,
        *,
        user_id: str,
        query: str,
        permissions: set[str] | frozenset[str],
        allow_sensitive: bool = False,
    ) -> dict[str, Any]:
        self._require(permissions, "memory.read")
        if allow_sensitive:
            self._require(permissions, "memory.sensitive.read")
        memories = (
            self.memory.find_memories(owner=user_id, query=query, limit=10)
            if query.strip()
            else self.memory.list_memories(owner=user_id)
        )
        selected: list[dict] = []
        excluded = 0
        for memory in memories:
            if self._memory_sensitivity(memory) != "normal":
                if not allow_sensitive:
                    excluded += 1
                    continue
                protected = memory.copy()
                protected["content"] = "[DATO SENSIBLE PROTEGIDO]"
                selected.append(protected)
            else:
                selected.append(memory)
        return {
            "status": "ok",
            "memories": selected,
            "excluded_sensitive": excluded,
        }
