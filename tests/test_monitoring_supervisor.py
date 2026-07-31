from pathlib import Path

from monitoring.desktop_state import DesktopStateWriter
from monitoring.incident_manager import IncidentManager
from monitoring.models import HealthCheckResult, HealthState
from monitoring.notification_router import NotificationRouter
from monitoring.supervisor import AtlasSupervisor, SupervisorProbe


def test_incident_opens_and_resolves_without_duplicates(tmp_path):
    opened = []
    resolved = []
    manager = IncidentManager(
        tmp_path / "incidents.json",
        on_opened=opened.append,
        on_resolved=resolved.append,
    )

    failing = HealthCheckResult(
        check_id="home_assistant",
        display_name="Home Assistant",
        state=HealthState.ERROR,
        available=False,
        message="No responde.",
    )
    healthy = HealthCheckResult(
        check_id="home_assistant",
        display_name="Home Assistant",
        state=HealthState.OK,
        available=True,
        message="Disponible.",
    )

    first = manager.apply_result(failing, affected_users={"REDACTED_f73137d930c3"})
    second = manager.apply_result(failing, affected_users={"REDACTED_7b9528898599"})
    assert first is second
    assert len(opened) == 1
    assert first.affected_users == {"REDACTED_f73137d930c3", "REDACTED_7b9528898599"}

    manager.apply_result(healthy)
    assert len(resolved) == 1
    assert manager.active_incidents() == []


def test_router_limits_home_assistant_to_present_authorized_users():
    sent = []

    def send(user_id, title, message):
        sent.append((user_id, title, message))
        return True

    router = NotificationRouter(
        send_private=send,
        is_user_at_home=lambda user_id: user_id == "REDACTED_7b9528898599",
        has_capability=lambda user_id, capability: user_id in {"REDACTED_f73137d930c3", "REDACTED_7b9528898599"},
    )

    assert router.affected_users_for("home_assistant") == {"REDACTED_f73137d930c3", "REDACTED_7b9528898599"}
    assert router.affected_users_for("ollama") == {"REDACTED_f73137d930c3"}


def test_supervisor_writes_status(tmp_path):
    manager = IncidentManager(tmp_path / "incidents.json")
    router = NotificationRouter(
        send_private=lambda *args: True,
    )
    status_path = tmp_path / "status.json"

    result = HealthCheckResult(
        check_id="raspberry",
        display_name="Raspberry Pi",
        state=HealthState.OK,
        available=True,
        details={
            "sd": {
                "mounted": True,
                "free_bytes": 10,
                "used_percent": 20,
            }
        },
    )
    supervisor = AtlasSupervisor(
        probes=[
            SupervisorProbe(
                probe_id="raspberry",
                checker=lambda: result,
            )
        ],
        incident_manager=manager,
        notification_router=router,
        state_writer=DesktopStateWriter(status_path),
        interval_seconds=10,
    )

    supervisor.run_once()
    assert status_path.exists()
    text = status_path.read_text(encoding="utf-8")
    assert '"raspberry"' in text
    assert '"sd"' in text
