from automation.home_intent_resolver import HomeIntentResolver, HomeIntentType


def test_schedule_small_aquarium_light():
    intent = HomeIntentResolver().resolve(
        "Programa la luz del acuario pequeño de 10:33 a 10:34"
    )
    assert intent is not None
    assert intent.intent_type == HomeIntentType.SCHEDULE_SWITCH
    assert intent.parameters["start_time"] == "10:33:00"
    assert intent.parameters["end_time"] == "10:34:00"


def test_duration_small_aquarium_minutes():
    intent = HomeIntentResolver().resolve(
        "Enciende la luz del acuario pequeño durante 30 minutos"
    )
    assert intent is not None
    assert intent.intent_type == HomeIntentType.TURN_ON_FOR_DURATION
    assert intent.parameters["entity_id"] == (
        "switch.despacho_acuario_pequeno_luz_acuario_pequeno"
    )
    assert intent.parameters["duration_minutes"] == "30"


def test_duration_large_aquarium_hours():
    intent = HomeIntentResolver().resolve(
        "Enciende la luz del acuario grande durante 2 horas"
    )
    assert intent is not None
    assert intent.intent_type == HomeIntentType.TURN_ON_FOR_DURATION
    assert intent.parameters["duration_minutes"] == "120"


def test_enable_schedule_small_aquarium():
    intent = HomeIntentResolver().resolve(
        "Activa el horario del acuario pequeño"
    )
    assert intent is not None
    assert intent.intent_type == HomeIntentType.ENABLE_SCHEDULE


def test_disable_schedule_small_aquarium():
    intent = HomeIntentResolver().resolve(
        "Desactiva la programación de la luz del acuario pequeño"
    )
    assert intent is not None
    assert intent.intent_type == HomeIntentType.DISABLE_SCHEDULE
