"""
===============================================================================
Proyecto Atlas
Archivo: memory/memory_service.py

Descripción:
    Este módulo gestiona la interacción entre el usuario y el sistema
    de memoria de Atlas.

    Sus responsabilidades son:

    - Procesar solicitudes para guardar recuerdos.
    - Clasificar automáticamente la visibilidad.
    - Preguntar la privacidad cuando exista alguna duda.
    - Mantener temporalmente un recuerdo pendiente.
    - Procesar la respuesta de visibilidad.
    - Mostrar los recuerdos que una persona puede consultar.

Diferencia con memory_manager.py:

    memory_manager.py:
        Guarda y lee físicamente los recuerdos del archivo JSON.

    memory_service.py:
        Gestiona la conversación y las decisiones relacionadas
        con esos recuerdos.

Importante:
    El usuario autenticado y la persona que habla pueden ser distintos.

    Para consultar recuerdos y comprobar permisos se utiliza siempre
    la identidad de la persona que está hablando actualmente.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

# Registra eventos informativos en el archivo atlas.log.
from core.log_manager import info

# Intenta clasificar automáticamente la visibilidad
# de la información que se quiere guardar.
from memory.classifier import classify_visibility

# Convierte respuestas como "3", "pareja" o "familia"
# en valores internos del sistema.
from memory.visibility import normalize_visibility

# Traduce los valores internos de privacidad
# a nombres comprensibles para el usuario.
from memory.visibility import VISIBILITY_LABELS


class MemoryService:
    """
    Gestiona la interacción de Atlas con su sistema de memoria.

    Esta clase no guarda directamente archivos JSON.

    Utiliza el MemoryManager que ya existe dentro de Atlas.
    """

    def __init__(
        self,
        atlas,
    ) -> None:
        """
        Inicializa el servicio de memoria.

        Parámetros:
            atlas:
                Instancia principal de la clase Atlas.

        Guardar esta referencia permite acceder a:

            - El usuario autenticado.
            - La persona que habla.
            - Los perfiles.
            - ConversationIdentity.
            - MemoryManager.
        """

        # Referencia a la instancia principal de Atlas.
        self.atlas = atlas

        # Recuerdo que espera que el usuario indique
        # su nivel de privacidad.
        #
        # Normalmente:
        #
        #     None
        #
        # Cuando existe una clasificación pendiente:
        #
        # {
        #     "owner": "Liam",
        #     "content": "Mi coche es..."
        # }
        self.pending_memory = None

    def has_pending_memory(
        self,
    ) -> bool:
        """
        Indica si existe un recuerdo esperando una respuesta
        sobre su visibilidad.

        Devuelve:
            True:
                Existe un recuerdo pendiente.

            False:
                No existe ninguno.
        """

        return self.pending_memory is not None

    def process_memory_request(
        self,
        content: str,
    ) -> bool:
        """
        Procesa una petición para guardar un recuerdo.

        Parámetros:
            content:
                Información exacta que debe almacenarse.

        Funcionamiento:

            1. Comprueba que exista contenido.
            2. Intenta clasificar su visibilidad.
            3. Lo guarda directamente si la clasificación es clara.
            4. Si existe duda, pregunta al usuario.
        """

        # Eliminamos espacios innecesarios.
        content = content.strip()

        # Evitamos guardar recuerdos vacíos.
        if not content:

            print()

            print(
                "No me has indicado qué debo recordar."
            )

            return True

        # El clasificador devuelve:
        #
        # visibility:
        #     Nivel de privacidad detectado o None.
        #
        # reason:
        #     Explicación de la decisión.
        visibility, reason = classify_visibility(
            content
        )

        # Si el clasificador ha encontrado una categoría clara,
        # guardamos el recuerdo directamente.
        if visibility is not None:

            saved = self.atlas.remember(
                content=content,
                visibility=visibility,
            )

            print()

            if saved:

                print(
                    f"Entendido, "
                    f"{self.atlas.get_user()}."
                )

                print()

                print(
                    "Lo guardaré como: "
                    f"{VISIBILITY_LABELS[visibility]}."
                )

            else:

                print(
                    "No he podido guardar "
                    "ese recuerdo."
                )

            return True

        # Si Daxter no está seguro, conserva temporalmente
        # el recuerdo hasta recibir una respuesta.
        self.pending_memory = {
            "owner": self.atlas.get_user(),
            "content": content,
        }

        print()

        print(
            "No estoy seguro de quién debería "
            "poder conocer esta información."
        )

        print()

        print("1. Solo tú")
        print("2. Tú y el administrador")
        print("3. Tu pareja")
        print("4. Tu familia")
        print("5. Personas de confianza")
        print("6. Cualquier persona")

        print()

        print(
            "Escribe un número del 1 al 6 "
            "o «cancelar»."
        )

        # Dejamos registrado por qué Daxter tuvo que preguntar.
        info(
            f"Clasificación pendiente: "
            f"{content}. Motivo: {reason}"
        )

        return True

    def process_visibility_answer(
        self,
        answer: str,
    ) -> bool:
        """
        Procesa la respuesta sobre la privacidad
        de un recuerdo pendiente.

        Parámetros:
            answer:
                Opción escrita por el usuario.

        Puede contener:

            - Un número del 1 al 6.
            - Una palabra como "pareja" o "familia".
            - La orden "cancelar".
        """

        # Protección adicional por si este método se llama
        # sin existir un recuerdo pendiente.
        if self.pending_memory is None:

            print()

            print(
                "No hay ningún recuerdo pendiente "
                "de clasificación."
            )

            return True

        # El usuario puede cancelar el guardado.
        if answer in {
            "cancelar",
            "cancela",
        }:

            self.pending_memory = None

            print()

            print(
                "He cancelado el recuerdo."
            )

            return True

        # Convertimos la respuesta en un nivel interno.
        visibility = normalize_visibility(
            answer
        )

        # Si la respuesta no se reconoce,
        # mantenemos el recuerdo pendiente.
        if visibility is None:

            print()

            print(
                "No he entendido el nivel "
                "de privacidad."
            )

            print(
                "Elige una opción del 1 al 6 "
                "o escribe «cancelar»."
            )

            return True

        # Guardamos temporalmente una copia del recuerdo
        # antes de limpiar el estado pendiente.
        pending_memory = self.pending_memory.copy()

        # La siguiente entrada volverá al flujo normal.
        self.pending_memory = None

        # Guardamos el recuerdo con el propietario que inició
        # la solicitud, aunque el usuario activo pudiera cambiar.
        saved = self.atlas.memory.remember(
            owner=pending_memory["owner"],
            content=pending_memory["content"],
            visibility=visibility,
        )

        print()

        if saved:

            print(
                "Recuerdo guardado correctamente."
            )

            print()

            print(
                "Visibilidad: "
                f"{VISIBILITY_LABELS[visibility]}."
            )

        else:

            print(
                "No he podido guardar "
                "el recuerdo."
            )

        return True

    @staticmethod
    def _memory_in_second_person(content: str, *, self_view: bool) -> str:
        """Convierte recuerdos redactados en primera persona a lenguaje natural."""
        text = " ".join(str(content).split()).strip().rstrip(".")
        if not self_view:
            return text
        lower = text.casefold()
        replacements = (
            ("mi coche es ", "Tu coche es "),
            ("mi movil es ", "Tu móvil es "),
            ("mi móvil es ", "Tu móvil es "),
            ("mi telefono es ", "Tu teléfono es "),
            ("mi teléfono es ", "Tu teléfono es "),
            ("mi trabajo es ", "Tu trabajo es "),
            ("trabajo como ", "Trabajas como "),
            ("trabajo en ", "Trabajas en "),
            ("mi fecha de nacimiento es ", "Tu fecha de nacimiento es "),
            ("naci el ", "Naciste el "),
            ("nací el ", "Naciste el "),
            ("mi cumpleaños es ", "Tu cumpleaños es "),
            ("cumplo años el ", "Cumples años el "),
            ("tengo ", "Tienes "),
            ("vivo en ", "Vives en "),
            ("soy de ", "Eres de "),
            ("naci en ", "Naciste en "),
            ("nací en ", "Naciste en "),
            ("mi mascota es ", "Tu mascota es "),
            ("mis mascotas son ", "Tus mascotas son "),
            ("tengo un perro ", "Tienes un perro "),
            ("tengo una perra ", "Tienes una perra "),
            ("tengo un gato ", "Tienes un gato "),
            ("tengo una gata ", "Tienes una gata "),
            ("me gusta ", "Te gusta "),
            ("soy ", "Eres "),
        )
        for source, target in replacements:
            if lower.startswith(source):
                return target + text[len(source):]
        if lower.startswith("mi "):
            return "Tu " + text[3:]
        return text[:1].upper() + text[1:]

    @staticmethod
    def _memory_signature(content: str) -> str:
        import re
        import unicodedata
        value = unicodedata.normalize("NFKD", str(content).casefold())
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = re.sub(r"\b(mi|mis|un|una|el|la|de|del|es|son)\b", " ", value)
        return re.sub(r"[^a-z0-9]+", " ", value).strip()

    @staticmethod
    def _essential_category(content: str) -> str | None:
        """Clasifica datos personales útiles para un resumen humano."""
        import re
        import unicodedata
        value = unicodedata.normalize("NFKD", str(content).casefold())
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        value = re.sub(r"[^a-z0-9ñ ]+", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        categories = (
            ("birth", ("fecha de nacimiento", "naci el", "cumpleanos", "cumplo anos")),
            ("age", ("tengo años", "tengo anos", "mi edad", "anos de edad")),
            ("work", ("trabajo como", "trabajo en", "mi trabajo", "mi profesion", "mi profesión")),
            ("residence", ("vivo en", "resido en", "mi domicilio", "mi residencia")),
            ("origin", ("soy de", "naci en", "mi pueblo", "mi ciudad natal")),
            ("pets", ("mascota", "mascotas", "mi perro", "mi perra", "mi gato", "mi gata", "tengo un perro", "tengo una perra", "tengo un gato", "tengo una gata")),
            ("family", ("mi pareja", "mi madre", "mi padre", "mi hermana", "mi hermano", "mi hijo", "mi hija")),
            ("vehicle", ("mi coche", "mi moto", "mi vehiculo", "mi vehículo")),
            ("phone", ("mi movil", "mi móvil", "mi telefono", "mi teléfono")),
        )
        for category, markers in categories:
            if any(marker in value for marker in markers):
                return category
        return None

    def _select_brief_memories(self, memories: list[dict], limit: int = 6) -> list[dict]:
        """Prioriza identidad cotidiana sin repetir categorías equivalentes."""
        ranked = sorted(memories, key=lambda item: (
            {"critical": 4, "high": 3, "medium": 2}.get(str(item.get("priority", "")).casefold(), 1),
            int(item.get("access_count", 0) or 0),
            str(item.get("updated_at") or item.get("created_at") or ""),
        ), reverse=True)
        selected: list[dict] = []
        used_categories: set[str] = set()
        essential_order = ("birth", "age", "work", "residence", "origin", "pets", "family", "vehicle", "phone")
        by_category: dict[str, list[dict]] = {}
        for memory in ranked:
            category = self._essential_category(memory.get("content", ""))
            if category:
                by_category.setdefault(category, []).append(memory)
        for category in essential_order:
            if category in by_category and len(selected) < limit:
                selected.append(by_category[category][0])
                used_categories.add(category)
        for memory in ranked:
            if len(selected) >= limit:
                break
            category = self._essential_category(memory.get("content", ""))
            if category and category in used_categories:
                continue
            if memory not in selected:
                selected.append(memory)
                if category:
                    used_categories.add(category)
        return selected

    def show_memories_about(
        self,
        owner: str,
        *,
        exhaustive: bool = False,
    ) -> None:
        """Muestra un resumen breve o el listado autorizado completo."""
        owner = owner.strip()
        if not owner:
            print()
            print("No me has indicado sobre quién quieres consultar recuerdos.")
            return

        viewer = self.atlas.conversation_identity.get_memory_viewer()
        if viewer is None:
            print()
            print("No hay ninguna persona identificada.")
            return

        viewer_profile = self.atlas.users.get_profile(viewer)
        if not isinstance(viewer_profile, dict):
            viewer_profile = {}

        is_owner = owner.casefold() == viewer.casefold()
        is_admin = viewer.casefold() == "liam"

        if is_admin:
            memories = self.atlas.memory.list_memories(owner=owner)
        else:
            memories = self.atlas.memory.get_accessible_memories(
                owner=owner,
                viewer=viewer,
                viewer_profile=viewer_profile,
            )

        info(
            f"Consulta de recuerdos. Propietario: {owner}. "
            f"Consultante: {viewer}. Resultados autorizados: {len(memories)}. "
            f"Listado completo: {exhaustive}."
        )
        print()

        # Para otra persona, «todo» significa todo lo que el consultante tiene
        # autorizado a ver, nunca los datos privados ocultos.
        restricted_other = exhaustive and not (is_owner or is_admin)

        candidates: list[dict] = []
        for memory in reversed(memories):
            content = " ".join(str(memory.get("content", "")).split()).strip()
            if not content:
                continue
            signature = self._memory_signature(content)
            duplicate_index = None
            for index, existing in enumerate(candidates):
                existing_signature = self._memory_signature(existing["content"])
                if (
                    signature == existing_signature
                    or signature in existing_signature
                    or existing_signature in signature
                ):
                    duplicate_index = index
                    break
            copy = memory.copy()
            copy["content"] = content
            if duplicate_index is None:
                candidates.append(copy)
            elif len(content) > len(candidates[duplicate_index]["content"]):
                candidates[duplicate_index] = copy
        unique = list(reversed(candidates))

        if not unique:
            if is_owner:
                print("Todavía no tengo información guardada sobre ti.")
            else:
                print(f"No tengo información sobre {owner} que pueda compartir contigo.")
            return

        def importance(memory: dict) -> tuple[int, int, str]:
            priority = str(memory.get("priority", "")).casefold()
            priority_score = {"critical": 4, "high": 3, "medium": 2}.get(priority, 1)
            access_score = int(memory.get("access_count", 0) or 0)
            timestamp = str(memory.get("updated_at") or memory.get("created_at") or "")
            return (priority_score, access_score, timestamp)

        if exhaustive:
            selected = sorted(unique, key=importance, reverse=True)
            if is_owner:
                print("Esto es todo lo que tengo guardado sobre ti:")
            elif is_admin:
                print(f"Esto es todo lo que tengo guardado sobre {owner}:")
            else:
                print(
                    f"Esto es todo lo que tienes autorizado a conocer sobre {owner}. "
                    "Sus datos privados no se muestran:"
                )
            print()
            for index, memory in enumerate(selected, start=1):
                line = self._memory_in_second_person(memory["content"], self_view=is_owner)
                print(f"{index}. {line}")
                if index < len(selected):
                    print()
            return

        selected = self._select_brief_memories(unique, limit=6)
        if is_owner:
            print("Estas son algunas de las cosas importantes que recuerdo sobre ti:")
        else:
            print(f"Esto es lo más importante que puedo contarte sobre {owner}:")
        print()
        for memory in selected:
            line = self._memory_in_second_person(memory["content"], self_view=is_owner)
            print(f"• {line}")

        if len(unique) > len(selected) and (is_owner or is_admin):
            print()
            print("También tengo más información guardada; puedes pedirme el listado completo.")
