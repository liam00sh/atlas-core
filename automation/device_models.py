"""
Proyecto Atlas
Archivo: automation/device_models.py

Modelos base para el registro de dispositivos y capacidades.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Mapping


class DeviceType(StrEnum):
    WINDOWS_PC = "windows_pc"
    LINUX_PC = "linux_pc"
    ANDROID_PHONE = "android_phone"
    IOS_PHONE = "ios_phone"
    TABLET = "tablet"
    WATCH = "watch"
    TV = "tv"
    RASPBERRY_PI = "raspberry_pi"
    HOME_NODE = "home_node"
    OTHER = "other"


class TrustLevel(StrEnum):
    UNTRUSTED = "untrusted"
    PENDING = "pending"
    PERSONAL = "personal"
    FAMILY = "family"
    INFRASTRUCTURE = "infrastructure"
    REVOKED = "revoked"


@dataclass(frozen=True)
class DeviceRecord:
    device_id: str
    display_name: str
    owner_user_id: str
    device_type: DeviceType
    operating_system: str
    agent_name: str
    agent_version: str
    trust_level: TrustLevel
    capabilities: frozenset[str] = field(default_factory=frozenset)
    shared_capabilities: Mapping[str, frozenset[str]] = field(default_factory=dict)
    online: bool = False
    requires_local_presence: bool = False
    confirmation_methods: frozenset[str] = field(default_factory=frozenset)
    created_at: datetime | None = None
    last_seen_at: datetime | None = None
    revoked_reason: str = ""

    def is_revoked(self) -> bool:
        return self.trust_level is TrustLevel.REVOKED

    def exposes(self, capability: str) -> bool:
        return capability in self.capabilities
