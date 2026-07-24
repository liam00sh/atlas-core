"""Creación de copias manuales mediante planes cerrados."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Any
import hashlib
import json


@dataclass(slots=True, frozen=True)
class BackupPlan:
    plan_id: str
    display_name: str
    runner: Callable[[], dict[str, Any] | str | Path]
    allowed: bool = True


class BackupAdapter:
    def __init__(self, manifest_dir: str | Path) -> None:
        self.manifest_dir = Path(manifest_dir)
        self.manifest_dir.mkdir(parents=True, exist_ok=True)
        self._plans: dict[str, BackupPlan] = {}

    def register(self, plan: BackupPlan) -> None:
        if not plan.plan_id.strip():
            raise ValueError("plan_id no puede estar vacío.")
        if plan.plan_id in self._plans:
            raise ValueError(f"El plan '{plan.plan_id}' ya está registrado.")
        self._plans[plan.plan_id] = plan

    def create(self, plan_id: str) -> dict[str, Any]:
        try:
            plan = self._plans[plan_id]
        except KeyError as exc:
            raise LookupError(f"Plan de copia no registrado: {plan_id}") from exc
        if not plan.allowed:
            raise PermissionError("El plan de copia está deshabilitado.")

        started_at = datetime.now(timezone.utc)
        raw = plan.runner()
        completed_at = datetime.now(timezone.utc)

        if isinstance(raw, dict):
            result = dict(raw)
        else:
            result = {"output": str(raw)}

        manifest = {
            "plan_id": plan.plan_id,
            "display_name": plan.display_name,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "result": result,
        }
        digest = hashlib.sha256(
            json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        manifest["manifest_sha256"] = digest

        path = self.manifest_dir / (
            f"{completed_at.strftime('%Y%m%dT%H%M%SZ')}_{plan.plan_id}.json"
        )
        path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        manifest["manifest_path"] = str(path)
        return manifest
