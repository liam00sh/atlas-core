"""
Proyecto Atlas
Archivo: automation/stage_d_bootstrap.py

Construcción del motor de la Etapa D con usuarios y permisos explícitos.
"""

from __future__ import annotations

from pathlib import Path

from automation.automation_manager import AutomationManager
from automation.automation_permissions import AutomationPermissions, UserAccess
from automation.automation_registry import AutomationRegistry
from automation.stage_c_catalog import register_stage_c_actions
from automation.stage_d_catalog import register_stage_d_actions


def build_stage_d_permissions() -> AutomationPermissions:
    permissions = AutomationPermissions()
    permissions.set_user(
        UserAccess(
            user_id="REDACTED_f73137d930c3",
            roles={"owner", "administrator"},
            permissions={
                "system.status.read",
                "backup.create",
                "notification.send",
                "routine.technical.run",
                "windows.status.read",
                "windows.process.read",
                "windows.application.open",
            },
        )
    )
    permissions.set_user(
        UserAccess(
            user_id="REDACTED_7b9528898599",
            roles={"family"},
            permissions={
                "system.status.read",
                "windows.status.read",
                # windows.application.open se concederá dinámicamente
                # solo cuando exista presencia doméstica verificada.
            },
        )
    )
    permissions.set_user(
        UserAccess(
            user_id="REDACTED_6915771be1c5",
            roles={"family"},
            permissions={
                "system.status.read",
            },
        )
    )
    permissions.set_user(
        UserAccess(
            user_id="system",
            roles={"administrator"},
            permissions=set(),
        )
    )
    return permissions


def build_stage_d_manager(
    *,
    storage_path: str | Path,
    audit_path: str | Path | None = None,
    include_stage_c: bool = False,
) -> AutomationManager:
    registry = AutomationRegistry()
    if include_stage_c:
        register_stage_c_actions(registry)
    register_stage_d_actions(registry)

    return AutomationManager(
        storage_path=storage_path,
        registry=registry,
        permissions=build_stage_d_permissions(),
        audit_path=audit_path,
    )
