"""Integración segura del camino real de construcción del supervisor."""

from __future__ import annotations

import json
from threading import Event, Thread

from monitoring.bootstrap import build_supervisor
from monitoring.models import HealthCheckResult, HealthState
from monitoring.supervisor import SupervisorProbe


def test_bootstrap_runs_failure_recovery_and_clean_shutdown(
    tmp_path,
    monkeypatch,
):
    incidents_path = tmp_path / "monitoring" / "incidents.json"
    status_path = tmp_path / "monitoring" / "status.json"
    monkeypatch.setenv("ATLAS_INCIDENTS_PATH", str(incidents_path))
    monkeypatch.setenv("ATLAS_SUPERVISOR_STATUS_PATH", str(status_path))
    monkeypatch.setenv("ATLAS_SUPERVISOR_INTERVAL", "0.01")
    monkeypatch.delenv("ATLAS_RASPBERRY_HOST", raising=False)

    notifications = []
    incident_opened = Event()
    incident_resolved = Event()
    recovery_enabled = Event()
    healthy_probe_ran = Event()

    def fake_telegram_sender(user_id, title, message):
        notifications.append((user_id, title, message))
        if "Recuperado" in title:
            incident_resolved.set()
        else:
            incident_opened.set()
        return True

    def healthy_checker():
        healthy_probe_ran.set()
        return HealthCheckResult(
            check_id="healthy_service",
            display_name="Healthy Service",
            state=HealthState.OK,
            available=True,
            message="Disponible.",
        )

    def recovering_checker():
        if not recovery_enabled.is_set():
            raise RuntimeError("simulated-token-must-not-leak")
        return HealthCheckResult(
            check_id="recovering_service",
            display_name="Recovering Service",
            state=HealthState.OK,
            available=True,
            message="Disponible.",
        )

    supervisor, monitor = build_supervisor(
        telegram_sender=fake_telegram_sender,
        probes=[
            SupervisorProbe("recovering_service", recovering_checker),
            SupervisorProbe("healthy_service", healthy_checker),
        ],
    )

    assert supervisor is not None
    assert monitor is None
    worker = Thread(
        target=supervisor.run_forever,
        name="atlas-monitoring-bootstrap-test",
    )
    worker.start()
    try:
        assert incident_opened.wait(2.0)
        assert healthy_probe_ran.wait(2.0)
        assert len(supervisor.incident_manager.active_incidents()) == 1
        recovery_enabled.set()
        assert incident_resolved.wait(2.0)
        assert supervisor.incident_manager.active_incidents() == []
    finally:
        supervisor.close()
        worker.join(timeout=2.0)

    assert supervisor.closed
    assert supervisor.wait(0)
    assert not worker.is_alive()
    assert incidents_path.is_file()
    assert status_path.is_file()

    incidents_text = incidents_path.read_text(encoding="utf-8")
    status_text = status_path.read_text(encoding="utf-8")
    payload = json.loads(status_text)
    checks = payload["supervisor"]["checks"]
    assert checks["recovering_service"]["state"] == "ok"
    assert checks["healthy_service"]["state"] == "ok"
    assert "simulated-token-must-not-leak" not in incidents_text
    assert "simulated-token-must-not-leak" not in status_text
    assert len(notifications) == 2
    assert notifications[0][0] == "REDACTED_f73137d930c3"
    assert "Recuperado" in notifications[1][1]
