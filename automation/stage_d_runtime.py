"""
Proyecto Atlas
Archivo: automation/stage_d_runtime.py

Runtime mínimo de la Etapa D para conversación local.
"""

from __future__ import annotations

from pathlib import Path

from automation.stage_d_bootstrap import build_stage_d_manager
from automation.windows_intent_service import WindowsIntentService


def build_stage_d_windows_intent_service(
    *,
    data_dir: str | Path,
) -> WindowsIntentService:
    root = Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)

    manager = build_stage_d_manager(
        storage_path=root / "automations.json",
        audit_path=root / "automation_audit.jsonl",
    )
    return WindowsIntentService(manager)
