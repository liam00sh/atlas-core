"""Persistencia atómica y aislada de propuestas de memoria."""

import json
import os
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from memory.workflow.models import CandidateResult, MemoryProposal


class MemoryProposalStore:
    """Mantiene propuestas por usuario y evita reutilizar confirmaciones."""

    def __init__(
        self,
        path: Path | str,
        *,
        expiration_minutes: int = 10,
        clock=None,
    ) -> None:
        self.path = Path(path)
        self.expiration_minutes = max(1, expiration_minutes)
        self.clock = clock or (lambda: datetime.now(UTC))

    def _load(self) -> list[MemoryProposal]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            return [MemoryProposal.from_dict(item) for item in data if isinstance(item, dict)]
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            # Una copia incompleta nunca debe tumbar Atlas ni autorizar una escritura.
            return []

    def _save(self, proposals: list[MemoryProposal]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with temporary.open("w", encoding="utf-8") as file:
                json.dump([item.to_dict() for item in proposals], file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary.exists():
                temporary.unlink(missing_ok=True)

    def create(
        self,
        *,
        user_id: str,
        source_text: str,
        candidate: CandidateResult,
        operation: str = "create",
        session_id: str | None = None,
        target_memory_id: str | None = None,
        metadata: dict | None = None,
    ) -> MemoryProposal:
        now = self.clock()
        proposal = MemoryProposal(
            proposal_id=uuid4().hex,
            user_id=user_id,
            content=candidate.content,
            category=candidate.category,
            source_text=source_text,
            confidence=candidate.confidence,
            sensitivity=candidate.sensitivity,
            temporal_scope=candidate.temporal_scope,
            created_at=now.isoformat(),
            expires_at=(now + timedelta(minutes=self.expiration_minutes)).isoformat(),
            metadata={**candidate.metadata, **(metadata or {})},
            operation=operation,
            session_id=session_id,
            target_memory_id=target_memory_id,
            reinforced_confirmation=candidate.reinforced_confirmation,
        )
        proposals = self._load()
        proposals.append(proposal)
        self._save(proposals)
        return proposal

    def get(
        self,
        proposal_id: str,
        *,
        user_id: str,
        session_id: str | None = None,
        include_closed: bool = True,
    ) -> MemoryProposal | None:
        self.expire()
        for proposal in self._load():
            if (
                proposal.proposal_id == proposal_id
                and proposal.user_id.casefold() == user_id.casefold()
                and proposal.session_id == session_id
            ):
                if include_closed or proposal.status == "pending":
                    return proposal
        return None

    def pending_for_user(self, user_id: str, session_id: str | None = None) -> list[MemoryProposal]:
        self.expire()
        return [
            item for item in self._load()
            if item.user_id.casefold() == user_id.casefold()
            and item.status in {"pending", "processing"}
            and item.session_id == session_id
        ]

    def latest_pending(self, user_id: str, session_id: str | None = None) -> MemoryProposal | None:
        items = self.pending_for_user(user_id, session_id)
        return items[-1] if items else None

    def replace(self, proposal: MemoryProposal) -> MemoryProposal:
        proposals = self._load()
        for index, item in enumerate(proposals):
            if item.proposal_id == proposal.proposal_id:
                proposals[index] = proposal
                self._save(proposals)
                return proposal
        raise LookupError("La propuesta no existe.")

    def update_content(
        self,
        proposal_id: str,
        *,
        user_id: str,
        session_id: str | None,
        content: str,
    ) -> MemoryProposal:
        proposal = self.get(
            proposal_id,
            user_id=user_id,
            session_id=session_id,
            include_closed=False,
        )
        if proposal is None:
            raise LookupError("La propuesta no está pendiente o no pertenece al usuario.")
        updated = replace(proposal, content=content.strip(), version=proposal.version + 1)
        return self.replace(updated)

    def close(
        self,
        proposal_id: str,
        *,
        user_id: str,
        session_id: str | None,
        status: str,
        result_id: str | None = None,
        minimize_content: bool = False,
    ) -> MemoryProposal:
        proposal = self.get(
            proposal_id,
            user_id=user_id,
            session_id=session_id,
            include_closed=True,
        )
        if proposal is None:
            raise LookupError("La propuesta no existe o no pertenece al usuario.")
        if proposal.status not in {"pending", "processing"}:
            return proposal
        closed = replace(
            proposal,
            status=status,
            result_id=result_id,
            content="" if minimize_content else proposal.content,
            source_text="" if minimize_content else proposal.source_text,
        )
        return self.replace(closed)

    def mark_processing(
        self,
        proposal_id: str,
        *,
        user_id: str,
        session_id: str | None,
    ) -> MemoryProposal:
        """Reserva idempotentemente una propuesta antes de modificar memoria."""

        proposal = self.get(
            proposal_id,
            user_id=user_id,
            session_id=session_id,
            include_closed=True,
        )
        if proposal is None:
            raise LookupError("La propuesta no existe en esta sesión.")
        if proposal.status != "pending":
            return proposal
        return self.replace(replace(proposal, status="processing"))

    def set_result(
        self,
        proposal_id: str,
        *,
        user_id: str,
        session_id: str | None,
        result_id: str,
    ) -> MemoryProposal:
        """Guarda el resultado mientras la propuesta continúa en procesamiento."""

        proposal = self.get(
            proposal_id,
            user_id=user_id,
            session_id=session_id,
            include_closed=True,
        )
        if proposal is None or proposal.status != "processing":
            raise LookupError("La propuesta no está en procesamiento en esta sesión.")
        return self.replace(replace(proposal, result_id=result_id))

    def expire(self) -> int:
        now = self.clock()
        proposals = self._load()
        changed = 0
        updated: list[MemoryProposal] = []
        for item in proposals:
            try:
                expires = datetime.fromisoformat(item.expires_at)
            except ValueError:
                expires = now
            if item.status == "pending" and expires <= now:
                updated.append(replace(item, status="expired", content="", source_text=""))
                changed += 1
            else:
                updated.append(item)
        if changed:
            self._save(updated)
        return changed
