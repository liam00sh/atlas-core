"""Contrato sintético de hogares y ubicaciones privadas."""

from core.household_data import (
    HOUSEHOLDS,
    find_household,
    find_person_location,
    order_family_names,
    preferred_person_name,
)


def test_example_household_can_be_resolved_by_alias_and_member():
    household = find_household("casa principal")
    assert household is not None
    assert household.key == "casa_ejemplo"
    assert find_household("Alex Romero") == household
    assert find_household("Nube") == household


def test_example_location_is_separate_from_identity():
    location = find_person_location("Vega")
    assert location is not None
    assert location.person == "Vega Ferrer"
    assert location.habitual_residence == "Provincia Ejemplo"


def test_preferred_names_and_order_are_deterministic():
    assert preferred_person_name("Alex Romero") == "Alex"
    assert order_family_names(["Diego Romero", "Carla Romero", "Vega Ferrer"]) == [
        "Carla Romero",
        "Diego Romero",
        "Vega Ferrer",
    ]


def test_public_fixture_is_small_and_explicitly_fictitious():
    assert 1 <= len(HOUSEHOLDS) <= 4
    assert all("fictici" in (household.label + " " + household.tenure).casefold() for household in HOUSEHOLDS)
