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
