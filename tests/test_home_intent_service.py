import random

from automation.home_intent_service import HomeIntentService
from automation.home_intent_resolver import HomeIntentType
from automation.stage_e_runtime import build_stage_e_simulation


def test_conversational_light_control(tmp_path):
    environment = build_stage_e_simulation(
        tmp_path / "automations.json"
    )
    service = HomeIntentService(environment)

    response = service.handle(
        "Enciende la luz virtual",
        user_id="Alex",
        channel="test",
    )

    assert response.handled is True
    assert response.message == "He encendido la luz virtual Atlas."


def test_conversational_temperature(tmp_path):
    environment = build_stage_e_simulation(
        tmp_path / "automations.json"
    )
    service = HomeIntentService(environment)

    response = service.handle(
        "¿Qué temperatura marca el sensor?",
        user_id="Alex",
        channel="test",
    )

    assert response.handled is True
    assert "22.5" in response.message


def test_switch_executes_without_confirmation(tmp_path):
    environment = build_stage_e_simulation(
        tmp_path / "automations.json"
    )
    service = HomeIntentService(environment)

    response = service.handle(
        "Enciende el enchufe virtual",
        user_id="Alex",
        channel="test",
    )

    assert response.handled is True
    assert response.requires_confirmation is False


def test_absent_guest_gets_daxter_coco_style_message(tmp_path):
    environment = build_stage_e_simulation(
        tmp_path / "automations.json",
        guest_user_ids=("Vega",),
    )
    service = HomeIntentService(
        environment,
        random_source=random.Random(7),
    )

    response = service.handle(
        "¿Qué temperatura marca el sensor?",
        user_id="Vega",
        channel="test",
    )

    assert response.handled is True
    assert response.message
    assert "No tienes permisos para usar los dispositivos" not in response.message
    assert any(
        name in response.message
        for name in ("Daxter", "Coco", "casa", "sensor")
    )


def test_absent_guest_message_does_not_repeat_immediately(tmp_path):
    environment = build_stage_e_simulation(
        tmp_path / "automations.json",
        guest_user_ids=("Vega",),
    )
    service = HomeIntentService(
        environment,
        random_source=random.Random(3),
    )

    first = service.handle(
        "¿Qué temperatura marca el sensor?",
        user_id="Vega",
        channel="test",
    )
    second = service.handle(
        "¿Qué temperatura marca el sensor?",
        user_id="Vega",
        channel="test",
    )

    assert first.message != second.message


def test_success_message_adds_del_for_aquarium_light():
    result = {
        "state": "on",
        "attributes": {"friendly_name": "Luz acuario pequeño"},
    }
    message = HomeIntentService._success_message(
        HomeIntentType.TURN_ON_SWITCH,
        result,
    )
    assert message == "He encendido la luz del acuario pequeño."
