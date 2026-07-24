from automation.home_intent_resolver import HomeIntentResolver


def test_real_aquarium_entities_are_resolved():
    resolver = HomeIntentResolver()

    cases = {
        "Enciende la luz del acuario grande": (
            "home.switch.turn_on",
            "switch.salon_acuario_grande_luz_acuario_grande",
        ),
        "Apaga la luz del acuario pequeño": (
            "home.switch.turn_off",
            "switch.despacho_acuario_pequeno_luz_acuario_pequeno",
        ),
        "Enciende el oxígeno del acuario pequeño": (
            "home.switch.turn_on",
            "switch.despacho_acuario_pequeno_oxigeno_acuario_pequeno",
        ),
    }

    for text, expected in cases.items():
        intent = resolver.resolve(text)
        assert intent is not None
        assert intent.action_id == expected[0]
        assert intent.parameters["entity_id"] == expected[1]
