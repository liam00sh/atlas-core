"""Ejecución controlada de acciones registradas."""

from __future__ import annotations

from automation.automation_audit import AutomationAudit
from automation.automation_permissions import AutomationPermissions
from automation.automation_registry import AutomationRegistry
from automation.automation_status import AutomationStatusService
from automation.models import (
    AuditEvent,
    Automation,
    AutomationStatus,
    ExecutionResult,
    PermissionDecision,
    utc_now,
)


class AutomationExecutor:
    def __init__(
        self,
        registry: AutomationRegistry,
        permissions: AutomationPermissions,
        audit: AutomationAudit,
        status_service: AutomationStatusService | None = None,
    ) -> None:
        self.registry = registry
        self.permissions = permissions
        self.audit = audit
        self.status_service = status_service or AutomationStatusService()
        self._running_keys: set[str] = set()

    def execute(
        self,
        automation: Automation,
        requested_by_user_id: str,
        channel: str,
        confirmed: bool = False,
    ) -> ExecutionResult:
        action = self.registry.get(automation.action_id)
        parameters = action.validate_parameters(automation.parameters)
        decision = self.permissions.evaluate(
            requested_by_user_id,
            action,
            automation,
        )

        if decision == PermissionDecision.DENY:
            self.status_service.transition(automation, AutomationStatus.BLOCKED)
            self._audit(
                "automation.blocked.permission",
                automation,
                requested_by_user_id,
                channel,
            )
            return ExecutionResult(
                False,
                automation.automation_id,
                automation.status,
                error_code="permission_denied",
                error_message="El usuario no tiene permiso.",
            )

        if decision == PermissionDecision.REQUIRE_CONFIRMATION and not confirmed:
            self.status_service.transition(
                automation,
                AutomationStatus.PENDING_CONFIRMATION,
            )
            self._audit(
                "automation.confirmation.requested",
                automation,
                requested_by_user_id,
                channel,
            )
            return ExecutionResult(
                False,
                automation.automation_id,
                automation.status,
                error_code="confirmation_required",
                error_message="La acción requiere confirmación.",
            )

        execution_key = (
            automation.execution_key
            or f"{automation.automation_id}:{automation.retry_count}"
        )
        if execution_key in self._running_keys:
            return ExecutionResult(
                False,
                automation.automation_id,
                automation.status,
                error_code="duplicate_execution",
                error_message="La automatización ya se está ejecutando.",
            )

        self._running_keys.add(execution_key)
        try:
            self.status_service.transition(
                automation,
                AutomationStatus.RUNNING,
            )
            automation.last_run_at = utc_now()
            self._audit(
                "automation.started",
                automation,
                requested_by_user_id,
                channel,
            )
            result = action.handler(parameters)
            self.status_service.transition(
                automation,
                AutomationStatus.COMPLETED,
            )
            self._audit(
                "automation.completed",
                automation,
                requested_by_user_id,
                channel,
                {"result_type": type(result).__name__},
            )
            return ExecutionResult(
                True,
                automation.automation_id,
                automation.status,
                result=result,
            )
        except Exception as exc:
            automation.error_code = type(exc).__name__
            automation.error_message = str(exc)
            self.status_service.transition(
                automation,
                AutomationStatus.FAILED,
            )
            self._audit(
                "automation.failed",
                automation,
                requested_by_user_id,
                channel,
                {"error_code": type(exc).__name__},
            )
            return ExecutionResult(
                False,
                automation.automation_id,
                automation.status,
                error_code=type(exc).__name__,
                error_message=str(exc),
            )
        finally:
            self._running_keys.discard(execution_key)

    def _audit(
        self,
        event_type: str,
        automation: Automation,
        user_id: str,
        channel: str,
        details: dict | None = None,
    ) -> None:
        self.audit.record(
            AuditEvent(
                event_type=event_type,
                automation_id=automation.automation_id,
                action_id=automation.action_id,
                owner_user_id=automation.owner_user_id,
                requested_by_user_id=user_id,
                channel=channel,
                details=details or {},
            )
        )
