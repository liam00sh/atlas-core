from automation.home_assistant_models import HomeEntityState
from tools.diagnose_home_assistant_entity import DELAYS, resolve_alias, sample_after_service


class FakeClient:
    def __init__(self):
        self.calls = []
    def call_service(self, domain, service, *, entity_id):
        self.calls.append((domain, service, entity_id))
        return HomeEntityState(entity_id, "on" if service == "turn_on" else "off")
    def get_state(self, entity_id):
        return HomeEntityState(entity_id, "on")


def test_alias_and_all_required_delays_are_used_even_if_state_matches():
    resolved = resolve_alias("luz del acuario pequeño")
    client = FakeClient()
    result = sample_after_service(client, resolved["entity_id"], "turn_on", sleep=lambda _: None)
    assert client.calls == [("switch", "turn_on", resolved["entity_id"])]
    assert [row["delay_seconds"] for row in result["api_samples"]] == list(DELAYS)
