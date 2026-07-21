"""Auditoría segura del ciclo de vida de memoria."""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from memory.workflow.models import MemoryAuditEntry


class MemoryAuditLog:
    """Registro JSONL mínimo; los valores sensibles se sustituyen por una marca."""

    SECRET = re.compile(
        r"(?i)\b(password|contrasena|token|api[ -]?key|cvv|iban)\b\s*[:=]?\s*\S+"
    )

    def __init__(self, path: Path | str, *, clock=None) -> None:
        self.path = Path(path)
        self.clock = clock or (lambda: datetime.now(UTC))

    def _safe(self, value: str | None, *, sensitive: bool) -> str | None:
        if value is None:
            return None
        if sensitive:
            return "[DATO SENSIBLE OMITIDO]"
        return self.SECRET.sub("[SECRETO OMITIDO]", value)

    def record(
        self,
        *,
        user_id: str,
        action: str,
        memory_id: str | None,
        proposal_id: str | None,
        previous_value: str | None = None,
        new_value: str | None = None,
        source: str = "conversation",
        sensitive: bool = False,
        metadata: dict | None = None,
    ) -> MemoryAuditEntry:
        entry = MemoryAuditEntry(
            event_id=uuid4().hex,
            memory_id=memory_id,
            user_id=user_id,
            action=action,
            timestamp=self.clock().isoformat(),
            source=source,
            previous_value=self._safe(previous_value, sensitive=sensitive),
            new_value=self._safe(new_value, sensitive=sensitive),
            proposal_id=proposal_id,
            metadata=metadata or {},
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        return entry

    def list_for_user(self, user_id: str) -> list[dict]:
        if not self.path.exists():
            return []
        results = []
        try:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(item.get("user_id", "")).casefold() == user_id.casefold():
                    results.append(item)
        except OSError:
            return []
        return results

    def has_event(self, *, user_id: str, proposal_id: str, action: str) -> bool:
        """Permite reintentos sin duplicar eventos de auditoría."""

        return any(
            item.get("proposal_id") == proposal_id
            and item.get("action") == action
            for item in self.list_for_user(user_id)
        )
