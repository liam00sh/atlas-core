"""
Proyecto Atlas
Archivo: automation/device_policy.py

Política común de autorización por usuario, dispositivo y capacidad.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from automation.device_models import DeviceRecord, TrustLevel


class AccessDecision(StrEnum):
    ALLOW = "allow"
    DENY_UNKNOWN_USER = "deny_unknown_user"
    DENY_REVOKED_DEVICE = "deny_revoked_device"
    DENY_UNTRUSTED_DEVICE = "deny_untrusted_device"
    DENY_CAPABILITY_MISSING = "deny_capability_missing"
    DENY_NOT_OWNER_OR_SHARED = "deny_not_owner_or_shared"
    DENY_CONFIRMATION_REQUIRED = "deny_confirmation_required"
    DENY_LOCAL_PRESENCE_REQUIRED = "deny_local_presence_required"


@dataclass(frozen=True)
class DeviceAccessRequest:
    requester_user_id: str
    device: DeviceRecord
    capability: str
    known_user: bool
    is_platform_admin: bool = False
    confirmed: bool = False
    local_presence_verified: bool = False
    sensitive: bool = False
    critical: bool = False


@dataclass(frozen=True)
class DeviceAccessResult:
    allowed: bool
    decision: AccessDecision
    reason: str


class DevicePolicyEngine:
    """Aplica una política conservadora y explícita."""

    def evaluate(self, request: DeviceAccessRequest) -> DeviceAccessResult:
        device = request.device

        if not request.known_user:
            return self._deny(
                AccessDecision.DENY_UNKNOWN_USER,
                "El solicitante no es un usuario vinculado de Atlas.",
            )

        if device.trust_level is TrustLevel.REVOKED:
            return self._deny(
                AccessDecision.DENY_REVOKED_DEVICE,
                "El dispositivo ha sido revocado.",
            )

        if device.trust_level in {TrustLevel.UNTRUSTED, TrustLevel.PENDING}:
            return self._deny(
                AccessDecision.DENY_UNTRUSTED_DEVICE,
                "El dispositivo todavía no es confiable.",
            )

        if not device.exposes(request.capability):
            return self._deny(
                AccessDecision.DENY_CAPABILITY_MISSING,
                "El dispositivo no expone esa capacidad.",
            )

        owner_access = request.requester_user_id == device.owner_user_id
        shared = request.capability in device.shared_capabilities.get(
            request.requester_user_id,
            frozenset(),
        )

        if not owner_access and not shared and not request.is_platform_admin:
            return self._deny(
                AccessDecision.DENY_NOT_OWNER_OR_SHARED,
                "La capacidad no está compartida con este usuario.",
            )

        if device.requires_local_presence and not request.local_presence_verified:
            return self._deny(
                AccessDecision.DENY_LOCAL_PRESENCE_REQUIRED,
                "La acción exige presencia local verificada.",
            )

        if (request.sensitive or request.critical) and not request.confirmed:
            return self._deny(
                AccessDecision.DENY_CONFIRMATION_REQUIRED,
                "La acción necesita confirmación explícita.",
            )

        return DeviceAccessResult(
            allowed=True,
            decision=AccessDecision.ALLOW,
            reason="Acceso autorizado.",
        )

    @staticmethod
    def _deny(decision: AccessDecision, reason: str) -> DeviceAccessResult:
        return DeviceAccessResult(
            allowed=False,
            decision=decision,
            reason=reason,
        )
