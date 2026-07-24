from automation.home_intent_resolver import HomeIntentResolver, HomeIntentType


def test_schedule_small_aquarium_light_with_colons():
    intent = HomeIntentResolver().resolve(
        "Programa la luz del acuario pequeño de 23:49 a 23:50"
    )
    assert intent is not None
    assert intent.intent_type == HomeIntentType.SCHEDULE_SWITCH
    assert intent.parameters["entity_id"] == (
        "switch.despacho_acuario_pequeno_luz_acuario_pequeno"
    )
    assert intent.parameters["start_time"] == "23:49:00"
    assert intent.parameters["end_time"] == "23:50:00"


def test_schedule_small_aquarium_after_normalization():
    intent = HomeIntentResolver().resolve(
        "programa la luz del acuario pequeno de 23 49 a 23 50"
    )
    assert intent is not None
    assert intent.intent_type == HomeIntentType.SCHEDULE_SWITCH
    assert intent.parameters["start_time"] == "23:49:00"
    assert intent.parameters["end_time"] == "23:50:00"


def test_schedule_large_aquarium_light():
    intent = HomeIntentResolver().resolve(
        "Programa la luz del acuario grande de 11:30 a 17:00"
    )
    assert intent is not None
    assert intent.intent_type == HomeIntentType.SCHEDULE_SWITCH
    assert intent.parameters["entity_id"] == (
        "switch.salon_acuario_grande_luz_acuario_grande"
    )


def test_enable_schedule():
    intent = HomeIntentResolver().resolve("Activa el horario del acuario")
    assert intent is not None
    assert intent.intent_type == HomeIntentType.ENABLE_SCHEDULE


def test_disable_schedule_small_aquarium():
    intent = HomeIntentResolver().resolve(
        "Desactiva la programación de la luz del acuario pequeño"
    )
    assert intent is not None
    assert intent.intent_type == HomeIntentType.DISABLE_SCHEDULE
    assert intent.parameters["entity_id"] == (
        "switch.despacho_acuario_pequeno_luz_acuario_pequeno"
    )
