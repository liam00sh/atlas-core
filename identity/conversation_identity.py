"""
===============================================================================
Proyecto Atlas
Archivo: identity/conversation_identity.py

Descripción:
    Gestiona la identidad activa durante una conversación.

    Este módulo separa dos conceptos fundamentales:

        Usuario autenticado
            Persona que ha iniciado la sesión.

        Interlocutor actual
            Persona que está hablando con Atlas.

    Ambos conceptos pueden coincidir o ser distintos.

    Ejemplo:

        Sesión iniciada:
            Liam

        Persona que habla:
            María

    En ese caso:

        Usuario autenticado:
            Liam

        Persona actual:
            María

    Atlas utilizará esta información para decidir:

    - Qué recuerdos puede consultar.
    - Qué permisos tiene.
    - Qué relaciones conoce.
    - Cómo debe dirigirse a esa persona.
    - Qué personalidad aplicar.

    Este módulo no realiza reconocimiento de voz,
    cámara ni biometría.

    Simplemente mantiene la identidad conversacional
    actual y coordina el resto del sistema.

===============================================================================
"""

# =============================================================================
# IMPORTACIONES
# =============================================================================

from core.log_manager import info

from identity.people_manager import PeopleManager
from identity.person import Person
from identity.person_status import get_status_label
from identity.visitor_manager import VisitorManager


class ConversationIdentity:
    """
    Gestiona quién está hablando actualmente con Atlas.

    No cambia la sesión del sistema.

    Solo cambia la identidad conversacional activa.
    """

    def __init__(
        self,
        people_manager: PeopleManager,
        visitor_manager: VisitorManager,
    ) -> None:
        """
        Inicializa el gestor de identidad conversacional.

        Parámetros
        ----------
        people_manager:
            Gestor principal de personas.

        visitor_manager:
            Gestor de visitantes y promociones.
        """

        if not isinstance(
            people_manager,
            PeopleManager,
        ):
            raise TypeError(
                "people_manager debe ser una instancia "
                "de PeopleManager."
            )

        if not isinstance(
            visitor_manager,
            VisitorManager,
        ):
            raise TypeError(
                "visitor_manager debe ser una instancia "
                "de VisitorManager."
            )

        self.people_manager = people_manager

        self.visitor_manager = visitor_manager

        # -------------------------------------------------------------
        # Usuario autenticado
        # -------------------------------------------------------------
        #
        # Persona que abrió la sesión.
        #
        # Este valor normalmente permanece estable durante
        # toda la sesión.
        #
        # Ejemplo:
        #
        # Liam
        #
        self.authenticated_user: str | None = None

        # -------------------------------------------------------------
        # Persona actual
        # -------------------------------------------------------------
        #
        # Persona que está hablando con Atlas.
        #
        # Puede cambiar continuamente.
        #
        # Liam
        #
        # ↓
        #
        # Saray
        #
        # ↓
        #
        # Rubén
        #
        # ↓
        #
        # María
        #
        self.current_person: Person | None = None

        info(
            "ConversationIdentity inicializado."
        )

    # =================================================================
    # USUARIO AUTENTICADO
    # =================================================================

    def set_authenticated_user(
        self,
        username: str,
    ) -> None:
        """
        Define el usuario que ha iniciado la sesión.

        No modifica la persona actual.
        """

        username = username.strip()

        if not username:
            raise ValueError(
                "El usuario autenticado no puede estar vacío."
            )

        self.authenticated_user = username

        info(
            f"Usuario autenticado establecido: "
            f"{username}."
        )

    def get_authenticated_user(
        self,
    ) -> str | None:
        """
        Devuelve el usuario autenticado.
        """

        return self.authenticated_user

    def has_authenticated_user(
        self,
    ) -> bool:
        """
        Indica si existe un usuario autenticado.
        """

        return self.authenticated_user is not None

    # =================================================================
    # PERSONA ACTUAL
    # =================================================================

    def get_current_person(
        self,
    ) -> Person | None:
        """
        Devuelve la persona que está hablando.
        """

        return self.current_person

    def has_current_person(
        self,
    ) -> bool:
        """
        Indica si existe una persona activa.
        """

        return self.current_person is not None

    def get_current_person_name(
        self,
    ) -> str | None:
        """
        Devuelve el nombre de la persona actual.
        """

        if self.current_person is None:
            return None

        return self.current_person.name

    def get_current_person_status(
        self,
    ) -> str | None:
        """
        Devuelve el estado de la persona actual.
        """

        if self.current_person is None:
            return None

        return self.current_person.status

    def get_current_identity_key(
        self,
    ) -> str | None:
        """
        Devuelve la clave canónica del interlocutor actual.

        Cuando la persona dispone de un perfil de UserManager, se utiliza
        ``user_profile``. Para visitantes y personas sin cuenta se conserva
        su nombre principal. Esta separación evita crear perfiles temporales
        duplicados cuando el nombre completo de una persona difiere del nombre
        corto utilizado para iniciar sesión.
        """

        if self.current_person is None:
            return None

        return (
            self.current_person.user_profile
            or self.current_person.name
        )

    def clear_current_person(
        self,
    ) -> None:
        """
        Elimina la identidad conversacional actual.

        No afecta al usuario autenticado.
        """

        if self.current_person is not None:

            info(
                f"Fin de conversación con "
                f"{self.current_person.name}."
            )

        self.current_person = None

    # =================================================================
    # CAMBIO DE INTERLOCUTOR
    # =================================================================

    def set_current_person(
        self,
        person: Person,
    ) -> None:
        """
        Establece la persona que está hablando actualmente.

        Si la persona cambia, se registra el encuentro mediante
        VisitorManager.

        No modifica el usuario autenticado.
        """

        if not isinstance(
            person,
            Person,
        ):
            raise TypeError(
                "person debe ser una instancia de Person."
            )

        previous_person = self.current_person

        # Si ya era la misma persona, no hacemos nada.
        if (
            previous_person is not None
            and previous_person.id == person.id
        ):
            return

        self.current_person = person

        # Registramos el encuentro.
        updated_person = (
            self.visitor_manager.register_visit(
                person.id
            )
        )

        if updated_person is not None:
            self.current_person = updated_person

        if previous_person is None:

            info(
                f"Conversación iniciada con "
                f"{person.name}."
            )

        else:

            info(
                f"Cambio de interlocutor: "
                f"{previous_person.name} -> "
                f"{person.name}."
            )

    def identify_person(
        self,
        name: str,
    ) -> Person:
        """
        Identifica a una persona por su nombre.

        Si ya existe, reutiliza su perfil.

        Si no existe, crea un nuevo invitado.

        Devuelve siempre la persona activa.
        """

        name = name.strip()

        if not name:

            raise ValueError(
                "El nombre no puede estar vacío."
            )

        person = (
            self.people_manager.find_person_by_name(
                name
            )
        )

        if person is None:

            person = (
                self.visitor_manager.register_new_visitor(
                    name=name,
                )
            )

            if person is None:

                raise RuntimeError(
                    "No se ha podido crear "
                    "el nuevo visitante."
                )

        self.set_current_person(
            person
        )

        return self.current_person

    def change_current_person(
        self,
        name: str,
    ) -> Person:
        """
        Cambia la identidad conversacional.

        Este método es simplemente un alias más natural
        para identify_person().
        """

        return self.identify_person(
            name
        )

    def restore_authenticated_user(
        self,
    ) -> Person | None:
        """
        Vuelve a considerar como interlocutor al usuario
        autenticado.

        No cambia la sesión.

        Solo cambia la identidad conversacional.
        """

        if self.authenticated_user is None:
            return None

        person = (
            self.people_manager.find_person_by_name(
                self.authenticated_user
            )
        )

        if person is None:

            return None

        self.set_current_person(
            person
        )

        return person

    # =================================================================
    # CONSULTAS
    # =================================================================

    def is_authenticated_user_speaking(
        self,
    ) -> bool:
        """
        Indica si quien habla coincide con el usuario
        autenticado.
        """

        if (
            self.authenticated_user is None
            or self.current_person is None
        ):
            return False

        current_identity = (
            self.get_current_identity_key()
        )

        if current_identity is None:
            return False

        return (
            self.authenticated_user.casefold()
            == current_identity.casefold()
        )

    def is_guest_speaking(
        self,
    ) -> bool:
        """
        Indica si la persona actual es un invitado.
        """

        if self.current_person is None:
            return False

        return (
            self.current_person.status
            == "guest"
        )

    def is_known_person_speaking(
        self,
    ) -> bool:
        """
        Indica si la persona actual ya es conocida.
        """

        if self.current_person is None:
            return False

        return (
            self.current_person.status
            == "known"
        )

    def is_regular_person_speaking(
        self,
    ) -> bool:
        """
        Indica si la persona actual es habitual.
        """

        if self.current_person is None:
            return False

        return (
            self.current_person.status
            == "regular"
        )

    def is_user_speaking(
        self,
    ) -> bool:
        """
        Indica si la persona actual posee un perfil
        completo de usuario.
        """

        if self.current_person is None:
            return False

        return (
            self.current_person.status
            == "user"
        )

    # =================================================================
    # PERMISOS
    # =================================================================

    def get_permission_viewer(
        self,
    ) -> str | None:
        """
        Devuelve la identidad que debe utilizarse para
        comprobar permisos.

        Atlas siempre utiliza la persona que está hablando.

        Esto permite que varias personas compartan una misma
        sesión sin compartir permisos.
        """

        return self.get_current_identity_key()

    def get_memory_viewer(
        self,
    ) -> str | None:
        """
        Devuelve la identidad que debe utilizarse para consultar
        recuerdos.

        Actualmente coincide con el permission viewer,
        pero se mantiene separado para permitir futuras
        ampliaciones.
        """

        return self.get_permission_viewer()

    def get_conversation_owner(
        self,
    ) -> str | None:
        """
        Devuelve el propietario actual de la conversación.

        En esta primera versión coincide con la persona
        que está hablando.

        En el futuro podrá representar conversaciones
        grupales.
        """

        return self.get_current_identity_key()

    def can_access_as_current_person(
        self,
        owner: str,
        memory_manager,
        users_manager,
    ) -> list[dict]:
        """
        Devuelve los recuerdos visibles para la persona
        que está hablando.

        Parámetros
        ----------
        owner:
            Persona propietaria de los recuerdos.

        memory_manager:
            Gestor de memoria.

        users_manager:
            Gestor de usuarios.

        Devuelve
        --------
        list[dict]
            Recuerdos accesibles.
        """

        if self.current_person is None:
            return []

        viewer = self.get_memory_viewer()

        if viewer is None:
            return []

        viewer_profile = (
            users_manager.get_profile(
                viewer
            )
        )

        return memory_manager.get_accessible_memories(
            owner=owner,
            viewer=viewer,
            viewer_profile=viewer_profile,
        )

    # =================================================================
    # DESCRIPCIÓN DEL INTERLOCUTOR
    # =================================================================

    def describe_current_person(
        self,
    ) -> str:
        """
        Devuelve una descripción legible de la persona
        que está hablando.
        """

        if self.current_person is None:

            return (
                "Actualmente no hay ninguna persona "
                "identificada."
            )

        description = (
            f"{self.current_person.name} "
            f"({self.current_person.status})"
        )

        if (
            self.current_person.encounter_count
            == 1
        ):

            description += (
                ", primer encuentro."
            )

        else:

            description += (
                f", "
                f"{self.current_person.encounter_count} "
                f"encuentros."
            )

        return description

    def get_identity_summary(
        self,
    ) -> dict:
        """
        Devuelve un resumen completo de la identidad
        conversacional actual.

        Este método está pensado para depuración,
        herramientas y futuras funciones de IA.
        """

        return {

            "authenticated_user":
                self.authenticated_user,

            "current_person":
                (
                    None
                    if self.current_person is None
                    else self.current_person.name
                ),

            "status":
                (
                    None
                    if self.current_person is None
                    else self.current_person.status
                ),

            "encounters":
                (
                    0
                    if self.current_person is None
                    else self.current_person.encounter_count
                ),

            "permission_viewer":
                self.get_permission_viewer(),

            "memory_viewer":
                self.get_memory_viewer(),

            "conversation_owner":
                self.get_conversation_owner(),

            "current_identity_key":
                self.get_current_identity_key(),

        }

    # =================================================================
    # CONTEXTO DE IDENTIDAD PARA LA IA
    # =================================================================

    def build_prompt_context(
        self,
    ) -> str:
        """
        Construye el contexto de identidad que se enviará
        al modelo de inteligencia artificial.

        Este texto permite distinguir entre:

        - El usuario que mantiene abierta la sesión.
        - La persona que está hablando actualmente.
        - La identidad que debe utilizarse para los permisos.

        Importante:
            El usuario autenticado no concede sus permisos
            a la persona que está hablando.

            Si la sesión pertenece a Liam, pero quien habla
            es María, los permisos deben comprobarse como María.
        """

        authenticated_user = (
            self.authenticated_user
            or "No identificado"
        )

        if self.current_person is None:

            return "\n".join(
                [
                    "IDENTIDAD DE LA CONVERSACIÓN",
                    "",
                    (
                        "Usuario autenticado: "
                        f"{authenticated_user}"
                    ),
                    (
                        "Persona que habla actualmente: "
                        "No identificada"
                    ),
                    "",
                    (
                        "No atribuyas al interlocutor los permisos "
                        "del usuario autenticado."
                    ),
                ]
            )

        current_person = self.current_person

        status_label = get_status_label(
            current_person.status
        )

        lines = [
            "IDENTIDAD DE LA CONVERSACIÓN",
            "",
            (
                "Usuario autenticado: "
                f"{authenticated_user}"
            ),
            (
                "Persona que habla actualmente: "
                f"{current_person.name}"
            ),
            (
                "Estado social de la persona: "
                f"{status_label}"
            ),
            (
                "Número de encuentros registrados: "
                f"{current_person.encounter_count}"
            ),
        ]

        if current_person.user_profile is not None:

            lines.append(
                "Perfil de usuario asociado: "
                f"{current_person.user_profile}"
            )

        else:

            lines.append(
                "Perfil de usuario asociado: ninguno"
            )

        if current_person.introduced_by is not None:

            lines.append(
                "Persona que la presentó: "
                f"{current_person.introduced_by}"
            )

        if current_person.summary:

            lines.append(
                "Resumen conocido: "
                f"{current_person.summary}"
            )

        lines.extend(
            [
                "",
                (
                    "La persona que habla actualmente es la identidad "
                    "que debe utilizarse para comprobar permisos, "
                    "privacidad y acceso a recuerdos."
                ),
                (
                    "No concedas a esta persona los permisos del "
                    "usuario autenticado únicamente por compartir "
                    "la misma sesión."
                ),
            ]
        )

        if self.is_authenticated_user_speaking():

            lines.append(
                (
                    "En este momento, la persona que habla coincide "
                    "con el usuario autenticado."
                )
            )

        else:

            lines.append(
                (
                    "En este momento, la persona que habla es distinta "
                    "del usuario autenticado."
                )
            )

        return "\n".join(
            lines
        )

    # =================================================================
    # PREPARACIÓN PARA FUTURAS FASES
    # =================================================================

    def identify_by_voice(
        self,
        voice_id: str,
    ) -> Person | None:
        """
        Identifica una persona mediante reconocimiento
        de voz.

        Esta funcionalidad todavía no está implementada.

        En una futura versión recibirá un identificador
        generado por el motor biométrico y devolverá
        la persona correspondiente.
        """

        del voice_id

        return None

    def identify_by_face(
        self,
        face_id: str,
    ) -> Person | None:
        """
        Identifica una persona mediante reconocimiento
        facial.

        Pendiente de implementación.
        """

        del face_id

        return None

    def identify_by_camera(
        self,
        camera_frame,
    ) -> Person | None:
        """
        Identifica una persona utilizando una imagen
        procedente de una cámara.

        Pendiente de implementación.
        """

        del camera_frame

        return None

    def identify_by_microphone(
        self,
        audio_data,
    ) -> Person | None:
        """
        Identifica una persona utilizando audio bruto.

        Pendiente de implementación.
        """

        del audio_data

        return None

    def identify_by_device(
        self,
        device_id: str,
    ) -> Person | None:
        """
        Identifica una persona utilizando un dispositivo
        conocido.

        Ejemplos futuros:

        - Móvil personal.
        - Smartwatch.
        - Pulsera BLE.
        - NFC.
        """

        del device_id

        return None

    # =================================================================
    # RESTABLECIMIENTO
    # =================================================================

    def reset(
        self,
    ) -> None:
        """
        Reinicia completamente el estado conversacional.

        No elimina personas ni visitantes.

        Únicamente limpia la conversación activa.
        """

        self.authenticated_user = None

        self.current_person = None

        info(
            "ConversationIdentity reiniciado."
        )

    # =================================================================
    # REPRESENTACIÓN
    # =================================================================

    def __repr__(
        self,
    ) -> str:
        """
        Representación técnica del objeto.
        """

        return (
            "ConversationIdentity("
            f"authenticated_user="
            f"{self.authenticated_user!r}, "
            f"current_person="
            f"{None if self.current_person is None else self.current_person.name!r}"
            ")"
        )

    def __str__(
        self,
    ) -> str:
        """
        Representación legible.
        """

        if self.current_person is None:

            return (
                "ConversationIdentity("
                "sin interlocutor activo)"
            )

        return (
            "ConversationIdentity("
            f"{self.current_person.name}, "
            f"{self.current_person.status})"
        )
