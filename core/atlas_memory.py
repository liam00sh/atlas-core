"""
===============================================================================
Proyecto Atlas
Archivo: core/atlas_memory.py

Descripción:
    Contiene los métodos de integración entre Atlas
    y el sistema de memoria persistente.

    Esta clase se utiliza como mixin de la clase principal Atlas.
===============================================================================
"""


from utils.memory_query_parser import parse_memory_query


class AtlasMemoryMixin:
    """
    Añade a Atlas las funciones relacionadas con memoria.
    """

    @staticmethod
    def _is_memory_storage_request(
        normalized_text: str,
    ) -> bool:
        """
        Indica si la entrada solicita guardar un recuerdo.
        """

        return normalized_text.startswith(
            "recuerda que "
        )

    def _handle_memory_storage_request(
        self,
        original_text: str,
    ) -> bool:
        """
        Extrae y envía un recuerdo al servicio de memoria.
        """

        content = original_text[13:].strip()

        return self.memory_service.process_memory_request(
            content
        )

    def _handle_memory_query(
        self,
        original_text: str,
    ) -> bool:
        """
        Procesa una consulta de recuerdos.
        """

        memory_query = parse_memory_query(
            original_text
        )

        if memory_query is None:
            return False

        if memory_query["type"] == "self":

            self.memory_service.show_memories_about(
                self.get_user()
            )

            return True

        requested_owner = memory_query[
            "owner"
        ]

        resolved_owner = self.users.resolve_user_name(
            requested_owner
        )

        if resolved_owner is None:

            print()
            print(
                f"No conozco ningún usuario llamado "
                f"«{requested_owner}»."
            )

            return True

        self.memory_service.show_memories_about(
            resolved_owner
        )

        return True

    def remember(
        self,
        content: str,
        visibility: str,
    ) -> bool:
        """
        Guarda un recuerdo para el usuario activo.
        """

        return self.memory.remember(
            owner=self.get_user(),
            content=content,
            visibility=visibility,
        )