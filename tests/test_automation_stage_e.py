from automation.models import AutomationStatus
from automation.stage_e_runtime import build_stage_e_simulation


def test_stage_e_catalog_and_devices(tmp_path):
    env = build_stage_e_simulation(tmp_path / "automations.json")
    assert env.action_registry.count == 6
    assert env.device_registry.count == 3
    assert env.adapter.health()["available"] is True


def test_read_virtual_sensor(tmp_path):
    env = build_stage_e_simulation(tmp_path / "automations.json")
    automation = env.manager.create(
        action_id="home.state.read",
        owner_user_id="Alex",
        creator_user_id="Alex",
        parameters={"entity_id": "sensor.atlas_temperature"},
    )
    result = env.manager.execute(
        automation.automation_id,
        requested_by_user_id="Alex",
        channel="test",
    )
    assert result.success is True
    assert result.result["state"] == "22.5"


def test_virtual_light_does_not_require_confirmation(tmp_path):
    env = build_stage_e_simulation(tmp_path / "automations.json")
    automation = env.manager.create(
        action_id="home.light.turn_on",
        owner_user_id="Alex",
        creator_user_id="Alex",
        parameters={"entity_id": "light.atlas_virtual"},
    )
    result = env.manager.execute(
        automation.automation_id,
        requested_by_user_id="Alex",
        channel="test",
    )
    assert result.success is True
    assert result.result["state"] == "on"


def test_virtual_switch_executes_without_confirmation(tmp_path):
    env = build_stage_e_simulation(tmp_path / "automations.json")
    automation = env.manager.create(
        action_id="home.switch.turn_on",
        owner_user_id="Alex",
        creator_user_id="Alex",
        parameters={"entity_id": "switch.atlas_virtual"},
    )
    first = env.manager.execute(
        automation.automation_id,
        requested_by_user_id="Alex",
        channel="test",
    )
    assert first.success is True
    assert first.status == AutomationStatus.COMPLETED
    assert first.error_code is None

    confirmed = env.manager.execute(
        automation.automation_id,
        requested_by_user_id="Alex",
        channel="test",
        confirmed=True,
    )
    assert confirmed.success is True
    assert confirmed.result["state"] == "on"


def test_guest_cannot_control_light(tmp_path):
    env = build_stage_e_simulation(tmp_path / "automations.json")
    automation = env.manager.create(
        action_id="home.light.turn_on",
        owner_user_id="Alex",
        creator_user_id="Alex",
        parameters={"entity_id": "light.atlas_virtual"},
        shared_user_ids=["guest"],
    )
    result = env.manager.execute(
        automation.automation_id,
        requested_by_user_id="guest",
        channel="test",
    )
    assert result.success is False
    assert result.error_code == "permission_denied"


def test_unknown_entity_is_rejected_and_audited_as_failure(tmp_path):
    env = build_stage_e_simulation(tmp_path / "automations.json")
    automation = env.manager.create(
        action_id="home.state.read",
        owner_user_id="Alex",
        creator_user_id="Alex",
        parameters={"entity_id": "lock.front_door"},
    )
    result = env.manager.execute(
        automation.automation_id,
        requested_by_user_id="Alex",
        channel="test",
    )
    assert result.success is False
    assert result.status == AutomationStatus.FAILED
    assert "no está autorizada" in result.error_message


def test_sensor_cannot_be_written(tmp_path):
    env = build_stage_e_simulation(tmp_path / "automations.json")
    automation = env.manager.create(
        action_id="home.light.turn_on",
        owner_user_id="Alex",
        creator_user_id="Alex",
        parameters={"entity_id": "sensor.atlas_temperature"},
    )
    result = env.manager.execute(
        automation.automation_id,
        requested_by_user_id="Alex",
        channel="test",
    )
    assert result.success is False
    assert result.status == AutomationStatus.FAILED


def test_audit_redacts_secrets(tmp_path):
    env = build_stage_e_simulation(tmp_path / "automations.json")
    automation = env.manager.create(
        action_id="home.light.turn_on",
        owner_user_id="Alex",
        creator_user_id="Alex",
        parameters={
            "entity_id": "light.atlas_virtual",
            "service_data": {"token": "secret-value", "brightness": 80},
        },
    )
    env.manager.execute(
        automation.automation_id,
        requested_by_user_id="Alex",
        channel="test",
    )
    events = env.manager.audit.read_all()
    assert events
