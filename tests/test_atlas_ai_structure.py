"""
Prueba estructural para evitar que los métodos de AtlasAIMixin
queden fuera de la clase por un error de sangría.
"""

import unittest

from core.atlas_ai import AtlasAIMixin


class TestAtlasAIMixinStructure(unittest.TestCase):

    def test_required_ai_methods_are_part_of_mixin(self):
        required_methods = (
            "_find_entities_mentioned",
            "_join_names",
            "_entity_by_id",
            "_answer_verified_entity_query",
            "_find_ambiguous_person_reference",
            "_handle_ai",
            "clear_ai_context",
        )

        for method_name in required_methods:
            with self.subTest(method=method_name):
                self.assertTrue(
                    hasattr(AtlasAIMixin, method_name),
                    f"AtlasAIMixin no contiene {method_name}",
                )
                self.assertTrue(
                    callable(getattr(AtlasAIMixin, method_name)),
                    f"{method_name} no es invocable",
                )


if __name__ == "__main__":
    unittest.main()
