import pytest

from automation.home_assistant_client import HomeAssistantHttpClient
from automation.home_assistant_factory import (
    create_home_assistant_client,
    load_home_assistant_settings,
)
from automation.home_assistant_simulator import HomeAssistantSimulator


def test_factory_builds_simulator_by_default():
    settings = load_home_assistant_settings({})
    assert isinstance(create_home_assistant_client(settings), HomeAssistantSimulator)


def test_factory_builds_real_client():
    settings = load_home_assistant_settings(
        {
            "HOME_ASSISTANT_MODE": "real",
            "HOME_ASSISTANT_URL": "http://192.168.1.31:8123",
            "HOME_ASSISTANT_TOKEN": "secret",
            "HOME_ASSISTANT_TIMEOUT": "10",
            "HOME_ASSISTANT_VERIFY_SSL": "false",
        }
    )
    client = create_home_assistant_client(settings)
    assert isinstance(client, HomeAssistantHttpClient)
    assert client.verify_ssl is False


def test_real_mode_requires_url_and_token():
    with pytest.raises(ValueError):
        load_home_assistant_settings({"HOME_ASSISTANT_MODE": "real"})
