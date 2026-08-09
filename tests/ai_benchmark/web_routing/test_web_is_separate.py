from core.atlas_ai import AtlasAIMixin


def test_current_external_fact_is_routed_to_web_policy_not_model_level():
    assert AtlasAIMixin._requires_external_verification(
        "¿Cuál es la población actual de REDACTED_a77d7bb7adbf?"
    ) is True


def test_creative_local_request_does_not_require_web():
    assert AtlasAIMixin._requires_external_verification(
        "Escribe un saludo corto para REDACTED_bc04a68d9192"
    ) is False

