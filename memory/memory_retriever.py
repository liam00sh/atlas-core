"""
===============================================================================
Proyecto Atlas
Archivo: memory/memory_retriever.py

Descripción:
    Selecciona recuerdos persistentes relevantes para una consulta.

    MemoryRetriever no guarda recuerdos y no accede directamente
    al archivo memories.json.

    Utiliza MemoryManager para:

    - Obtener recuerdos almacenados.
    - Aplicar las reglas de privacidad.
    - Respetar propietarios, relaciones y roles.

    Su responsabilidad consiste únicamente en:

    - Normalizar la consulta.
    - Extraer términos significativos.
    - Compararlos con recuerdos autorizados.
    - Calcular una puntuación de relevancia.
    - Ordenar los resultados.
    - Limitar la cantidad enviada al modelo.
    - Preparar los recuerdos para PromptBuilder.

    Esta primera versión utiliza coincidencias léxicas.

    En futuras versiones podrá sustituirse o ampliarse con:

    - Embeddings.
    - Búsqueda semántica.
    - ChromaDB.
    - FAISS.
    - RAG documental.

    El resto de Atlas no necesitará conocer qué sistema de búsqueda
    utiliza internamente este módulo.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

import re

from typing import Any

from core.log_manager import info

from utils.text_normalizer import normalize_text


# =============================================================================
# CONSTANTES
# =============================================================================

# Palabras demasiado comunes para determinar la relevancia
# real de un recuerdo.
STOP_WORDS = {
    "a",
    "al",
    "algo",
    "como",
    "con",
    "cual",
    "cuando",
    "de",
    "del",
    "dime",
    "donde",
    "el",
    "ella",
    "en",
    "es",
    "esa",
    "ese",
    "esto",
    "ha",
    "hay",
    "la",
    "las",
    "lo",
    "los",
    "me",
    "mi",
    "mis",
    "para",
    "por",
    "que",
    "quien",
    "se",
    "sobre",
    "soy",
    "su",
    "sus",
    "te",
    "tengo",
    "tiene",
    "tu",
    "un",
    "una",
    "y",
    "yo",
}


# Relaciona términos habituales que pueden expresar
# un mismo concepto.
#
# Esta tabla es deliberadamente pequeña. Más adelante
# será sustituida por búsqueda semántica.
SYNONYM_GROUPS = (
    {
        "coche",
        "automovil",
        "vehiculo",
        "carro",
    },
    {
        "trabajo",
        "empleo",
        "empresa",
        "puesto",
        "laboral",
    },
    {
        "pareja",
        "novia",
        "novio",
        "compañera",
        "compañero",
    },
    {
        "ordenador",
        "pc",
        "equipo",
        "computadora",
    },
    {
        "movil",
        "telefono",
        "smartphone",
    },
    {
        "casa",
        "hogar",
        "vivienda",
    },
    {
        "estudios",
        "formacion",
        "curso",
        "grado",
    },
)


class MemoryRetriever:
    """
    Recupera recuerdos autorizados y relevantes.
    """

    def __init__(
        self,
        memory_manager,
    ) -> None:
        """
        Inicializa el recuperador.

        Parámetros:
            memory_manager:
                Instancia de MemoryManager utilizada
                para obtener recuerdos autorizados.
        """

        self.memory_manager = memory_manager

    def find(
        self,
        query: str,
        owner: str,
        viewer: str,
        viewer_profile: dict,
        limit: int = 5,
        minimum_score: float = 1.0,
    ) -> list[dict[str, Any]]:
        """
        Busca recuerdos relevantes y autorizados.

        Parámetros:
            query:
                Pregunta o mensaje actual del usuario.

            owner:
                Propietario de los recuerdos buscados.

            viewer:
                Usuario que realiza la consulta.

            viewer_profile:
                Perfil completo del usuario que consulta.

            limit:
                Número máximo de recuerdos devueltos.

            minimum_score:
                Puntuación mínima necesaria para considerar
                que un recuerdo es relevante.

        Devuelve:
            list[dict]:
                Recuerdos autorizados ordenados de mayor
                a menor relevancia.

                Cada elemento incluye temporalmente:

                    relevance_score

                Este valor solo se utiliza durante la recuperación
                y no se guarda en memories.json.
        """

        query = query.strip()

        if not query:
            return []

        if limit < 1:
            return []

        accessible_memories = (
            self.memory_manager.get_accessible_memories(
                owner=owner,
                viewer=viewer,
                viewer_profile=viewer_profile,
            )
        )

        if not accessible_memories:
            return []

        query_terms = self._extract_terms(
            query
        )

        if not query_terms:
            return []

        scored_memories = []

        for memory in accessible_memories:

            score = self._score_memory(
                query_terms=query_terms,
                memory=memory,
            )

            if score < minimum_score:
                continue

            scored_memory = memory.copy()

            scored_memory[
                "relevance_score"
            ] = score

            scored_memories.append(
                scored_memory
            )

        scored_memories.sort(
            key=lambda memory: (
                memory.get(
                    "relevance_score",
                    0.0,
                ),
                memory.get(
                    "created_at",
                    "",
                ),
            ),
            reverse=True,
        )

        selected_memories = scored_memories[
            :limit
        ]

        info(
            f"MemoryRetriever: "
            f"{len(selected_memories)} recuerdos relevantes "
            f"seleccionados para {viewer} "
            f"sobre {owner}."
        )

        return selected_memories

    def format_for_prompt(
        self,
        memories: list[dict[str, Any]],
    ) -> str:
        """
        Convierte recuerdos en un texto seguro para PromptBuilder.

        No incluye:

        - Identificadores internos.
        - Puntuaciones de relevancia.
        - Fechas técnicas.
        - Información de control innecesaria.

        Devuelve:
            str:
                Lista de recuerdos preparada para el modelo.

                Cadena vacía si no existen recuerdos.
        """

        if not memories:
            return ""

        lines = []

        for memory in memories:

            owner = str(
                memory.get(
                    "owner",
                    "Usuario",
                )
            ).strip()

            content = str(
                memory.get(
                    "content",
                    "",
                )
            ).strip()

            if not content:
                continue

            lines.append(
                f"- Sobre {owner}: {content}"
            )

        return "\n".join(
            lines
        )

    def _score_memory(
        self,
        query_terms: set[str],
        memory: dict[str, Any],
    ) -> float:
        """
        Calcula la relevancia de un recuerdo.

        Criterios actuales:

        - Coincidencia exacta de términos.
        - Coincidencia mediante grupos de sinónimos.
        - Coincidencia del propietario.
        - Coincidencias múltiples dentro del contenido.

        Esta puntuación no representa probabilidad.
        Solo sirve para ordenar recuerdos.
        """

        content = str(
            memory.get(
                "content",
                "",
            )
        )

        owner = str(
            memory.get(
                "owner",
                "",
            )
        )

        content_terms = self._extract_terms(
            content
        )

        owner_terms = self._extract_terms(
            owner
        )

        exact_matches = (
            query_terms
            & content_terms
        )

        owner_matches = (
            query_terms
            & owner_terms
        )

        score = float(
            len(exact_matches) * 3
        )

        score += float(
            len(owner_matches) * 2
        )

        score += self._score_synonyms(
            query_terms=query_terms,
            content_terms=content_terms,
        )

        # Pequeña bonificación cuando aparecen varios
        # términos relevantes en el mismo recuerdo.
        if len(exact_matches) >= 2:
            score += 1.0

        return score

    @staticmethod
    def _score_synonyms(
        query_terms: set[str],
        content_terms: set[str],
    ) -> float:
        """
        Puntúa coincidencias conceptuales sencillas
        mediante grupos de sinónimos.
        """

        score = 0.0

        for synonym_group in SYNONYM_GROUPS:

            query_matches_group = bool(
                query_terms
                & synonym_group
            )

            content_matches_group = bool(
                content_terms
                & synonym_group
            )

            if (
                query_matches_group
                and content_matches_group
            ):
                score += 2.0

        return score

    @staticmethod
    def _extract_terms(
        text: str,
    ) -> set[str]:
        """
        Normaliza un texto y extrae términos significativos.
        """

        normalized_text = normalize_text(
            text
        )

        raw_terms = re.findall(
            r"[a-z0-9]+",
            normalized_text,
        )

        return {
            term
            for term in raw_terms
            if (
                len(term) >= 2
                and term not in STOP_WORDS
            )
        }