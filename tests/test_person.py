"""Pruebas unitarias para identity.person."""

import unittest

from identity.person import Person
from identity.person_status import GUEST, USER


class PersonTests(unittest.TestCase):
    def test_normalizes_name_aliases_and_summary(self):
        person = Person(
            name="  Liam Vicente Martínez  ",
            aliases=["Liam", " liam ", "", "Nerea Vicente"],
            summary="  Usuario principal  ",
        )
        self.assertEqual(person.name, "Liam Vicente Martínez")
        self.assertEqual(person.aliases, ["Liam", "Nerea Vicente"])
        self.assertEqual(person.summary, "Usuario principal")
        self.assertTrue(person.matches_name("liam"))
        self.assertTrue(person.matches_name("NEREA VICENTE"))

    def test_rejects_invalid_data(self):
        with self.assertRaises(ValueError):
            Person(name="")
        with self.assertRaises(ValueError):
            Person(name="Liam", status="invalid")
        with self.assertRaises(ValueError):
            Person(name="Liam", encounter_count=-1)
        with self.assertRaises(ValueError):
            Person(name="Liam", status=USER)

    def test_alias_encounters_and_serialization(self):
        person = Person(name="Saray", status=GUEST)
        self.assertTrue(person.add_alias("Sara"))
        self.assertFalse(person.add_alias("sara"))
        person.register_encounter("2026-07-14T12:00:00")
        self.assertEqual(person.encounter_count, 1)
        restored = Person.from_dict(person.to_dict())
        self.assertEqual(restored.to_dict(), person.to_dict())

    def test_linking_user_profile_sets_user_status(self):
        person = Person(name="Saray")
        person.link_user_profile("Saray")
        self.assertTrue(person.is_user())
        self.assertEqual(person.status, USER)
        self.assertEqual(person.user_profile, "Saray")


if __name__ == "__main__":
    unittest.main()
