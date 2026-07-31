"""Gestión persistente y deduplicada de incidencias técnicas."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable, Iterable

from monitoring.models import (
    HealthCheckResult,
    HealthState,
    Incident,
    IncidentSeverity,
    utc_now_iso,
)


class IncidentManager:
    def __init__(
        self,
        storage_path: str | Path,
        *,
        on_opened: Callable[[Incident], None] | None = None,
        on_resolved: Callable[[Incident], None] | None = None,
    ) -> None:
        self.storage_path = Path(storage_path)
        self.on_opened = on_opened
        self.on_resolved = on_resolved
        self._incidents: dict[str, Incident] = {}
        self._load()

    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for item in payload:
            incident = Incident(
                incident_id=item["incident_id"],
                source_id=item["source_id"],
                title=item["title"],
                message=item["message"],
                severity=IncidentSeverity(item["severity"]),
                opened_at=item["opened_at"],
                updated_at=item["updated_at"],
                resolved_at=item.get("resolved_at"),
                active=bool(item.get("active", True)),
                affected_users=set(item.get("affected_users", [])),
                metadata=dict(item.get("metadata", {})),
            )
            self._incidents[incident.source_id] = incident

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = []
        for incident in self._incidents.values():
            item = asdict(incident)
            item["severity"] = incident.severity.value
            item["affected_users"] = sorted(incident.affected_users)
            payload.append(item)
        temp = self.storage_path.with_suffix(self.storage_path.suffix + ".tmp")
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.storage_path)

    @staticmethod
    def _severity_for(result: HealthCheckResult) -> IncidentSeverity:
        mapping = {
            HealthState.WARNING: IncidentSeverity.WARNING,
            HealthState.ERROR: IncidentSeverity.ERROR,
            HealthState.CRITICAL: IncidentSeverity.CRITICAL,
            HealthState.UNKNOWN: IncidentSeverity.WARNING,
        }
        return mapping.get(result.state, IncidentSeverity.INFO)

    def apply_result(
        self,
        result: HealthCheckResult,
        *,
        affected_users: Iterable[str] = (),
    ) -> Incident | None:
        current = self._incidents.get(result.check_id)
        now = utc_now_iso()
        unhealthy = result.state in {
            HealthState.WARNING,
            HealthState.ERROR,
            HealthState.CRITICAL,
            HealthState.UNKNOWN,
        }

        if unhealthy:
            if current is None or not current.active:
                incident = Incident(
                    incident_id=f"{result.check_id}-{datetime.now(timezone.utc):%Y%m%d%H%M%S}",
                    source_id=result.check_id,
                    title=f"Incidencia en {result.display_name}",
                    message=result.message or "Se ha detectado un problema.",
                    severity=self._severity_for(result),
                    opened_at=now,
                    updated_at=now,
                    affected_users=set(affected_users),
                    metadata={"result": result.details},
                )
                self._incidents[result.check_id] = incident
                self._save()
                if self.on_opened:
                    self.on_opened(incident)
                return incident

            current.updated_at = now
            current.message = result.message or current.message
            current.severity = self._severity_for(result)
            current.affected_users.update(affected_users)
            current.metadata["result"] = result.details
            self._save()
            return current

        if current is not None and current.active:
            current.active = False
            current.updated_at = now
            current.resolved_at = now
            current.affected_users.update(affected_users)
            self._save()
            if self.on_resolved:
                self.on_resolved(current)
            return current
        return None

    def add_affected_user(self, source_id: str, user_id: str) -> bool:
        incident = self._incidents.get(source_id)
        if incident is None or not incident.active:
            return False
        if user_id in incident.affected_users:
            return False
        incident.affected_users.add(user_id)
        incident.updated_at = utc_now_iso()
        self._save()
        return True

    def active_incidents(self) -> list[Incident]:
        return [
            incident
            for incident in self._incidents.values()
            if incident.active
        ]
