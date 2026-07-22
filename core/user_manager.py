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
from pathlib import Path
import re


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

        # Validador externo opcional para impedir perfiles de entidades
        # que no sean personas, como los animales registrados.
        self._profile_validator = None

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


            # -----------------------------------------------------------------
            # PERFIL DE MARÍA JOSÉ MARTÍNEZ SANZ (MARY)
            # -----------------------------------------------------------------
            "mary": {
                "name": "Mary",

                "aliases": [
                    "Mary",
                    "María José",
                    "Maria Jose",
                    "Maria Jose Martinez Sanz",
                    "María José Martínez Sanz",
                ],

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
            },        }

        # Cada perfil dispone de un espacio privado propio. Esto se crea
        # también para los perfiles legacy al arrancar Atlas.
        self.ensure_all_profile_storage()


    def _profile_storage_key(self, user: str) -> str:
        """Devuelve una clave de carpeta segura y estable para un perfil."""
        resolved = self.resolve_user_name(str(user).strip()) or str(user).strip()
        normalized = self._normalize_identity_name(resolved)
        key = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
        if not key:
            raise ValueError("No se puede crear almacenamiento para un perfil sin nombre.")
        return key

    def get_profile_data_dir(self, user: str) -> Path:
        """Ruta privada del perfil dentro de data/users/<perfil>."""
        project_root = Path(__file__).resolve().parent.parent
        return project_root / "data" / "users" / self._profile_storage_key(user)

    def get_internet_history_path(self, user: str) -> Path:
        """Ruta canónica del historial web privado de un perfil."""
        return self.get_profile_data_dir(user) / "internet_history.jsonl"

    def ensure_profile_storage(self, user: str) -> Path:
        """Crea de forma idempotente el espacio privado mínimo del perfil."""
        profile_dir = self.get_profile_data_dir(user)
        profile_dir.mkdir(parents=True, exist_ok=True)
        history_path = profile_dir / "internet_history.jsonl"
        history_path.touch(exist_ok=True)
        return profile_dir

    def ensure_all_profile_storage(self) -> int:
        """Asegura el almacenamiento de todos los perfiles ya registrados."""
        created = 0
        for key, profile in self.profiles.items():
            name = str(profile.get("name") or key) if isinstance(profile, dict) else str(key)
            directory = self.get_profile_data_dir(name)
            existed = directory.exists() and (directory / "internet_history.jsonl").exists()
            self.ensure_profile_storage(name)
            if not existed:
                created += 1
        return created

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
        """Resuelve un perfil por clave, nombre visible o alias.

        La comparación ignora mayúsculas, minúsculas y acentos, pero nunca
        convierte un nombre desconocido en el usuario activo.
        """

        normalized_requested_name = self._normalize_identity_name(
            requested_name
        )

        for profile_key, profile in self.profiles.items():
            if not isinstance(profile, dict):
                continue

            candidates = {
                str(profile_key),
                str(profile.get("name", "")),
            }

            for field in ("alias", "aliases", "nickname", "preferred_name"):
                value = profile.get(field)
                if isinstance(value, str):
                    candidates.add(value)
                elif isinstance(value, (list, tuple, set)):
                    candidates.update(str(item) for item in value)

            for candidate in candidates:
                if not candidate.strip():
                    continue
                if self._normalize_identity_name(candidate) == normalized_requested_name:
                    return str(profile.get("name") or profile_key)

        return None


    def set_profile_validator(self, validator) -> None:
        """Configura una función que valida si un nombre puede tener perfil."""

        if validator is not None and not callable(validator):
            raise TypeError("El validador de perfiles debe ser invocable.")

        self._profile_validator = validator

    def _ensure_profile_allowed(self, user: str) -> None:
        """Impide crear o utilizar perfiles para entidades no autorizadas."""

        if self._profile_validator is None:
            return

        if not self._profile_validator(user):
            raise ValueError(
                f"{user} no puede tener un perfil de usuario en Atlas."
            )

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


    def register_profile(
        self,
        user: str,
        *,
        aliases: list[str] | None = None,
        grammatical_gender: str = "neutral",
        roles: list[str] | None = None,
    ) -> dict:
        """Registra un perfil Atlas real sin crear personas implícitamente.

        La existencia de la persona debe validarse en una capa superior. Este
        método solo mantiene el catálogo de perfiles de UserManager.
        """

        clean_user = str(user).strip()
        if not clean_user:
            raise ValueError("El nombre del perfil no puede estar vacío.")
        self._ensure_profile_allowed(clean_user)

        existing = self.resolve_user_name(clean_user)
        if existing is not None:
            self.ensure_profile_storage(existing)
            return self.get_profile(existing)

        valid_genders = {"masculine", "feminine", "neutral"}
        clean_gender = str(grammatical_gender).strip().casefold()
        if clean_gender not in valid_genders:
            clean_gender = "neutral"

        profile = {
            "name": clean_user,
            "aliases": [
                str(alias).strip()
                for alias in (aliases or [])
                if str(alias).strip() and str(alias).strip().casefold() != clean_user.casefold()
            ],
            "grammatical_gender": clean_gender,
            "pronouns": {
                "subject": "él" if clean_gender == "masculine" else ("ella" if clean_gender == "feminine" else "esa persona"),
                "object": "lo" if clean_gender == "masculine" else ("la" if clean_gender == "feminine" else "le"),
                "indirect_object": "le",
                "possessive": "su",
            },
            "roles": list(dict.fromkeys(roles or ["known"])),
            "relationships": {
                "partner_of": [],
                "family_of": [],
                "known_of": [self.main_user],
            },
        }
        self.profiles[self._normalize_name(clean_user)] = profile
        self.ensure_profile_storage(clean_user)
        return profile

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

        # Los perfiles conocidos pueden solicitarse por nombre completo o alias.
        # Se convierten siempre a su identificador canónico antes de buscar.
        resolved_user = self.resolve_user_name(
            selected_user
        )
        if resolved_user is not None:
            selected_user = resolved_user

        # Validamos antes de buscar o crear el perfil.
        self._ensure_profile_allowed(
            selected_user
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

        # Resolvemos nombres completos y alias al identificador canónico.
        # Así «Mary» y «María José Martínez Sanz» activan el mismo perfil.
        resolved_user = self.resolve_user_name(
            str(user)
        )
        selected_user = resolved_user or str(user).strip()

        # Validamos y obtenemos el perfil antes de cambiar el usuario.
        # Así una entidad rechazada nunca queda activa parcialmente.
        self.get_profile(
            selected_user
        )

        self.current_user = selected_user

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