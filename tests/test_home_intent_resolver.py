from automation.home_intent_resolver import (
    HomeIntentResolver,
    HomeIntentType,
)


def test_turn_on_virtual_light():
    resolver = HomeIntentResolver()

    result = resolver.resolve("Enciende la luz virtual")

    assert result is not None
    assert result.intent_type == HomeIntentType.TURN_ON_LIGHT
    assert result.action_id == "home.light.turn_on"
    assert result.parameters["entity_id"] == "light.atlas_virtual"


def test_turn_off_virtual_light():
    resolver = HomeIntentResolver()

    result = resolver.resolve("Apaga la luz virtual")

    assert result is not None
    assert result.intent_type == HomeIntentType.TURN_OFF_LIGHT


def test_read_temperature():
    resolver = HomeIntentResolver()

    result = resolver.resolve("¿Qué temperatura marca el sensor?")

    assert result is not None
    assert result.intent_type == HomeIntentType.READ_TEMPERATURE


def test_unrelated_text_is_not_handled():
    resolver = HomeIntentResolver()

    result = resolver.resolve("Cuéntame una historia")

    assert result is None