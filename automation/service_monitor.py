"""Supervisión segura y determinista de servicios registrados."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Any


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True, frozen=True)
class ServiceProbe:
    service_id: str
    display_name: str
    checker: Callable[[], bool | dict[str, Any]]
    critical: bool = False


class ServiceMonitor:
    def __init__(self) -> None:
        self._probes: dict[str, ServiceProbe] = {}

    def register(self, probe: ServiceProbe) -> None:
        if not probe.service_id.strip():
            raise ValueError("service_id no puede estar vacío.")
        if probe.service_id in self._probes:
            raise ValueError(f"El servicio '{probe.service_id}' ya está registrado.")
        self._probes[probe.service_id] = probe

    def check(self, service_id: str) -> dict[str, Any]:
        try:
            probe = self._probes[service_id]
        except KeyError as exc:
            raise LookupError(f"Servicio no registrado: {service_id}") from exc

        checked_at = _utc_now().isoformat()
        try:
            raw = probe.checker()
            if isinstance(raw, dict):
                available = bool(raw.get("available", raw.get("ok", False)))
                details = dict(raw)
            else:
                available = bool(raw)
                details = {}
            return {
                "service_id": probe.service_id,
                "display_name": probe.display_name,
                "available": available,
                "critical": probe.critical,
                "checked_at": checked_at,
                "details": details,
            }
        except Exception as exc:
            return {
                "service_id": probe.service_id,
                "display_name": probe.display_name,
                "available": False,
                "critical": probe.critical,
                "checked_at": checked_at,
                "details": {},
                "error_code": type(exc).__name__,
            }

    def check_all(self) -> list[dict[str, Any]]:
        return [self.check(service_id) for service_id in sorted(self._probes)]

    def summary(self) -> dict[str, Any]:
        services = self.check_all()
        unavailable = [item for item in services if not item["available"]]
        critical_down = [
            item for item in unavailable if item.get("critical", False)
        ]
        return {
            "available": not critical_down,
            "healthy_services": len(services) - len(unavailable),
            "total_services": len(services),
            "unavailable_services": [
                item["service_id"] for item in unavailable
            ],
            "critical_unavailable": [
                item["service_id"] for item in critical_down
            ],
            "services": services,
        }
