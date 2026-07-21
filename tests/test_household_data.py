from core.household_data import (
    find_household,
    find_person_location,
    order_family_names,
    preferred_person_name,
)


def test_REDACTED_7467b914d771_household():
    household = find_household("REDACTED_d296a64095dd")
    assert household is not None
    assert household.people == (
        "REDACTED_3ae65da8646e",
        "REDACTED_7ac2d8ee0281",
        "REDACTED_91f6198b34bc",
    )


def test_REDACTED_f73137d930c3_household_contains_people_and_animals():
    household = find_household("REDACTED_2c7b6821719d")
    assert household is not None
    assert "REDACTED_ba2c2b03ba9a" in household.people
    assert household.animals == ("REDACTED_a9baf529fb36", "REDACTED_0f38c2ded26f", "REDACTED_52d7d8604bf7")


def test_raul_has_unnamed_flatmates_not_living_alone():
    household = find_household("REDACTED_de9c80449aae")
    assert household is not None
    assert household.anonymous_companions == ("unos compañeros de piso",)


def test_cousins_are_grouped_by_family_branch():
    unordered = [
        "REDACTED_103e3365dd76",
        "REDACTED_2130eea91209",
        "REDACTED_a57a306cce03",
        "REDACTED_8f775d9efc06",
        "REDACTED_516d7f9914e7",
        "REDACTED_aff1bed113aa",
    ]
    assert order_family_names(unordered) == [
        "REDACTED_a57a306cce03",
        "REDACTED_516d7f9914e7",
        "REDACTED_8f775d9efc06",
        "REDACTED_2130eea91209",
        "REDACTED_aff1bed113aa",
        "REDACTED_103e3365dd76",
    ]


def test_conversational_names_are_short_and_unambiguous():
    assert preferred_person_name("REDACTED_d3969f681ba1") == "REDACTED_de9c80449aae"
    assert preferred_person_name("REDACTED_38b7adc65154") == "REDACTED_342ad0893cb2"
    assert preferred_person_name("REDACTED_fd70e667da43") == "REDACTED_c116c5ff0ef3"
    assert preferred_person_name("REDACTED_0a0e53340b75") == "REDACTED_fd70e667da43"


def test_locations_distinguish_origin_and_current_residence():
    REDACTED_7b9528898599 = find_person_location("REDACTED_bc04a68d9192")
    raul = find_person_location("REDACTED_de9c80449aae")
    REDACTED_f73137d930c3 = find_person_location("REDACTED_2c7b6821719d")
    assert REDACTED_7b9528898599 is not None and REDACTED_7b9528898599.origin == "REDACTED_039ed2c608a5"
    assert REDACTED_7b9528898599.habitual_residence == "REDACTED_4cde1bf18b9c"
    assert REDACTED_7b9528898599.summer_residence == "REDACTED_039ed2c608a5"
    assert raul is not None and raul.origin == "REDACTED_a77d7bb7adbf"
    assert raul.habitual_residence == "Barcelona"
    assert REDACTED_f73137d930c3 is not None and REDACTED_f73137d930c3.origin == REDACTED_f73137d930c3.habitual_residence == "REDACTED_a77d7bb7adbf"
