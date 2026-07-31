import json

from monitoring.history import HealthHistoryStore
from monitoring.models import HealthCheckResult, HealthState
from monitoring.recovery import RecoveryAction, RecoveryCoordinator
from monitoring.supervisor import _raspberry_resource_results


def unhealthy(**overrides):
    values = dict(
        check_id="telegram",
        display_name="Telegram",
        state=HealthState.ERROR,
        available=False,
        message="No disponible.",
        recoverable=True,
        requires_intervention=True,
        recovery_action_id="service.telegram.restart",
    )
    values.update(overrides)
    return HealthCheckResult(**values)


def test_common_health_result_exposes_uniform_contract():
    result = unhealthy()
    assert result.identifier == "telegram"
    assert result.status == "unavailable"
    assert result.additional_data == {}
    assert result.recoverable is True
    assert result.requires_intervention is True


def test_recommendation_never_executes_action(tmp_path):
    calls = []
    coordinator = RecoveryCoordinator(
        tmp_path / "recovery.json", is_owner=lambda user: user == "REDACTED_2c7b6821719d"
    )
    coordinator.register(RecoveryAction(
        "service.telegram.restart", "Reiniciar Telegram", lambda: calls.append(1)
    ))
    recommendation = coordinator.recommend(unhealthy())
    assert recommendation.action_id == "service.telegram.restart"
    assert calls == []


def test_recovery_denied_to_normal_user_and_without_confirmation(tmp_path):
    calls = []
    coordinator = RecoveryCoordinator(
        tmp_path / "recovery.json", is_owner=lambda user: user == "REDACTED_2c7b6821719d"
    )
    coordinator.register(RecoveryAction(
        "service.telegram.restart", "Reiniciar Telegram", lambda: calls.append(1)
    ))
    denied_user = coordinator.execute(
        "service.telegram.restart", requested_by="REDACTED_aebac53c46bb",
        confirmed=True, policy_allows=True,
    )
    denied_confirmation = coordinator.execute(
        "service.telegram.restart", requested_by="REDACTED_2c7b6821719d",
        confirmed=False, policy_allows=True,
    )
    assert not denied_user.authorized
    assert not denied_confirmation.authorized
    assert calls == []


def test_owner_can_execute_explicitly_authorized_recovery(tmp_path):
    coordinator = RecoveryCoordinator(
        tmp_path / "recovery.json", is_owner=lambda user: user.casefold() == "REDACTED_f73137d930c3"
    )
    coordinator.register(RecoveryAction(
        "service.telegram.restart", "Reiniciar Telegram", lambda: "reiniciado"
    ))
    result = coordinator.execute(
        "service.telegram.restart", requested_by="REDACTED_f73137d930c3",
        confirmed=True, policy_allows=True,
    )
    assert result.authorized and result.success
    assert result.result == "reiniciado"
    assert coordinator.history()[0]["requested_by"] == "REDACTED_f73137d930c3"


def test_health_history_rotates_and_tolerates_corruption(tmp_path):
    path = tmp_path / "health.json"
    store = HealthHistoryStore(path, max_entries=2)
    store.append_many([unhealthy(check_id="one"), unhealthy(check_id="two")])
    store.append_many([unhealthy(check_id="three")])
    assert [item["check_id"] for item in store.read()] == ["two", "three"]
    path.write_text("{corrupt", encoding="utf-8")
    assert store.read() == []
    store.append_many([unhealthy(check_id="new")])
    assert json.loads(path.read_text(encoding="utf-8"))[0]["check_id"] == "new"


def test_raspberry_details_become_uniform_docker_and_temperature_results():
    parent = HealthCheckResult(
        check_id="raspberry", display_name="Raspberry", state=HealthState.OK,
        available=True,
        details={"docker": {"service_active": False}, "temperature_c": 80},
    )
    results = {item.check_id: item for item in _raspberry_resource_results(parent)}
    assert results["docker"].status == "unavailable"
    assert results["docker"].recoverable
    assert results["temperature"].status == "degraded"
