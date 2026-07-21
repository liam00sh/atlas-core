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


import re
import unicodedata

from utils.memory_query_parser import parse_memory_query


class AtlasMemoryMixin:
    """
    Añade a Atlas las funciones relacionadas con memoria.
    """

    def _handle_memory_workflow(self, original_text: str) -> bool:
        """Procesa propuestas confirmables sin escribir durante la detección."""

        controller = getattr(self, "memory_workflow_conversation", None)
        if controller is None:
            return False
        result = controller.handle(self, original_text)
        if not result.get("handled", False):
            return False
        print()
        print(result.get("message", "Operación de memoria procesada."))
        return True

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

        # Formas exhaustivas naturales que el parser heredado no reconocía,
        # por ejemplo «dime todo lo que sepas de Saray». Sin esta ruta, esas
        # frases llegaban a la IA y podían producir relaciones inventadas.
        if memory_query is None:
            folded = "".join(
                ch for ch in unicodedata.normalize("NFD", original_text.casefold())
                if unicodedata.category(ch) != "Mn"
            )
            folded = re.sub(r"[^a-z0-9ñ ]+", " ", folded)
            folded = re.sub(r"\s+", " ", folded).strip()

            # Variantes naturales que deben consultar la memoria y no pasar a
            # la IA: «qué sabes sobre mí», «qué recuerdas de mí», etc.
            if re.match(
                r"^(?:dime\s+)?(?:que sabes|que recuerdas|que conoces)\s+(?:de|sobre)\s+(?:mi|yo)$",
                folded,
            ):
                memory_query = {"type": "self"}

            match = re.match(
                r"^(?:dime|muestrame|ensename|cuentame)?\s*"
                r"(?:absolutamente\s+)?(?:todo\s+lo\s+que\s+(?:sabes|sepas|recuerdas)|"
                r"toda\s+la\s+informacion\s+que\s+(?:tienes|tengas)|"
                r"todos\s+los\s+datos(?:\s+que\s+(?:tienes|tengas))?)"
                r"\s+(?:de|sobre)\s+(.+)$",
                folded,
            )
            if memory_query is None and match:
                owner_text = match.group(1).strip()
                if owner_text in {"mi", "mí", "yo"}:
                    memory_query = {"type": "self"}
                else:
                    memory_query = {"type": "other", "owner": owner_text}

        if memory_query is None:
            return False

        normalized_request = " ".join(original_text.casefold().split())
        exhaustive = any(
            marker in normalized_request
            for marker in (
                "todo lo que sabes",
                "todo lo que sepas",
                "toda la informacion",
                "toda la información",
                "todos los datos",
                "lista completa",
                "absolutamente todo",
            )
        )

        if memory_query["type"] == "self":

            # En Telegram puede hablar temporalmente otra persona desde la
            # cuenta autenticada. La consulta «qué sabes de mí» pertenece al
            # interlocutor actual, no necesariamente al dueño de la cuenta.
            current_speaker_getter = getattr(
                self,
                "_get_current_conversation_user",
                None,
            )
            owner = (
                current_speaker_getter()
                if callable(current_speaker_getter)
                else self.get_user()
            )
            self.memory_service.show_memories_about(
                owner,
                exhaustive=exhaustive,
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
            resolved_owner,
            exhaustive=exhaustive,
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
