from automation.home_assistant_adapter import HomeAssistantAdapter
from automation.home_assistant_models import (
    HomeEntityDefinition, HomeEntityKind, HomeEntityMode, HomeEntityRisk, HomeEntityState,
)
from automation.home_device_registry import HomeDeviceRegistry


class _DelayedTransport:
    def __init__(self):
        self.states = ["off", "off", "on"]

    def call_service(self, *_args, entity_id, **_kwargs):
        return HomeEntityState(entity_id, "off", {})

    def get_state(self, entity_id):
        state = self.states.pop(0) if len(self.states) > 1 else self.states[0]
        return HomeEntityState(entity_id, state, {"friendly_name": "Luz acuario"})


def test_adapter_tolerates_the_observed_250ms_stale_window():
    registry = HomeDeviceRegistry()
    registry.register(HomeEntityDefinition(
        entity_id="switch.test",
        name="Luz acuario",
        kind=HomeEntityKind.SWITCH,
        mode=HomeEntityMode.PHYSICAL,
        risk=HomeEntityRisk.MEDIUM,
        allowed_services=frozenset({"turn_on", "turn_off"}),
        required_permission="home.control.switch",
    ))
    sleeps = []
    adapter = HomeAssistantAdapter(_DelayedTransport(), registry, sleep=sleeps.append)
    result = adapter.turn_on("switch.test")
    assert result["state"] == "on"
    assert sleeps == [0.25, 0.25]
    assert [item["state"]["state"] for item in result["atlas_trace"]["observations"]] == ["off", "off", "on"]
