"""Modelos del motor de automatizaciones seguras."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Callable
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def from_iso(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class AutomationRisk(StrEnum):
    SAFE = "safe"
    SENSITIVE = "sensitive"
    CRITICAL = "critical"


class ConfirmationLevel(StrEnum):
    NONE = "none"
    SIMPLE = "simple"
    REINFORCED = "reinforced"


class AutomationStatus(StrEnum):
    DRAFT = "draft"
    PENDING_CONFIRMATION = "pending_confirmation"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    BLOCKED = "blocked"


class Visibility(StrEnum):
    PRIVATE = "private"
    SHARED = "shared"
    TECHNICAL = "technical"


class PermissionDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_CONFIRMATION = "require_confirmation"


@dataclass(slots=True, frozen=True)
class ActionDefinition:
    action_id: str
    name: str
    description: str
    handler: Callable[[dict[str, Any]], Any]
    required_permission: str
    risk: AutomationRisk = AutomationRisk.SAFE
    confirmation: ConfirmationLevel = ConfirmationLevel.NONE
    timeout_seconds: int = 30
    max_retries: int = 0
    cancellable: bool = True
    allowed_parameters: frozenset[str] = frozenset()
    technical_only: bool = False

    def validate_parameters(self, parameters: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(parameters, dict):
            raise TypeError("Los parámetros deben ser un diccionario.")
        unknown = set(parameters) - set(self.allowed_parameters)
        if unknown:
            joined = ", ".join(sorted(unknown))
            raise ValueError(f"Parámetros no permitidos: {joined}.")
        return dict(parameters)


@dataclass(slots=True)
class Automation:
    action_id: str
    owner_user_id: str
    creator_user_id: str
    parameters: dict[str, Any] = field(default_factory=dict)
    automation_id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    description: str = ""
    visibility: Visibility = Visibility.PRIVATE
    shared_user_ids: list[str] = field(default_factory=list)
    shared_group_ids: list[str] = field(default_factory=list)
    status: AutomationStatus = AutomationStatus.DRAFT
    scheduled_for: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    last_run_at: datetime | None = None
    confirmation_id: str | None = None
    confirmation_expires_at: datetime | None = None
    confirmation_user_id: str | None = None
    confirmation_channel: str | None = None
    execution_key: str | None = None
    retry_count: int = 0
    error_code: str | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["visibility"] = self.visibility.value
        data["status"] = self.status.value
        for key in (
            "scheduled_for",
            "created_at",
            "updated_at",
            "last_run_at",
            "confirmation_expires_at",
        ):
            data[key] = to_iso(getattr(self, key))
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Automation":
        payload = dict(data)
        payload["visibility"] = Visibility(payload.get("visibility", "private"))
        payload["status"] = AutomationStatus(payload.get("status", "draft"))
        for key in (
            "scheduled_for",
            "created_at",
            "updated_at",
            "last_run_at",
            "confirmation_expires_at",
        ):
            payload[key] = from_iso(payload.get(key))
        return cls(**payload)


@dataclass(slots=True, frozen=True)
class ExecutionResult:
    success: bool
    automation_id: str
    status: AutomationStatus
    result: Any = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(slots=True, frozen=True)
class AuditEvent:
    event_type: str
    automation_id: str
    action_id: str
    owner_user_id: str
    requested_by_user_id: str
    channel: str
    timestamp: datetime = field(default_factory=utc_now)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "automation_id": self.automation_id,
            "action_id": self.action_id,
            "owner_user_id": self.owner_user_id,
            "requested_by_user_id": self.requested_by_user_id,
            "channel": self.channel,
            "timestamp": to_iso(self.timestamp),
            "details": self.details,
        }
