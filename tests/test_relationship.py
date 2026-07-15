"""Pruebas de la entidad y utilidades de relaciones."""

import unittest

from identity.relationship import (
    BROTHER,
    PET_OF,
    PET_OWNER,
    SIBLING,
    SISTER,
    Relationship,
    get_inverse_relationship_type,
)


class RelationshipTests(unittest.TestCase):
    def test_round_trip_serialization(self):
        relationship = Relationship(
            source_entity_id="p1",
            relationship_type=BROTHER,
            target_entity_id="p2",
            confirmed=True,
        )
        restored = Relationship.from_dict(
            relationship.to_dict()
        )
        self.assertEqual(restored.id, relationship.id)
        self.assertEqual(restored.relationship_type, BROTHER)
        self.assertTrue(restored.confirmed)

    def test_inverse_mapping_uses_generic_contract(self):
        """Las relaciones de hermanos usan una inversa genérica."""
        self.assertEqual(
            get_inverse_relationship_type(BROTHER),
            SIBLING,
        )
        self.assertEqual(
            get_inverse_relationship_type(SISTER),
            SIBLING,
        )
        self.assertEqual(
            get_inverse_relationship_type(PET_OWNER),
            PET_OF,
        )

    def test_unknown_inverse_returns_none(self):
        self.assertIsNone(
            get_inverse_relationship_type("unknown")
        )


if __name__ == "__main__":
    unittest.main()
