import json

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

    first = manager.apply_result(failing, affected_users={"Alex"})
    second = manager.apply_result(failing, affected_users={"Vega"})
    assert first is second
    assert len(opened) == 1
    assert first.affected_users == {"Alex", "Vega"}

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
        is_user_at_home=lambda user_id: user_id == "Vega",
        has_capability=lambda user_id, capability: user_id in {"Alex", "Vega"},
    )

    assert router.affected_users_for("home_assistant") == {"Alex", "Vega"}
    assert router.affected_users_for("ollama") == {"Alex"}


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


def test_failing_probe_does_not_stop_other_probes(tmp_path):
    notifications = []
    router = NotificationRouter(
        send_private=lambda *args: notifications.append(args) or True,
    )
    manager = IncidentManager(
        tmp_path / "incidents.json",
    )
    status_path = tmp_path / "status.json"

    def fail():
        raise RuntimeError("token=secret-value")

    healthy = HealthCheckResult(
        check_id="ollama",
        display_name="Ollama",
        state=HealthState.OK,
        available=True,
        message="Disponible.",
    )
    supervisor = AtlasSupervisor(
        probes=[
            SupervisorProbe("home_assistant", fail),
            SupervisorProbe("ollama", lambda: healthy),
        ],
        incident_manager=manager,
        notification_router=router,
        state_writer=DesktopStateWriter(status_path),
        interval_seconds=0,
    )

    results = supervisor.run_once()

    assert [item.check_id for item in results] == ["home_assistant", "ollama"]
    assert results[0].error_code == "probe_exception"
    assert "secret-value" not in (results[0].message or "")
    assert results[1] is healthy
    assert len(manager.active_incidents()) == 1
    assert notifications
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert set(payload["supervisor"]["checks"]) == {
        "home_assistant",
        "ollama",
    }


def test_probe_recovery_resolves_incident_and_close_is_clean(tmp_path):
    notifications = []
    router = NotificationRouter(
        send_private=lambda *args: notifications.append(args) or True,
    )
    manager = IncidentManager(tmp_path / "incidents.json")
    state = {"healthy": False}

    def check():
        healthy = state["healthy"]
        return HealthCheckResult(
            check_id="ollama",
            display_name="Ollama",
            state=HealthState.OK if healthy else HealthState.ERROR,
            available=healthy,
            message="Disponible." if healthy else "No responde.",
        )

    supervisor = AtlasSupervisor(
        probes=[SupervisorProbe("ollama", check)],
        incident_manager=manager,
        notification_router=router,
        state_writer=DesktopStateWriter(tmp_path / "status.json"),
        interval_seconds=0,
    )

    supervisor.run_once()
    assert len(manager.active_incidents()) == 1
    state["healthy"] = True
    supervisor.run_once()
    assert manager.active_incidents() == []
    assert len(notifications) == 2

    supervisor.close()
    assert supervisor.closed
    assert supervisor.wait(0)
    try:
        supervisor.run_once()
    except RuntimeError as exc:
        assert "cerrado" in str(exc)
    else:
        raise AssertionError("run_once debe rechazar ciclos tras close()")
