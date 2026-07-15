"""
===============================================================================
Proyecto Atlas
Archivo: core/user_manager.py

Descripción:
    Este módulo gestiona los usuarios de Atlas.

    Sus responsabilidades principales son:

    - Definir el usuario principal.
    - Mantener el usuario activo.
    - Almacenar perfiles conocidos.
    - Guardar roles y relaciones entre usuarios.
    - Crear perfiles temporales para invitados.
    - Resolver nombres ignorando mayúsculas y acentos.
    - Volver al usuario principal cuando termina una sesión temporal.

Ejemplo:

    Usuario principal:
        Liam

    Usuarios conocidos:
        Liam
        Saray
        Lidia

    Usuario temporal:
        Cualquier persona que escriba "soy Nombre"

Importante:
    Este módulo no guarda todavía los perfiles en disco.

    Los perfiles existen únicamente mientras Atlas está ejecutándose.
===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

# unicodedata permite trabajar con caracteres Unicode.
#
# En este archivo se utiliza para eliminar acentos al comparar nombres.
#
# Ejemplo:
#
#     "Rubén" -> "ruben"
#
# Así, una consulta escrita como "Ruben" puede encontrar
# correctamente un perfil llamado "Rubén".
import unicodedata


class UserManager:
    """
    Gestiona los usuarios y perfiles de Atlas.

    Esta clase conoce:

    - El usuario principal.
    - El usuario activo.
    - Los perfiles registrados.
    - Los roles.
    - Las relaciones entre personas.
    """

    def __init__(self):
        """
        Inicializa el gestor de usuarios.

        Durante la creación:

        1. Se define Liam como usuario principal.
        2. El usuario activo comienza siendo Liam.
        3. Se cargan los perfiles conocidos.
        """

        # Usuario principal del sistema.
        #
        # Cuando Atlas arranca, siempre empieza con este usuario.
        self.main_user = "Liam"

        # Usuario que está utilizando Atlas en este momento.
        #
        # Al iniciar, coincide con el usuario principal.
        self.current_user = self.main_user

        # Diccionario con los perfiles conocidos.
        #
        # Las claves están en minúsculas para facilitar la búsqueda:
        #
        #     "liam"
        #     "saray"
        #     "lidia"
        #
        # Cada perfil contiene:
        #
        # - Nombre visible.
        # - Roles.
        # - Relaciones.
        self.profiles = {

            # -----------------------------------------------------------------
            # PERFIL DE LIAM
            # -----------------------------------------------------------------
            "liam": {
                "name": "Liam",

                # Género gramatical utilizado al redactar respuestas.
                "grammatical_gender": "masculine",

                # Pronombres configurados explícitamente.
                "pronouns": {
                    "subject": "él",
                    "object": "lo",
                    "indirect_object": "le",
                    "possessive": "su",
                },

                "roles": [
                    "owner",
                    "admin",
                ],

                "relationships": {
                    "partner_of": [
                        "Saray",
                    ],
                    "family_of": [
                        "Lidia",
                    ],
                    "known_of": [
                        "Saray",
                        "Lidia",
                    ],
                },
            },

            # -----------------------------------------------------------------
            # PERFIL DE SARAY
            # -----------------------------------------------------------------
            "saray": {
                "name": "Saray",

                "grammatical_gender": "feminine",

                "pronouns": {
                    "subject": "ella",
                    "object": "la",
                    "indirect_object": "le",
                    "possessive": "su",
                },

                "roles": [
                    "partner",
                    "known",
                ],

                "relationships": {
                    "partner_of": [
                        "Liam",
                    ],
                    "family_of": [],
                    "known_of": [
                        "Liam",
                    ],
                },
            },

            # -----------------------------------------------------------------
            # PERFIL DE LIDIA
            # -----------------------------------------------------------------
            "lidia": {
                "name": "Lidia",

                "grammatical_gender": "feminine",

                "pronouns": {
                    "subject": "ella",
                    "object": "la",
                    "indirect_object": "le",
                    "possessive": "su",
                },

                "roles": [
                    "family",
                    "known",
                ],

                "relationships": {
                    "partner_of": [],
                    "family_of": [
                        "Liam",
                    ],
                    "known_of": [
                        "Liam",
                    ],
                },
            },
        }

    def _normalize_name(
        self,
        user: str,
    ) -> str:
        """
        Normaliza un nombre para utilizarlo como clave interna.

        Parámetros:
            user:
                Nombre original del usuario.

        Devuelve:
            str:
                Nombre sin espacios exteriores y en minúsculas.

        Ejemplo:

            "  Saray  " -> "saray"
        """

        return user.strip().lower()

    def _normalize_identity_name(
        self,
        user: str,
    ) -> str:
        """
        Normaliza un nombre para compararlo ignorando acentos.

        Parámetros:
            user:
                Nombre que se desea normalizar.

        Devuelve:
            str:
                Nombre en minúsculas y sin acentos.

        Ejemplo:

            "Rubén" -> "ruben"
        """

        # NFD separa las letras de sus signos diacríticos.
        #
        # Ejemplo:
        #
        # "é" se convierte en:
        #
        # "e" + marca de acento
        normalized = unicodedata.normalize(
            "NFD",
            user.strip().lower(),
        )

        # Reconstruimos el texto ignorando los caracteres
        # cuya categoría Unicode sea "Mn".
        #
        # "Mn" significa:
        #     Marca no espaciada.
        #
        # En este caso representa los acentos.
        return "".join(
            character
            for character in normalized
            if unicodedata.category(
                character
            ) != "Mn"
        )

    def resolve_user_name(
        self,
        requested_name: str,
    ) -> str | None:
        """
        Busca un usuario conocido por su nombre.

        Parámetros:
            requested_name:
                Nombre escrito por el usuario.

        Devuelve:
            str:
                Nombre correcto del perfil encontrado.

            None:
                No existe ningún perfil coincidente.

        La comparación ignora:

        - Mayúsculas.
        - Minúsculas.
        - Acentos.

        Pero no corrige nombres distintos.

        Ejemplos:

            "ruben" puede encontrar "Rubén".

            "sary" no se convierte automáticamente en "Saray".
        """

        # Normalizamos el nombre solicitado.
        normalized_requested_name = (
            self._normalize_identity_name(
                requested_name
            )
        )

        # Recorremos todos los perfiles conocidos.
        for profile in self.profiles.values():

            # Obtenemos el nombre visible del perfil.
            profile_name = profile["name"]

            # Normalizamos también el nombre guardado.
            normalized_profile_name = (
                self._normalize_identity_name(
                    profile_name
                )
            )

            # Comparamos las dos formas normalizadas.
            if (
                normalized_profile_name
                == normalized_requested_name
            ):

                # Devolvemos el nombre real guardado,
                # conservando sus mayúsculas y acentos.
                return profile_name

        # No existe coincidencia.
        return None

    def _create_guest_profile(
        self,
        user: str,
    ) -> dict:
        """
        Crea un perfil temporal para un usuario desconocido.

        Como Atlas no debe deducir el género de una persona
        únicamente por su nombre, los perfiles nuevos utilizan
        inicialmente un tratamiento neutral.
        """

        return {
            "name": user,

            "grammatical_gender": "neutral",

            "pronouns": {
                "subject": "esa persona",
                "object": "le",
                "indirect_object": "le",
                "possessive": "su",
            },

            "roles": [
                "guest",
            ],

            "relationships": {
                "partner_of": [],
                "family_of": [],
                "known_of": [],
            },
        }

    def get_current_user(self):
        """
        Devuelve el usuario activo.

        Ejemplos:
            Liam
            Saray
            Lidia
        """

        return self.current_user

    def get_main_user(self):
        """
        Devuelve el usuario principal del sistema.

        Actualmente:
            Liam
        """

        return self.main_user

    def get_profile(
        self,
        user: str | None = None,
    ) -> dict:
        """
        Devuelve el perfil de un usuario.

        Parámetros:
            user:
                Nombre del usuario solicitado.

                Si no se indica, se utiliza el usuario activo.

        Devuelve:
            dict:
                Perfil completo del usuario.

        Si el perfil no existe, se crea automáticamente
        un perfil de invitado.
        """

        # Si se ha recibido un nombre, lo utilizamos.
        #
        # Si no, usamos el usuario actual.
        selected_user = (
            user
            or self.current_user
        )

        # Convertimos el nombre en una clave interna.
        normalized_name = self._normalize_name(
            selected_user
        )

        # Si el usuario no existe en profiles,
        # creamos un perfil temporal.
        if normalized_name not in self.profiles:

            self.profiles[normalized_name] = (
                self._create_guest_profile(
                    selected_user
                )
            )

        # Devolvemos el perfil encontrado o creado.
        return self.profiles[
            normalized_name
        ]

    def get_grammatical_gender(
        self,
        user: str | None = None,
    ) -> str:
        """
        Devuelve el género gramatical configurado
        para un usuario.

        Valores posibles:

            masculine
            feminine
            neutral
        """

        profile = self.get_profile(
            user
        )

        return profile.get(
            "grammatical_gender",
            "neutral",
        )


    def get_pronouns(
        self,
        user: str | None = None,
    ) -> dict[str, str]:
        """
        Devuelve una copia de los pronombres configurados
        para un usuario.

        Si el perfil no contiene pronombres, utiliza
        una configuración neutral.
        """

        profile = self.get_profile(
            user
        )

        default_pronouns = {
            "subject": "esa persona",
            "object": "le",
            "indirect_object": "le",
            "possessive": "su",
        }

        pronouns = profile.get(
            "pronouns",
            default_pronouns,
        )

        return pronouns.copy()

    def set_grammatical_gender(
        self,
        user: str,
        grammatical_gender: str,
    ) -> bool:
        """
        Modifica el género gramatical de un perfil.

        Devuelve:
            True:
                El valor era válido y se ha guardado.

            False:
                El valor recibido no es válido.
        """

        valid_genders = {
            "masculine",
            "feminine",
            "neutral",
        }

        normalized_gender = (
            grammatical_gender
            .strip()
            .lower()
        )

        if normalized_gender not in valid_genders:
            return False

        profile = self.get_profile(
            user
        )

        profile["grammatical_gender"] = (
            normalized_gender
        )

        return True


    def set_pronouns(
        self,
        user: str,
        subject: str,
        object_pronoun: str,
        indirect_object: str = "le",
        possessive: str = "su",
    ) -> bool:
        """
        Configura los pronombres de un usuario.
        """

        subject = subject.strip()
        object_pronoun = object_pronoun.strip()
        indirect_object = indirect_object.strip()
        possessive = possessive.strip()

        if not subject or not object_pronoun:
            return False

        profile = self.get_profile(
            user
        )

        profile["pronouns"] = {
            "subject": subject,
            "object": object_pronoun,
            "indirect_object": indirect_object or "le",
            "possessive": possessive or "su",
        }

        return True

    def change_user(
        self,
        user,
    ):
        """
        Cambia el usuario activo.

        Parámetros:
            user:
                Nombre del nuevo usuario.

        Si el perfil no existe, se crea automáticamente
        como invitado.
        """

        # Actualizamos el usuario activo.
        self.current_user = user

        # Nos aseguramos de que exista un perfil.
        self.get_profile(
            user
        )

    def return_to_main(self):
        """
        Devuelve la sesión al usuario principal.
        """

        self.current_user = self.main_user

    def is_main_user(self):
        """
        Comprueba si el usuario activo es el principal.

        Devuelve:
            True:
                El usuario activo es Liam.

            False:
                El usuario activo es otra persona.
        """

        return (
            self.current_user
            == self.main_user
        )