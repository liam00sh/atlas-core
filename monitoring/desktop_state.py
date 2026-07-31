"""Persistencia atómica del estado mostrado por los widgets del escritorio."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from monitoring.models import HealthCheckResult, Incident


class DesktopStateWriter:
    def __init__(self, status_path: str | Path) -> None:
        self.status_path = Path(status_path)

    def write(
        self,
        *,
        raspberry: HealthCheckResult | None,
        active_incidents: list[Incident],
        supervisor: dict[str, Any],
    ) -> None:
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "raspberry": asdict(raspberry) if raspberry is not None else None,
            "incidents": [
                {
                    **asdict(incident),
                    "severity": incident.severity.value,
                    "affected_users": sorted(incident.affected_users),
                }
                for incident in active_incidents
            ],
            "supervisor": supervisor,
        }
        temp = self.status_path.with_suffix(self.status_path.suffix + ".tmp")
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temp.replace(self.status_path)
