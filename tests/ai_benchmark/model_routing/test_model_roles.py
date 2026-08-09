import pytest

from ai.models.roles import ModelRole, ModelRoleRegistry, RoleModelDefinition


def test_physical_names_are_centralized_behind_roles():
    models = ModelRoleRegistry().as_dict()
    assert models["fast"]["model"] == "qwen2.5:7b"
    assert models["reasoning"]["model"] == "qwen2.5:14b"
    assert models["deep"]["model"] == "qwen3:30b"
    assert models["external"] == {
        "provider": "disabled",
        "model": None,
        "enabled": False,
    }


def test_external_cannot_be_enabled_in_this_phase():
    with pytest.raises(ValueError, match="external"):
        RoleModelDefinition(ModelRole.EXTERNAL, "paid-api", "remote", enabled=True)

