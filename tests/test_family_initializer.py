"""Pruebas genéricas del inicializador de datos privados."""

from identity.family_data import FAMILY_ANIMALS, FAMILY_PEOPLE, FAMILY_RELATIONSHIPS
from identity.family_initializer import FamilyInitializer
from identity.identity_storage import IdentityStorage
from identity.people_manager import PeopleManager
from identity.relationship_engine import RelationshipEngine


def _initializer(path):
    storage = IdentityStorage(path)
    people = PeopleManager(storage)
    engine = RelationshipEngine(people, storage)
    return FamilyInitializer(people, engine), people, engine


def test_first_run_populates_and_second_run_is_idempotent(tmp_path):
    initializer, people, engine = _initializer(tmp_path)
    assert initializer.initialize() == {
        "created_people": len(FAMILY_PEOPLE),
        "created_animals": len(FAMILY_ANIMALS),
        "created_relationships": len(FAMILY_RELATIONSHIPS) * 2,
    }
    assert initializer.initialize() == {
        "created_people": 0,
        "created_animals": 0,
        "created_relationships": 0,
    }
    assert people.get_person_count() == len(FAMILY_PEOPLE)
    assert people.get_animal_count() == len(FAMILY_ANIMALS)
    assert engine.get_relationship_count() == len(FAMILY_RELATIONSHIPS) * 2


def test_reloading_storage_remains_idempotent(tmp_path):
    initializer, _, _ = _initializer(tmp_path)
    initializer.initialize()
    reloaded, _, _ = _initializer(tmp_path)
    assert reloaded.initialize() == {
        "created_people": 0,
        "created_animals": 0,
        "created_relationships": 0,
    }


def test_declared_alias_resolves_to_single_example_person(tmp_path):
    initializer, people, _ = _initializer(tmp_path)
    initializer.initialize()
    canonical = people.find_person_by_name("Alex Romero")
    alias = people.find_person_by_name("Alias Anterior Ejemplo")
    assert canonical is not None and alias is not None
    assert canonical.id == alias.id
