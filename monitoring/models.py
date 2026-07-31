"""Modelos comunes para monitorización e incidencias de Atlas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class HealthState(StrEnum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class IncidentSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(slots=True, frozen=True)
class HealthCheckResult:
    check_id: str
    display_name: str
    state: HealthState
    available: bool
    checked_at: str = field(default_factory=utc_now_iso)
    details: dict[str, Any] = field(default_factory=dict)
    error_code: str | None = None
    message: str | None = None


@dataclass(slots=True)
class Incident:
    incident_id: str
    source_id: str
    title: str
    message: str
    severity: IncidentSeverity
    opened_at: str
    updated_at: str
    resolved_at: str | None = None
    active: bool = True
    affected_users: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)
