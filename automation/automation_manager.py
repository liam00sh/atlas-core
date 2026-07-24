"""Fachada y persistencia del motor de automatizaciones."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from automation.automation_audit import AutomationAudit
from automation.automation_executor import AutomationExecutor
from automation.automation_permissions import AutomationPermissions
from automation.automation_registry import AutomationRegistry
from automation.automation_scheduler import AutomationScheduler
from automation.automation_status import AutomationStatusService
from automation.models import (
    AuditEvent,
    Automation,
    AutomationStatus,
    ExecutionResult,
    Visibility,
    utc_now,
)


class AutomationManager:
    def __init__(
        self,
        storage_path: str | Path,
        registry: AutomationRegistry,
        permissions: AutomationPermissions,
        audit_path: str | Path | None = None,
    ) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry = registry
        self.permissions = permissions
        self.audit = AutomationAudit(
            audit_path or self.storage_path.with_suffix(".audit.jsonl")
        )
        self.status_service = AutomationStatusService()
        self.executor = AutomationExecutor(
            registry=registry,
            permissions=permissions,
            audit=self.audit,
            status_service=self.status_service,
        )
        self.scheduler = AutomationScheduler(self.executor)
        self._automations: dict[str, Automation] = {}
        self.load()

    def create(
        self,
        *,
        action_id: str,
        owner_user_id: str,
        creator_user_id: str,
        parameters: dict[str, Any] | None = None,
        title: str = "",
        description: str = "",
        visibility: Visibility = Visibility.PRIVATE,
        shared_user_ids: list[str] | None = None,
        shared_group_ids: list[str] | None = None,
        scheduled_for=None,
        metadata: dict[str, Any] | None = None,
    ) -> Automation:
        action = self.registry.get(action_id)
        clean_parameters = action.validate_parameters(parameters or {})
        creator = self.permissions.get_user(creator_user_id)
        if not creator.active:
            # Compatibilidad defensiva con registros heredados que pudieron
            # conservar la clave original sin normalizar.
            raw_users = getattr(self.permissions, "_users", {})
            legacy = next(
                (
                    value
                    for key, value in raw_users.items()
                    if str(key).strip().casefold()
                    == str(creator_user_id).strip().casefold()
                ),
                None,
            )
            if legacy is not None:
                creator = legacy
        if not creator.active:
            raise PermissionError("El creador no es un usuario activo.")
        if action.technical_only and not creator.is_admin:
            raise PermissionError(
                "Solo el administrador puede crear automatizaciones técnicas."
            )
        automation = Automation(
            action_id=action_id,
            owner_user_id=owner_user_id,
            creator_user_id=creator_user_id,
            parameters=clean_parameters,
            title=title.strip(),
            description=description.strip(),
            visibility=visibility,
            shared_user_ids=list(dict.fromkeys(shared_user_ids or [])),
            shared_group_ids=list(dict.fromkeys(shared_group_ids or [])),
            scheduled_for=scheduled_for,
            status=(
                AutomationStatus.SCHEDULED
                if scheduled_for is not None
                else AutomationStatus.DRAFT
            ),
            metadata=dict(metadata or {}),
        )
        self._automations[automation.automation_id] = automation
        self.save()
        self.audit.record(
            AuditEvent(
                event_type="automation.created",
                automation_id=automation.automation_id,
                action_id=automation.action_id,
                owner_user_id=automation.owner_user_id,
                requested_by_user_id=creator_user_id,
                channel="internal",
            )
        )
        return automation

    def get(self, automation_id: str, user_id: str) -> Automation:
        automation = self._automations[automation_id]
        if not self.permissions.can_view(user_id, automation):
            raise PermissionError("No puedes consultar esta automatización.")
        return automation

    def list_for_user(self, user_id: str) -> list[Automation]:
        return [
            item
            for item in sorted(
                self._automations.values(),
                key=lambda value: value.created_at,
            )
            if self.permissions.can_view(user_id, item)
        ]

    def execute(
        self,
        automation_id: str,
        requested_by_user_id: str,
        channel: str,
        confirmed: bool = False,
    ) -> ExecutionResult:
        automation = self._automations[automation_id]
        result = self.executor.execute(
            automation,
            requested_by_user_id=requested_by_user_id,
            channel=channel,
            confirmed=confirmed,
        )
        self.save()
        return result

    def pause(self, automation_id: str, requested_by_user_id: str) -> Automation:
        automation = self._require_manage(
            automation_id,
            requested_by_user_id,
        )
        self.status_service.transition(
            automation,
            AutomationStatus.PAUSED,
        )
        self.save()
        return automation

    def resume(self, automation_id: str, requested_by_user_id: str) -> Automation:
        automation = self._require_manage(
            automation_id,
            requested_by_user_id,
        )
        self.status_service.transition(
            automation,
            AutomationStatus.SCHEDULED,
        )
        self.save()
        return automation

    def cancel(self, automation_id: str, requested_by_user_id: str) -> Automation:
        automation = self._require_manage(
            automation_id,
            requested_by_user_id,
        )
        self.status_service.transition(
            automation,
            AutomationStatus.CANCELLED,
        )
        self.save()
        return automation

    def run_due(self, now=None) -> list[ExecutionResult]:
        results = self.scheduler.run_due(
            list(self._automations.values()),
            requested_by_user_id="system",
            channel="scheduler",
            now=now,
        )
        self.save()
        return results

    def save(self) -> None:
        payload = {
            "schema_version": 1,
            "updated_at": utc_now().isoformat(),
            "automations": [
                item.to_dict()
                for item in self._automations.values()
            ],
        }
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.storage_path.parent,
            delete=False,
        ) as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2)
            temporary = Path(stream.name)
        os.replace(temporary, self.storage_path)

    def load(self) -> None:
        self._automations.clear()
        if not self.storage_path.exists():
            return
        with self.storage_path.open("r", encoding="utf-8") as stream:
            payload = json.load(stream)
        for data in payload.get("automations", []):
            automation = Automation.from_dict(data)
            self._automations[automation.automation_id] = automation

    def _require_manage(
        self,
        automation_id: str,
        requested_by_user_id: str,
    ) -> Automation:
        automation = self._automations[automation_id]
        if not self.permissions.can_manage(
            requested_by_user_id,
            automation,
        ):
            raise PermissionError("No puedes administrar esta automatización.")
        return automation
