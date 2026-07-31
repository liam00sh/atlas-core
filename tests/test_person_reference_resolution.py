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
            _person("jvn", "REDACTED_0a0e53340b75", ["REDACTED_f3ddd50afbeb"]),
            _person("jmmp", "REDACTED_516d7f9914e7", ["REDACTED_2ff76a67ecfb", "REDACTED_c792e277ccc5"]),
            _person("jv", "REDACTED_fd70e667da43", ["REDACTED_e09b6c1fc25a", "REDACTED_c116c5ff0ef3"]),
            _person("jemm", "REDACTED_8f775d9efc06", ["REDACTED_b79a0304ba32"]),
            _person("jmic", "REDACTED_020164a43a4e", ["REDACTED_77c013518681", "REDACTED_ae978aa10c62"]),
            _person("pvn", "REDACTED_32885d880536", ["REDACTED_342ad0893cb2", "REDACTED_2c910d64bd54"]),
            _person("pcl", "REDACTED_e3b252570a2f", ["REDACTED_342ad0893cb2", "REDACTED_2c910d64bd54"]),
            _person("sa", "REDACTED_53b1fb446230", ["REDACTED_f7f7fd06a965"]),
            _person("si", "REDACTED_8762331d93e2", ["REDACTED_bc04a68d9192"]),
            _person("saa", "REDACTED_54558996de60"),
            _person("sav", "REDACTED_103e3365dd76"),
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

    def test_REDACTED_1ec4ed037766_miguel_is_unique(self):
        self.assertEqual(
            self.names("REDACTED_77c013518681"),
            ["REDACTED_020164a43a4e"],
        )

    def test_REDACTED_1ec4ed037766_alone_lists_all_REDACTED_1ec4ed037766(self):
        names = self.names("José")
        self.assertEqual(len(names), 5)
        self.assertIn("REDACTED_020164a43a4e", names)
        self.assertIn("REDACTED_0a0e53340b75", names)

    def test_REDACTED_1ec4ed037766_vicente_includes_exact_and_longer_name(self):
        self.assertEqual(
            set(self.names("REDACTED_fd70e667da43")),
            {"REDACTED_fd70e667da43", "REDACTED_0a0e53340b75"},
        )

    def test_non_contiguous_names_are_not_treated_as_verified_aliases(self):
        self.assertEqual(self.names("José REDACTED_6311e2faf08cez"), [])
        self.assertEqual(self.names("Salvador Vicente"), [])

    def test_REDACTED_3a6d64c24cf8_does_not_match_REDACTED_7b9528898599(self):
        self.assertEqual(self.names("REDACTED_53b1fb446230"), ["REDACTED_53b1fb446230"])
        self.assertEqual(
            self.names("REDACTED_bc04a68d9192"),
            ["REDACTED_8762331d93e2"],
        )

    def test_REDACTED_e899cf89ab27_and_salvador_remain_ambiguous(self):
        self.assertEqual(len(self.names("REDACTED_342ad0893cb2")), 2)
        self.assertEqual(len(self.names("Salvador")), 2)

    def test_unverified_partial_reference_is_not_rewritten(self):
        rewritten, handled = self.atlas._prepare_entity_clarification(
            "quien es REDACTED_1ec4ed037766 martinez"
        )
        self.assertFalse(handled)
        self.assertEqual(rewritten, "quien es REDACTED_1ec4ed037766 martinez")
        self.assertFalse(hasattr(self.atlas, "_resolved_entity_id"))


class VerifiedResponseStyleTests(unittest.TestCase):

    def test_daxter_classic_biography_style(self):
        atlas = AtlasAIMixin()
        atlas.identity_manager = _IdentityManager("Daxter", "classic")
        styled = atlas._style_verified_response(
            "REDACTED_77c013518681 es el padre de REDACTED_bc04a68d9192.",
            response_kind="biography",
        )
        self.assertEqual(
            styled,
            "Vale, te pongo en situación: REDACTED_77c013518681 es el padre de REDACTED_bc04a68d9192.",
        )

    def test_coco_classic_style(self):
        atlas = AtlasAIMixin()
        atlas.identity_manager = _IdentityManager("Coco", "classic")
        styled = atlas._style_verified_response(
            "REDACTED_77c013518681 es el padre de REDACTED_bc04a68d9192.",
            response_kind="biography",
        )
        self.assertTrue(styled.startswith("Claro, te cuento:"))

    def test_work_mode_is_factual_for_both_identities(self):
        atlas = AtlasAIMixin()
        atlas.identity_manager = _IdentityManager("Daxter", "work")
        styled = atlas._style_verified_response(
            "La madre de REDACTED_bc04a68d9192 es REDACTED_e3b252570a2f.",
            response_kind="relationship",
        )
        self.assertTrue(
            styled.startswith("Vamos con los datos verificados:")
        )


if __name__ == "__main__":
    unittest.main()
