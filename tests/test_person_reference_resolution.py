"""
Regresiones para referencias personales compuestas y estilo de respuestas.
"""

import unittest
from types import SimpleNamespace

from core.atlas_ai import AtlasAIMixin


def _person(identifier, name, aliases=None):
    return SimpleNamespace(
        id=identifier,
        name=name,
        aliases=list(aliases or []),
    )


class _PeopleManager:
    def __init__(self):
        self._people = [
            _person("zs", "Zoe Soler", ["Zoe", "Luz"]),
            _person("zv", "Zoe Vidal", ["Zoe", "Luz"]),
            _person("mr", "Marcos Río", ["Marco"]),
            _person("si", "Vega Ferrer", ["Vega"]),
        ]

    def get_people(self):
        return list(self._people)


class _IdentityManager:
    def __init__(self, identity, mode):
        self.identity = identity
        self.mode = mode

    def get_active_display_name(self):
        return self.identity

    def get_active_mode_name(self):
        return self.mode


class PersonReferenceResolutionTests(unittest.TestCase):

    def setUp(self):
        self.atlas = AtlasAIMixin()
        self.atlas.people_manager = _PeopleManager()

    def names(self, query):
        return [
            person.name
            for person in self.atlas._people_matching_reference(query)
        ]

    def test_unique_alias_resolves_one_person(self):
        self.assertEqual(
            self.names("Marco"),
            ["Marcos Río"],
        )

    def test_shared_alias_lists_all_matches(self):
        names = self.names("Zoe")
        self.assertEqual(len(names), 2)
        self.assertIn("Zoe Soler", names)
        self.assertIn("Zoe Vidal", names)

    def test_full_name_resolves_exact_person(self):
        self.assertEqual(
            self.names("Zoe Soler"),
            ["Zoe Soler"],
        )

    def test_non_contiguous_names_are_not_treated_as_verified_aliases(self):
        self.assertEqual(self.names("Zoe Río"), [])
        self.assertEqual(self.names("Marco Soler"), [])

    def test_Marco_does_not_match_Vega(self):
        self.assertEqual(self.names("Marco"), ["Marcos Río"])
        self.assertEqual(
            self.names("Vega"),
            ["Vega Ferrer"],
        )

    def test_shared_name_and_alias_remain_ambiguous(self):
        self.assertEqual(len(self.names("Zoe")), 2)
        self.assertEqual(len(self.names("Luz")), 2)

    def test_unverified_partial_reference_is_not_rewritten(self):
        rewritten, handled = self.atlas._prepare_entity_clarification(
            "quien es Marco Vidal"
        )
        self.assertFalse(handled)
        self.assertEqual(rewritten, "quien es Marco Vidal")
        self.assertFalse(hasattr(self.atlas, "_resolved_entity_id"))


class VerifiedResponseStyleTests(unittest.TestCase):

    def test_daxter_classic_biography_style(self):
        atlas = AtlasAIMixin()
        atlas.identity_manager = _IdentityManager("Daxter", "classic")
        styled = atlas._style_verified_response(
            "Marco es el bibliotecario.",
            response_kind="biography",
        )
        self.assertEqual(
            styled,
            "Vale, te pongo en situación: Marco es el bibliotecario.",
        )

    def test_coco_classic_style(self):
        atlas = AtlasAIMixin()
        atlas.identity_manager = _IdentityManager("Coco", "classic")
        styled = atlas._style_verified_response(
            "Marco es el bibliotecario.",
            response_kind="biography",
        )
        self.assertTrue(styled.startswith("Claro, te cuento:"))

    def test_work_mode_is_factual_for_both_identities(self):
        atlas = AtlasAIMixin()
        atlas.identity_manager = _IdentityManager("Daxter", "work")
        styled = atlas._style_verified_response(
            "Carla es familiar de Alex.",
            response_kind="relationship",
        )
        self.assertTrue(
            styled.startswith("Vamos con los datos verificados:")
        )


if __name__ == "__main__":
    unittest.main()
