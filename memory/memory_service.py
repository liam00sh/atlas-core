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

    def show_memories_about(
        self,
        owner: str,
    ) -> None:
        """
        Muestra los recuerdos accesibles sobre una persona.

        Parámetros:
            owner:
                Propietario de los recuerdos buscados.

        La información mostrada depende de:

            - La persona que realiza la consulta.
            - Sus roles.
            - Sus relaciones.
            - La visibilidad de cada recuerdo.

        Importante:
            Los permisos se comprueban utilizando a la persona
            que habla actualmente.

            No se heredan los permisos del usuario autenticado.
        """

        owner = owner.strip()

        if not owner:

            print()

            print(
                "No me has indicado sobre quién "
                "quieres consultar recuerdos."
            )

            return

        # ---------------------------------------------------------------------
        # PERSONA QUE ESTÁ REALIZANDO LA CONSULTA
        # ---------------------------------------------------------------------

        viewer = (
            self.atlas
            .conversation_identity
            .get_memory_viewer()
        )

        if viewer is None:

            print()

            print(
                "No hay ninguna persona identificada."
            )

            return

        # ---------------------------------------------------------------------
        # PERFIL DE LA PERSONA QUE CONSULTA
        # ---------------------------------------------------------------------

        # Si la persona tiene un perfil completo de usuario,
        # UserManager devolverá sus roles y relaciones.
        #
        # Si se trata de un invitado sin perfil, deberá devolver
        # un diccionario vacío o un perfil sin privilegios.
        viewer_profile = self.atlas.users.get_profile(
            viewer
        )

        if not isinstance(
            viewer_profile,
            dict,
        ):

            viewer_profile = {}

        # ---------------------------------------------------------------------
        # RECUERDOS AUTORIZADOS
        # ---------------------------------------------------------------------

        # MemoryManager devuelve únicamente los recuerdos
        # que puede leer la persona que está hablando.
        memories = (
            self.atlas.memory.get_accessible_memories(
                owner=owner,
                viewer=viewer,
                viewer_profile=viewer_profile,
            )
        )

        info(
            f"Consulta de recuerdos. "
            f"Propietario: {owner}. "
            f"Consultante: {viewer}. "
            f"Resultados autorizados: {len(memories)}."
        )

        print()

        # No se ha encontrado ningún recuerdo accesible.
        if not memories:

            # Consulta sobre uno mismo.
            if owner.casefold() == viewer.casefold():

                print(
                    f"Todavía no recuerdo nada "
                    f"sobre {owner}."
                )

            # Consulta sobre otra persona.
            else:

                print(
                    f"No tengo información sobre "
                    f"{owner} que pueda compartir "
                    f"con {viewer}."
                )

            return

        # Cabecera de la lista.
        print(
            f"Esto es lo que puedo compartir "
            f"con {viewer} sobre {owner}:"
        )

        print()

        # Mostramos los recuerdos numerados.
        for index, memory in enumerate(
            memories,
            start=1,
        ):

            # Nombre legible de la visibilidad.
            visibility = memory.get(
                "visibility",
                "",
            )

            label = VISIBILITY_LABELS.get(
                visibility,
                "Visibilidad desconocida",
            )

            content = str(
                memory.get(
                    "content",
                    "",
                )
            ).strip()

            if not content:
                continue

            print(
                f"{index}. {content} "
                f"[{label}]"
            )