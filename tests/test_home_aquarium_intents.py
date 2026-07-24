from automation.home_intent_resolver import HomeIntentResolver, HomeIntentType


def test_real_aquarium_intents():
    resolver = HomeIntentResolver()

    light = resolver.resolve("Enciende la luz del acuario grande")
    assert light is not None
    assert light.parameters["entity_id"] == "switch.salon_acuario_grande_luz_acuario_grande"

    oxygen = resolver.resolve("Apaga el oxígeno del acuario pequeño")
    assert oxygen is not None
    assert oxygen.parameters["entity_id"] == "switch.despacho_acuario_pequeno_oxigeno_acuario_pequeno"

    group = resolver.resolve("Apaga el acuario pequeño")
    assert group is not None
    assert group.intent_type == HomeIntentType.TURN_OFF_GROUP
    assert "switch.despacho_acuario_pequeno_luz_acuario_pequeno" in group.parameters["entity_ids"]
    assert "switch.despacho_acuario_pequeno_oxigeno_acuario_pequeno" in group.parameters["entity_ids"]


def test_resolver_accepts_common_typo_eniende():
    resolver = HomeIntentResolver()
    intent = resolver.resolve("eniende la luz del acuario pequeño")
    assert intent is not None
    assert intent.intent_type == HomeIntentType.TURN_ON_SWITCH
    assert intent.parameters["entity_id"] == (
        "switch.despacho_acuario_pequeno_luz_acuario_pequeno"
    )
