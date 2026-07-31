"""Recomendación y ejecución explícita de recuperaciones monitorizadas."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Callable

from monitoring.models import HealthCheckResult, utc_now_iso


@dataclass(frozen=True, slots=True)
class RecoveryAction:
    action_id: str
    description: str
    handler: Callable[[], object]
    owner_only: bool = True


@dataclass(frozen=True, slots=True)
class RecoveryRecommendation:
    source_id: str
    action_id: str
    description: str
    requires_owner: bool
    requires_confirmation: bool = True


@dataclass(frozen=True, slots=True)
class RecoveryResult:
    action_id: str
    requested_by: str
    authorized: bool
    success: bool
    executed_at: str
    result: str | None = None
    error: str | None = None


class RecoveryCoordinator:
    """Mantiene recomendar y actuar separados; nunca actúa desde una sonda."""

    def __init__(
        self,
        audit_path: str | Path,
        *,
        is_owner: Callable[[str], bool],
        max_history: int = 500,
    ) -> None:
        self.audit_path = Path(audit_path)
        self.is_owner = is_owner
        self.max_history = max(1, int(max_history))
        self._actions: dict[str, RecoveryAction] = {}

    def register(self, action: RecoveryAction) -> None:
        if not action.action_id.strip() or action.action_id in self._actions:
            raise ValueError("La acción de recuperación debe tener un identificador único.")
        self._actions[action.action_id] = action

    def recommend(self, result: HealthCheckResult) -> RecoveryRecommendation | None:
        if result.available or not result.recoverable or not result.recovery_action_id:
            return None
        action = self._actions.get(result.recovery_action_id)
        if action is None:
            return None
        return RecoveryRecommendation(
            source_id=result.check_id,
            action_id=action.action_id,
            description=action.description,
            requires_owner=action.owner_only,
        )

    def execute(
        self,
        action_id: str,
        *,
        requested_by: str,
        confirmed: bool,
        policy_allows: bool,
    ) -> RecoveryResult:
        action = self._actions.get(action_id)
        allowed = bool(
            action
            and confirmed
            and policy_allows
            and (not action.owner_only or self.is_owner(requested_by))
        )
        if not allowed:
            result = RecoveryResult(
                action_id=action_id,
                requested_by=requested_by,
                authorized=False,
                success=False,
                executed_at=utc_now_iso(),
                error="recovery_not_authorized",
            )
            self._record(result)
            return result
        try:
            value = action.handler()
            result = RecoveryResult(
                action_id=action_id,
                requested_by=requested_by,
                authorized=True,
                success=True,
                executed_at=utc_now_iso(),
                result=str(value),
            )
        except Exception as exc:
            result = RecoveryResult(
                action_id=action_id,
                requested_by=requested_by,
                authorized=True,
                success=False,
                executed_at=utc_now_iso(),
                error=type(exc).__name__,
            )
        self._record(result)
        return result

    def history(self) -> list[dict]:
        if not self.audit_path.exists():
            return []
        try:
            payload = json.loads(self.audit_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return payload if isinstance(payload, list) else []

    def _record(self, result: RecoveryResult) -> None:
        payload = [*self.history(), asdict(result)][-self.max_history:]
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.audit_path.with_suffix(self.audit_path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.audit_path)
