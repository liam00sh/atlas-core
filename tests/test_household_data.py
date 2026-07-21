from core.household_data import (
    find_household,
    find_person_location,
    order_family_names,
    preferred_person_name,
)


def test_noa_household():
    household = find_household("Noa")
    assert household is not None
    assert household.people == (
        "Georgel Melinte",
        "Manoli Carreres López",
        "Noa Melinte Carreres",
    )


def test_liam_household_contains_people_and_animals():
    household = find_household("Liam")
    assert household is not None
    assert "María José Martínez Sanz" in household.people
    assert household.animals == ("Gato", "Funcio", "Lucas")


def test_raul_has_unnamed_flatmates_not_living_alone():
    household = find_household("Raúl")
    assert household is not None
    assert household.anonymous_companions == ("unos compañeros de piso",)


def test_cousins_are_grouped_by_family_branch():
    unordered = [
        "Salvador Amorós Vicente",
        "María Teresa Maestre Martínez",
        "Alba Martínez Pérez",
        "José Evaristo Maestre Martínez",
        "José Manuel Martínez Pérez",
        "Mario Amorós Vicente",
    ]
    assert order_family_names(unordered) == [
        "Alba Martínez Pérez",
        "José Manuel Martínez Pérez",
        "José Evaristo Maestre Martínez",
        "María Teresa Maestre Martínez",
        "Mario Amorós Vicente",
        "Salvador Amorós Vicente",
    ]


def test_conversational_names_are_short_and_unambiguous():
    assert preferred_person_name("Raúl Isidro Vicente Martínez") == "Raúl"
    assert preferred_person_name("Josefa Carreres López") == "Pepi"
    assert preferred_person_name("José Vicente") == "Pepe Vicente"
    assert preferred_person_name("José Vicente Navarro") == "José Vicente"


def test_locations_distinguish_origin_and_current_residence():
    saray = find_person_location("Saray")
    raul = find_person_location("Raúl")
    liam = find_person_location("Liam")
    assert saray is not None and saray.origin == "Caudete"
    assert saray.habitual_residence == "Alicante"
    assert saray.summer_residence == "Caudete"
    assert raul is not None and raul.origin == "Beneixama"
    assert raul.habitual_residence == "Barcelona"
    assert liam is not None and liam.origin == liam.habitual_residence == "Beneixama"
