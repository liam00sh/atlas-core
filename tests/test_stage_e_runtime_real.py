from automation.home_assistant_client import HomeAssistantHttpClient
from automation.home_intent_resolver import HomeIntentResolver
from automation.stage_e_runtime import build_stage_e_environment


def test_real_runtime_uses_closed_lab_catalog(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "HOME_ASSISTANT_MODE=real",
                "HOME_ASSISTANT_URL=http://192.168.1.31:8123",
                "HOME_ASSISTANT_TOKEN=secret",
                "HOME_ASSISTANT_TIMEOUT=10",
                "HOME_ASSISTANT_VERIFY_SSL=false",
            ]
        ),
        encoding="utf-8",
    )
    env = build_stage_e_environment(tmp_path / "automations.json", env_file=env_file)
    assert isinstance(env.client, HomeAssistantHttpClient)
    assert env.simulator is None
    assert env.device_registry.get("light.atlas_light_lab").entity_id == "light.atlas_light_lab"
    resolver = HomeIntentResolver.from_device_registry(env.device_registry)
    intent = resolver.resolve("Enciende la luz")
    assert intent.parameters["entity_id"] == "light.atlas_light_lab"
