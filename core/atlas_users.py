"""
===============================================================================
Proyecto Atlas
Archivo: core/atlas_users.py

Descripción:
    Contiene los métodos de identidad, usuarios y perfiles de Atlas.

    Esta clase se utiliza como mixin de la clase principal Atlas.
===============================================================================
"""


from core.log_manager import info


class AtlasUsersMixin:
    """
    Añade a Atlas la gestión básica de identidad y usuarios.
    """


    def _handle_user_management_request(self, original_text: str) -> bool:
        """Resuelve consultas simples de usuarios antes de la conversación IA."""

        import re
        import unicodedata

        value = unicodedata.normalize("NFKD", str(original_text).casefold())
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        normalized = " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())

        if normalized in {
            "listar usuarios", "lista de usuarios", "usuarios",
            "mostrar usuarios", "ver usuarios", "listar perfiles",
            "perfiles de usuario",
        }:
            profiles = getattr(self.users, "profiles", {})
            names: list[str] = []
            seen: set[str] = set()
            if isinstance(profiles, dict):
                for key, profile in profiles.items():
                    if isinstance(profile, dict):
                        name = str(profile.get("name") or key).strip()
                    else:
                        name = str(key).strip()
                    identity = name.casefold()
                    if name and identity not in seen:
                        seen.add(identity)
                        names.append(name)
            names.sort(key=str.casefold)
            print()
            if not names:
                print("No hay perfiles de usuario registrados en Atlas.")
            else:
                print("Perfiles de usuario registrados en Atlas:")
                for name in names:
                    current = " (perfil actual)" if name.casefold() == self.get_user().casefold() else ""
                    print(f"• {name}{current}")
            return True

        if normalized in {
            "quien soy", "quien soy yo", "mi perfil", "usuario actual",
            "que usuario soy", "que perfil tengo",
        }:
            request_context = getattr(self, "channel_request_context", None)
            channel = str(getattr(request_context, "channel", "cli") or "cli")
            print()
            print(f"Tu perfil autenticado es «{self.get_user()}» y estás usando el canal {channel}.")
            return True

        return False

    def sync_identity_user_profiles(self) -> int:
        """Carga en UserManager todos los perfiles persistentes de personas user."""

        people_manager = getattr(self, "people_manager", None)
        if people_manager is None:
            return 0

        loaded = 0
        for person in people_manager.get_users():
            profile_name = str(person.user_profile or "").strip()
            if not profile_name:
                continue
            existed = self.users.resolve_user_name(profile_name) is not None
            self.users.register_profile(
                profile_name,
                aliases=[person.name, *list(person.aliases)],
                grammatical_gender=(
                    person.grammatical_gender
                    if person.grammatical_gender in {"masculine", "feminine", "neutral"}
                    else "neutral"
                ),
                roles=["known"],
            )
            if not existed:
                loaded += 1
        return loaded

    def create_profile_for_known_person(self, requested_name: str) -> tuple[bool, str, str | None]:
        """Promociona una persona conocida a usuario Atlas de forma persistente.

        Solo Liam puede ejecutar esta operación. No crea personas nuevas ni
        admite animales, nombres ambiguos o perfiles ya vinculados a otra persona.
        """

        request_context = getattr(self, "channel_request_context", None)
        authenticated_user = (
            str(getattr(request_context, "atlas_user_id", "") or self.get_user()).strip()
        )
        if authenticated_user.casefold() != self.get_main_user().casefold():
            return False, "Solo Liam puede crear perfiles de usuario en Atlas.", None

        clean_name = str(requested_name).strip(" .,:;!?¡¿")
        if not clean_name:
            return False, "Indica el nombre de una persona conocida.", None

        person = self.people_manager.find_person_by_name(clean_name)
        if person is None:
            return (
                False,
                "No encuentro una persona conocida con ese nombre. Primero debe existir en el registro de personas de Atlas.",
                None,
            )

        if person.is_user():
            profile_name = str(person.user_profile or person.name).strip()
            self.users.register_profile(
                profile_name,
                aliases=[person.name, *list(person.aliases)],
                grammatical_gender=person.grammatical_gender,
                roles=["known"],
            )
            return False, f"{person.name} ya tiene el perfil Atlas «{profile_name}».", profile_name

        profile_name = person.aliases[0] if person.aliases else person.name
        profile_name = str(profile_name).strip()
        collision = self.people_manager.find_person_by_user_profile(profile_name)
        if collision is not None and collision.id.casefold() != person.id.casefold():
            return False, "Ese nombre de perfil ya está vinculado a otra persona.", None

        existing_profile = self.users.resolve_user_name(profile_name)
        if existing_profile is not None:
            linked = self.people_manager.find_person_by_user_profile(existing_profile)
            if linked is not None and linked.id.casefold() != person.id.casefold():
                return False, "Ya existe otro perfil Atlas con ese nombre o alias.", None
            # Puede existir un perfil legacy todavía no vinculado en people.json
            # (por ejemplo Lidia o Mary). En ese caso se reutiliza y se corrige
            # únicamente el vínculo persistente, sin crear un duplicado.
            profile_name = existing_profile

        self.users.register_profile(
            profile_name,
            aliases=[person.name, *list(person.aliases)],
            grammatical_gender=person.grammatical_gender,
            roles=["family", "known"],
        )
        if not self.people_manager.link_person_to_user(person.id, profile_name):
            self.users.profiles.pop(self.users._normalize_name(profile_name), None)
            return False, "No se pudo guardar el vínculo del perfil. No se ha realizado ningún cambio parcial.", None

        return (
            True,
            f"Perfil Atlas creado para {person.name} con el nombre «{profile_name}». Ya puede vincular su cuenta de Telegram.",
            profile_name,
        )

    def get_name(self) -> str:
        """
        Devuelve el nombre visible de la identidad activa.

        Durante las primeras etapas del constructor, antes de que exista
        ``identity_manager``, utiliza el nombre configurado en ``self.name``
        como valor de respaldo.
        """

        identity_manager = getattr(
            self,
            "identity_manager",
            None,
        )

        if identity_manager is not None:
            return (
                identity_manager
                .get_active_display_name()
            )

        return self.name

    def get_version(self) -> str:
        """Devuelve la versión de Atlas."""

        return self.version

    def get_project(self) -> str:
        """Devuelve el nombre del proyecto."""

        return self.project

    def get_user(self) -> str:
        """Devuelve el usuario activo."""

        return self.users.get_current_user()

    def get_main_user(self) -> str:
        """Devuelve el usuario principal."""

        return self.users.get_main_user()
    
    def get_user_grammatical_gender(
        self,
        user: str | None = None,
    ) -> str:
        """
        Devuelve el género gramatical configurado
        para un usuario.
        """

        selected_user = user or self.get_user()

        return self.users.get_grammatical_gender(
            selected_user
        )


    def get_user_pronouns(
        self,
        user: str | None = None,
    ) -> dict[str, str]:
        """
        Devuelve los pronombres configurados
        para un usuario.
        """

        selected_user = user or self.get_user()

        return self.users.get_pronouns(
            selected_user
        )

    def change_user(
        self,
        user: str,
    ) -> bool:
        """
        Cambia el usuario activo y sincroniza todos los servicios
        dependientes del perfil.

        Una confirmación pendiente se cancela antes del cambio para
        impedir que otra persona apruebe una acción ajena.
        """

        clean_user = str(user).strip()

        request_context = getattr(self, "channel_request_context", None)
        authenticated_channel_user = getattr(request_context, "atlas_user_id", None)
        if (
            getattr(request_context, "channel", None) == "telegram"
            and authenticated_channel_user
            and clean_user.casefold() != str(authenticated_channel_user).casefold()
        ):
            info(
                "Cambio de usuario rechazado: la identidad del canal "
                "Telegram es autoritativa."
            )
            return False

        people_manager = getattr(self, "people_manager", None)

        if people_manager is not None:
            animal = people_manager.find_animal_by_name(clean_user)

            if animal is not None:
                info(
                    f"Cambio de usuario rechazado: {animal.name} es un animal."
                )
                return False

        previous_user = self.get_user()

        if self.confirmations.has_pending_confirmation():
            self.confirmations.clear_confirmation()
            info(
                "Confirmación pendiente cancelada "
                "por cambio de usuario."
            )

        self.users.change_user(clean_user)
        current_user = self.get_user()

        conversation_identity = getattr(
            self,
            "conversation_identity",
            None,
        )

        if conversation_identity is not None:
            conversation_identity.set_authenticated_user(
                current_user
            )
            conversation_identity.identify_person(
                current_user
            )

        self._get_ai_context_for_user(
            current_user
        )

        self.identity_manager.load_user(
            current_user
        )

        info(
            f"Cambio de usuario: "
            f"{previous_user} -> {current_user}. "
            f"Contexto del nuevo perfil activado."
        )

        return True

    def return_to_main_user(
        self,
    ) -> None:
        """
        Devuelve la sesión al usuario principal y sincroniza todos
        los servicios dependientes del perfil.
        """

        request_context = getattr(self, "channel_request_context", None)
        authenticated_channel_user = getattr(request_context, "atlas_user_id", None)
        if (
            getattr(request_context, "channel", None) == "telegram"
            and authenticated_channel_user
            and self.get_main_user().casefold()
            != str(authenticated_channel_user).casefold()
        ):
            info(
                "Regreso al usuario principal rechazado: la identidad del "
                "canal Telegram es autoritativa."
            )
            return

        previous_user = self.get_user()

        if self.confirmations.has_pending_confirmation():
            self.confirmations.clear_confirmation()
            info(
                "Confirmación pendiente cancelada "
                "al volver al usuario principal."
            )

        self.users.return_to_main()
        current_user = self.get_user()

        conversation_identity = getattr(
            self,
            "conversation_identity",
            None,
        )

        if conversation_identity is not None:
            conversation_identity.set_authenticated_user(
                current_user
            )
            conversation_identity.identify_person(
                current_user
            )

        self._get_ai_context_for_user(
            current_user
        )

        self.identity_manager.load_user(
            current_user
        )

        info(
            f"Regreso al usuario principal: "
            f"{previous_user} -> {current_user}. "
            f"Contexto anterior restaurado."
        )

    def is_main_user(self) -> bool:
        """
        Indica si el usuario activo es el principal.
        """

        return self.users.is_main_user()
