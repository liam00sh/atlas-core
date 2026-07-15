"""
===============================================================================
Proyecto Atlas
Archivo: tests/test_memory_retriever.py

Descripción:
    Contiene las pruebas automáticas de MemoryRetriever.

    Estas pruebas verifican que el recuperador de memoria pueda:

    - Encontrar recuerdos relevantes por coincidencia exacta.
    - Encontrar recuerdos mediante grupos de sinónimos.
    - Ignorar recuerdos no relacionados.
    - Ordenar resultados por relevancia.
    - Respetar el límite máximo de resultados.
    - Excluir recuerdos con una puntuación insuficiente.
    - Formatear recuerdos para PromptBuilder.
    - Omitir metadatos internos en el texto final.
    - Respetar siempre el filtro de permisos aplicado
      por MemoryManager.

    Las pruebas no leen ni escriben memories.json.

    Se utiliza un MemoryManager falso para devolver
    recuerdos controlados y reproducibles.

Ejecución:

    Desde la raíz de atlas_core:

        python -m unittest tests.test_memory_retriever -v

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

import unittest

from memory.memory_retriever import MemoryRetriever


# =============================================================================
# MEMORY MANAGER FALSO
# =============================================================================

class FakeMemoryManager:
    """
    Simula MemoryManager sin utilizar archivos reales.

    El recuperador seguirá llamando a:

        get_accessible_memories()

    pero las pruebas controlan exactamente qué recuerdos
    son accesibles.
    """

    def __init__(
        self,
        accessible_memories: list[dict] | None = None,
    ) -> None:
        """
        Inicializa el gestor falso.
        """

        self.accessible_memories = (
            accessible_memories or []
        )

        self.last_owner = None
        self.last_viewer = None
        self.last_viewer_profile = None

    def get_accessible_memories(
        self,
        owner: str,
        viewer: str,
        viewer_profile: dict,
    ) -> list[dict]:
        """
        Devuelve una copia de los recuerdos permitidos.
        """

        self.last_owner = owner
        self.last_viewer = viewer
        self.last_viewer_profile = viewer_profile

        return [
            memory.copy()
            for memory in self.accessible_memories
        ]


# =============================================================================
# PRUEBAS
# =============================================================================

class TestMemoryRetriever(
    unittest.TestCase,
):
    """
    Pruebas automáticas de MemoryRetriever.
    """

    def setUp(
        self,
    ) -> None:
        """
        Crea recuerdos controlados antes de cada prueba.
        """

        self.memories = [
            {
                "id": "memory-car",
                "owner": "Liam",
                "content": (
                    "Mi coche es un Hyundai i30N Fastback."
                ),
                "visibility": "private",
                "created_at": "2026-07-11T20:00:00",
            },
            {
                "id": "memory-job",
                "owner": "Liam",
                "content": (
                    "Trabajo como administrador de sistemas Linux."
                ),
                "visibility": "known",
                "created_at": "2026-07-12T20:00:00",
            },
            {
                "id": "memory-partner",
                "owner": "Liam",
                "content": (
                    "Mi pareja se llama Saray."
                ),
                "visibility": "partner",
                "created_at": "2026-07-13T20:00:00",
            },
            {
                "id": "memory-computer",
                "owner": "Liam",
                "content": (
                    "Mi ordenador tiene una NVIDIA RTX 4060."
                ),
                "visibility": "known",
                "created_at": "2026-07-14T20:00:00",
            },
        ]

        self.manager = FakeMemoryManager(
            accessible_memories=self.memories
        )

        self.retriever = MemoryRetriever(
            memory_manager=self.manager
        )

        self.viewer_profile = {
            "name": "Liam",
            "roles": [
                "owner",
            ],
            "relationships": {},
        }

    def test_find_exact_match(
        self,
    ) -> None:
        """
        Una consulta con una palabra exacta debe encontrar
        el recuerdo correspondiente.
        """

        results = self.retriever.find(
            query="¿Qué coche tengo?",
            owner="Liam",
            viewer="Liam",
            viewer_profile=self.viewer_profile,
        )

        self.assertGreater(
            len(results),
            0,
        )

        self.assertEqual(
            results[0]["id"],
            "memory-car",
        )

    def test_find_synonym_match(
        self,
    ) -> None:
        """
        La palabra vehículo debe relacionarse con coche.
        """

        results = self.retriever.find(
            query="¿Qué vehículo tengo?",
            owner="Liam",
            viewer="Liam",
            viewer_profile=self.viewer_profile,
        )

        self.assertGreater(
            len(results),
            0,
        )

        self.assertEqual(
            results[0]["id"],
            "memory-car",
        )

    def test_find_job_memory(
        self,
    ) -> None:
        """
        Una consulta laboral debe recuperar el recuerdo del trabajo.
        """

        results = self.retriever.find(
            query="¿En qué trabajo?",
            owner="Liam",
            viewer="Liam",
            viewer_profile=self.viewer_profile,
        )

        self.assertGreater(
            len(results),
            0,
        )

        self.assertEqual(
            results[0]["id"],
            "memory-job",
        )

    def test_find_partner_memory(
        self,
    ) -> None:
        """
        Una consulta sobre la pareja debe recuperar
        el recuerdo correspondiente.
        """

        results = self.retriever.find(
            query="¿Cómo se llama mi pareja?",
            owner="Liam",
            viewer="Liam",
            viewer_profile=self.viewer_profile,
        )

        self.assertGreater(
            len(results),
            0,
        )

        self.assertEqual(
            results[0]["id"],
            "memory-partner",
        )

    def test_find_computer_memory_by_synonym(
        self,
    ) -> None:
        """
        PC y ordenador deben considerarse términos relacionados.
        """

        results = self.retriever.find(
            query="¿Qué gráfica tiene mi PC?",
            owner="Liam",
            viewer="Liam",
            viewer_profile=self.viewer_profile,
        )

        self.assertGreater(
            len(results),
            0,
        )

        self.assertEqual(
            results[0]["id"],
            "memory-computer",
        )

    def test_unrelated_query_returns_empty_list(
        self,
    ) -> None:
        """
        Una consulta sin relación no debe devolver recuerdos.
        """

        results = self.retriever.find(
            query="¿Cuál es la capital de Francia?",
            owner="Liam",
            viewer="Liam",
            viewer_profile=self.viewer_profile,
        )

        self.assertEqual(
            results,
            [],
        )

    def test_empty_query_returns_empty_list(
        self,
    ) -> None:
        """
        Una consulta vacía no debe recuperar recuerdos.
        """

        self.assertEqual(
            self.retriever.find(
                query="",
                owner="Liam",
                viewer="Liam",
                viewer_profile=self.viewer_profile,
            ),
            [],
        )

        self.assertEqual(
            self.retriever.find(
                query="   ",
                owner="Liam",
                viewer="Liam",
                viewer_profile=self.viewer_profile,
            ),
            [],
        )

    def test_limit_zero_returns_empty_list(
        self,
    ) -> None:
        """
        Un límite menor que uno debe devolver una lista vacía.
        """

        results = self.retriever.find(
            query="coche",
            owner="Liam",
            viewer="Liam",
            viewer_profile=self.viewer_profile,
            limit=0,
        )

        self.assertEqual(
            results,
            [],
        )

    def test_limit_is_respected(
        self,
    ) -> None:
        """
        El número de resultados no puede superar el límite.
        """

        repeated_memories = [
            {
                "id": f"car-{index}",
                "owner": "Liam",
                "content": (
                    f"Mi coche número {index} es especial."
                ),
                "visibility": "known",
                "created_at": (
                    f"2026-07-{10 + index:02d}T10:00:00"
                ),
            }
            for index in range(
                1,
                7,
            )
        ]

        manager = FakeMemoryManager(
            accessible_memories=repeated_memories
        )

        retriever = MemoryRetriever(
            memory_manager=manager
        )

        results = retriever.find(
            query="¿Qué coche tengo?",
            owner="Liam",
            viewer="Liam",
            viewer_profile=self.viewer_profile,
            limit=3,
        )

        self.assertEqual(
            len(results),
            3,
        )

    def test_minimum_score_filters_results(
        self,
    ) -> None:
        """
        Una puntuación mínima muy alta debe excluir
        coincidencias débiles.
        """

        results = self.retriever.find(
            query="vehículo",
            owner="Liam",
            viewer="Liam",
            viewer_profile=self.viewer_profile,
            minimum_score=10.0,
        )

        self.assertEqual(
            results,
            [],
        )

    def test_results_include_relevance_score(
        self,
    ) -> None:
        """
        Los resultados internos deben incluir su puntuación.
        """

        results = self.retriever.find(
            query="¿Qué coche tengo?",
            owner="Liam",
            viewer="Liam",
            viewer_profile=self.viewer_profile,
        )

        self.assertIn(
            "relevance_score",
            results[0],
        )

        self.assertGreater(
            results[0]["relevance_score"],
            0,
        )

    def test_original_memories_are_not_modified(
        self,
    ) -> None:
        """
        La puntuación no debe guardarse en los recuerdos originales.
        """

        self.retriever.find(
            query="¿Qué coche tengo?",
            owner="Liam",
            viewer="Liam",
            viewer_profile=self.viewer_profile,
        )

        for memory in self.memories:

            self.assertNotIn(
                "relevance_score",
                memory,
            )

    def test_manager_receives_access_parameters(
        self,
    ) -> None:
        """
        MemoryRetriever debe delegar los permisos
        en MemoryManager.
        """

        profile = {
            "name": "Saray",
            "roles": [],
        }

        self.retriever.find(
            query="¿Qué coche tiene Liam?",
            owner="Liam",
            viewer="Saray",
            viewer_profile=profile,
        )

        self.assertEqual(
            self.manager.last_owner,
            "Liam",
        )

        self.assertEqual(
            self.manager.last_viewer,
            "Saray",
        )

        self.assertIs(
            self.manager.last_viewer_profile,
            profile,
        )

    def test_inaccessible_memory_cannot_be_returned(
        self,
    ) -> None:
        """
        Si MemoryManager no autoriza recuerdos,
        el recuperador no puede acceder a ellos.
        """

        manager = FakeMemoryManager(
            accessible_memories=[]
        )

        retriever = MemoryRetriever(
            memory_manager=manager
        )

        results = retriever.find(
            query="¿Qué coche tiene Liam?",
            owner="Liam",
            viewer="Saray",
            viewer_profile={
                "name": "Saray",
                "roles": [],
            },
        )

        self.assertEqual(
            results,
            [],
        )

    def test_only_accessible_memories_are_searched(
        self,
    ) -> None:
        """
        Un recuerdo no incluido por MemoryManager
        nunca puede aparecer en los resultados.
        """

        accessible_only = [
            self.memories[1],
        ]

        manager = FakeMemoryManager(
            accessible_memories=accessible_only
        )

        retriever = MemoryRetriever(
            memory_manager=manager
        )

        results = retriever.find(
            query="¿Qué coche tengo?",
            owner="Liam",
            viewer="Liam",
            viewer_profile=self.viewer_profile,
        )

        self.assertEqual(
            results,
            [],
        )

    def test_more_exact_match_scores_higher(
        self,
    ) -> None:
        """
        Una coincidencia exacta debe superar a una
        coincidencia únicamente por sinónimo.
        """

        memories = [
            {
                "id": "exact",
                "owner": "Liam",
                "content": (
                    "Mi coche es un Hyundai."
                ),
                "visibility": "known",
                "created_at": "2026-07-10T10:00:00",
            },
            {
                "id": "synonym",
                "owner": "Liam",
                "content": (
                    "Mi vehículo es gris."
                ),
                "visibility": "known",
                "created_at": "2026-07-11T10:00:00",
            },
        ]

        retriever = MemoryRetriever(
            memory_manager=FakeMemoryManager(
                accessible_memories=memories
            )
        )

        results = retriever.find(
            query="¿Qué coche tengo?",
            owner="Liam",
            viewer="Liam",
            viewer_profile=self.viewer_profile,
        )

        self.assertEqual(
            results[0]["id"],
            "exact",
        )

        self.assertGreater(
            results[0]["relevance_score"],
            results[1]["relevance_score"],
        )

    def test_equal_scores_use_newest_memory_first(
        self,
    ) -> None:
        """
        Si dos recuerdos tienen la misma puntuación,
        debe aparecer primero el más reciente.
        """

        memories = [
            {
                "id": "older",
                "owner": "Liam",
                "content": "Tengo un coche azul.",
                "visibility": "known",
                "created_at": "2026-07-10T10:00:00",
            },
            {
                "id": "newer",
                "owner": "Liam",
                "content": "Tengo un coche gris.",
                "visibility": "known",
                "created_at": "2026-07-12T10:00:00",
            },
        ]

        retriever = MemoryRetriever(
            memory_manager=FakeMemoryManager(
                accessible_memories=memories
            )
        )

        results = retriever.find(
            query="coche",
            owner="Liam",
            viewer="Liam",
            viewer_profile=self.viewer_profile,
        )

        self.assertEqual(
            results[0]["id"],
            "newer",
        )

    # =========================================================================
    # FORMATO PARA PROMPT
    # =========================================================================

    def test_format_for_prompt(
        self,
    ) -> None:
        """
        Los recuerdos deben formatearse como una lista legible.
        """

        text = self.retriever.format_for_prompt(
            [
                self.memories[0],
                self.memories[1],
            ]
        )

        self.assertIn(
            "- Sobre Liam: Mi coche es un Hyundai i30N Fastback.",
            text,
        )

        self.assertIn(
            (
                "- Sobre Liam: Trabajo como administrador "
                "de sistemas Linux."
            ),
            text,
        )

    def test_format_for_prompt_empty_list(
        self,
    ) -> None:
        """
        Sin recuerdos debe devolverse una cadena vacía.
        """

        self.assertEqual(
            self.retriever.format_for_prompt(
                []
            ),
            "",
        )

    def test_format_does_not_include_internal_metadata(
        self,
    ) -> None:
        """
        El prompt no debe exponer identificadores,
        visibilidad ni puntuaciones.
        """

        memory = self.memories[0].copy()

        memory["relevance_score"] = 5.0

        text = self.retriever.format_for_prompt(
            [
                memory,
            ]
        )

        self.assertNotIn(
            "memory-car",
            text,
        )

        self.assertNotIn(
            "private",
            text,
        )

        self.assertNotIn(
            "5.0",
            text,
        )

        self.assertNotIn(
            "created_at",
            text,
        )

    def test_format_ignores_empty_content(
        self,
    ) -> None:
        """
        Los recuerdos sin contenido no deben incluirse.
        """

        text = self.retriever.format_for_prompt(
            [
                {
                    "owner": "Liam",
                    "content": "   ",
                },
                {
                    "owner": "Liam",
                    "content": "Contenido válido.",
                },
            ]
        )

        self.assertEqual(
            text,
            "- Sobre Liam: Contenido válido.",
        )


# =============================================================================
# EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":

    unittest.main()