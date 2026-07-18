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
            _person("jvn", "José Vicente Navarro", ["Padre de Liam"]),
            _person("jmmp", "José Manuel Martínez Pérez", ["Txipi", "José Manuel"]),
            _person("jv", "José Vicente", ["Pepe", "Pepe Vicente"]),
            _person("jemm", "José Evaristo Maestre Martínez", ["José Evaristo"]),
            _person("jmic", "José Miguel Izquierdo Catalán", ["José Miguel", "Jose"]),
            _person("pvn", "Pepi Vicente Navarro", ["Pepi", "Pepa"]),
            _person("pcl", "Pepi Carreres López", ["Pepi", "Pepa"]),
            _person("sa", "Sara", ["Sara, pareja de Txipi"]),
            _person("si", "Saray Izquierdo Carreres", ["Saray"]),
            _person("saa", "Salvador Amorós"),
            _person("sav", "Salvador Amorós Vicente"),
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

    def test_jose_miguel_is_unique(self):
        self.assertEqual(
            self.names("José Miguel"),
            ["José Miguel Izquierdo Catalán"],
        )

    def test_jose_alone_lists_all_jose(self):
        names = self.names("José")
        self.assertEqual(len(names), 5)
        self.assertIn("José Miguel Izquierdo Catalán", names)
        self.assertIn("José Vicente Navarro", names)

    def test_jose_vicente_includes_exact_and_longer_name(self):
        self.assertEqual(
            set(self.names("José Vicente")),
            {"José Vicente", "José Vicente Navarro"},
        )

    def test_jose_martinez_prefers_closest_ordered_match(self):
        self.assertEqual(
            self.names("José Martínez"),
            ["José Manuel Martínez Pérez"],
        )

    def test_sara_does_not_match_saray(self):
        self.assertEqual(self.names("Sara"), ["Sara"])
        self.assertEqual(
            self.names("Saray"),
            ["Saray Izquierdo Carreres"],
        )

    def test_pepi_and_salvador_remain_ambiguous(self):
        self.assertEqual(len(self.names("Pepi")), 2)
        self.assertEqual(len(self.names("Salvador")), 2)

    def test_unique_partial_reference_is_rewritten_to_canonical_name(self):
        rewritten, handled = self.atlas._prepare_entity_clarification(
            "quien es jose martinez"
        )
        self.assertFalse(handled)
        self.assertIn("José Manuel Martínez Pérez", rewritten)
        self.assertEqual(
            self.atlas._resolved_entity_id,
            "jmmp",
        )


class VerifiedResponseStyleTests(unittest.TestCase):

    def test_daxter_classic_biography_style(self):
        atlas = AtlasAIMixin()
        atlas.identity_manager = _IdentityManager("Daxter", "classic")
        styled = atlas._style_verified_response(
            "José Miguel es el padre de Saray.",
            response_kind="biography",
        )
        self.assertEqual(
            styled,
            "Vale, te pongo en situación: José Miguel es el padre de Saray.",
        )

    def test_coco_classic_style(self):
        atlas = AtlasAIMixin()
        atlas.identity_manager = _IdentityManager("Coco", "classic")
        styled = atlas._style_verified_response(
            "José Miguel es el padre de Saray.",
            response_kind="biography",
        )
        self.assertTrue(styled.startswith("Claro, te cuento:"))

    def test_work_mode_is_factual_for_both_identities(self):
        atlas = AtlasAIMixin()
        atlas.identity_manager = _IdentityManager("Daxter", "work")
        styled = atlas._style_verified_response(
            "La madre de Saray es Pepi Carreres López.",
            response_kind="relationship",
        )
        self.assertTrue(
            styled.startswith("Vamos con los datos verificados:")
        )


if __name__ == "__main__":
    unittest.main()
