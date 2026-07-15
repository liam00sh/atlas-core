"""
===============================================================================
Proyecto Atlas
Archivo: core/atlas_tools.py

Descripción:
    Contiene la integración entre Atlas y el sistema de herramientas locales.

    Sus responsabilidades son:

    - Consultar ToolSelector.
    - Determinar si una petición puede resolverse con una herramienta.
    - Ejecutar la herramienta mediante ToolRegistry.
    - Comprobar capacidades y requisitos básicos.
    - Mostrar el resultado al usuario.
    - Añadir al contexto conversacional la pregunta y la respuesta.
    - Registrar la ejecución en los logs.

    El modelo de lenguaje no ejecuta herramientas directamente.

    Atlas mantiene siempre el control sobre:

    - Qué herramienta se utiliza.
    - Qué usuario la solicita.
    - Si la capacidad está activada.
    - Si necesita Internet.
    - Si necesita confirmación.
    - Si puede ejecutarse de forma segura.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from ai.prompts.tool_prompt import build_tool_response_prompt

from core.log_manager import info

# =============================================================================
# RESPUESTAS DE CONFIRMACIÓN
# =============================================================================

CONFIRMATION_ACCEPTED = {
    "si",
    "sí",
    "confirmo",
    "confirmar",
    "acepto",
    "adelante",
    "continua",
    "continúa",
    "hazlo",
}

CONFIRMATION_CANCELLED = {
    "no",
    "cancelar",
    "cancela",
    "rechazar",
    "dejalo",
    "déjalo",
    "mejor no",
}

class AtlasToolsMixin:
    """
    Añade a Atlas la selección y ejecución controlada de herramientas.
    """

    def _generate_natural_tool_response(
        self,
        original_text: str,
        tool_name: str,
        tool_result,
    ) -> str:
        """
        Convierte el resultado técnico de una herramienta
        en una respuesta natural mediante la IA local.

        Si la IA no está disponible o se produce un error,
        devuelve directamente el mensaje original de la herramienta.

        Parámetros:
            original_text:
                Pregunta original del usuario.

            tool_name:
                Nombre de la herramienta ejecutada.

            tool_result:
                Resultado devuelto por ToolRegistry.

        Devuelve:
            str:
                Respuesta natural o resultado técnico de respaldo.
        """

        fallback_response = tool_result.message

        # Sin proveedor no puede generarse una redacción natural.
        if self.ai_provider is None:
            return fallback_response

        # La capacidad de IA debe estar activada.
        if not self.can_use_ai():
            return fallback_response

        try:

            provider_available = (
                self.ai_provider.is_available()
            )

        except (
            RuntimeError,
            ValueError,
        ) as exception:

            info(
                f"No se pudo comprobar el proveedor de IA "
                f"para redactar una herramienta: {exception}"
            )

            return fallback_response

        if not provider_available:
            return fallback_response

        try:

            prompt = build_tool_response_prompt(
                user_message=original_text,
                tool_name=tool_name,
                tool_message=tool_result.message,
                tool_data=tool_result.data,
                user_name=self.get_user(),
                assistant_name=self.get_name(),
            )

            natural_response = (
                self.ai_provider.generate(
                    prompt
                ).strip()
            )

        except (
            RuntimeError,
            ValueError,
        ) as exception:

            info(
                f"No se pudo generar una respuesta natural "
                f"para la herramienta {tool_name}: "
                f"{exception}"
            )

            return fallback_response

        if not natural_response:
            return fallback_response

        info(
            f"Resultado de herramienta redactado mediante IA. "
            f"Herramienta: {tool_name}. "
            f"Usuario: {self.get_user()}."
        )

        return natural_response

    def _handle_pending_confirmation(
        self,
        normalized_text: str,
    ) -> bool | None:
        """
        Procesa la respuesta a una confirmación pendiente.

        Devuelve:
            True:
                La respuesta se ha procesado y Atlas continúa.

            False:
                La herramienta confirmada ha indicado que Atlas
                debe finalizar.

            None:
                La entrada no era una respuesta válida y debe
                mantenerse la confirmación pendiente.
        """

        confirmation = (
            self.confirmations.get_confirmation()
        )

        # Puede haber caducado entre la comprobación inicial
        # y la recuperación.
        if confirmation is None:

            print()

            print(
                "La confirmación ha caducado. "
                "Tendrás que solicitar la acción de nuevo."
            )

            return True

        current_user = self.get_user()

        # La confirmación solo puede resolverla quien inició la acción.
        if not self.confirmations.belongs_to_user(
            current_user
        ):

            print()

            print(
                "Esa confirmación pertenece a otro usuario. "
                "No puedo aceptar una autorización en su nombre."
            )

            info(
                f"Intento de confirmar una acción ajena. "
                f"Usuario actual: {current_user}. "
                f"Propietario: {confirmation['user']}. "
                f"Acción: {confirmation['action_name']}."
            )

            return True

        # -------------------------------------------------------------
        # CANCELACIÓN
        # -------------------------------------------------------------

        if normalized_text in CONFIRMATION_CANCELLED:

            action_name = confirmation[
                "action_name"
            ]

            self.confirmations.clear_confirmation()

            print()

            print(
                "Perfecto, lo dejamos como estaba. "
                "No he ejecutado la acción."
            )

            info(
                f"Acción cancelada por el usuario. "
                f"Usuario: {current_user}. "
                f"Acción: {action_name}."
            )

            return True

        # -------------------------------------------------------------
        # CONFIRMACIÓN
        # -------------------------------------------------------------

        if normalized_text in CONFIRMATION_ACCEPTED:

            # Eliminamos primero la confirmación para impedir
            # que pueda reutilizarse aunque la ejecución falle.
            self.confirmations.clear_confirmation()

            return self._execute_confirmed_tool(
                confirmation
            )

        # -------------------------------------------------------------
        # RESPUESTA NO RECONOCIDA
        # -------------------------------------------------------------

        print()

        print(
            "No he entendido si quieres continuar. "
            "Responde «sí» para confirmar o «no» para cancelar."
        )

        return True

    def _execute_confirmed_tool(
        self,
        confirmation: dict,
    ) -> bool:
        """
        Ejecuta una herramienta después de recibir
        una confirmación válida.

        Antes de ejecutarla vuelve a comprobar:

        - Que la acción sea de tipo herramienta.
        - Que la herramienta siga registrada.
        - Que el usuario sea el mismo.
        - Que Internet esté permitido si resulta necesario.
        """

        action_type = confirmation.get(
            "action_type"
        )

        if action_type != "tool":

            print()

            print(
                "La acción pendiente no corresponde "
                "a una herramienta válida."
            )

            info(
                f"Tipo de confirmación no compatible: "
                f"{action_type}."
            )

            return True

        tool_name = confirmation.get(
            "action_name",
            "",
        )

        arguments = confirmation.get(
            "arguments",
            {},
        )

        requested_by = confirmation.get(
            "user",
            "",
        )

        if requested_by.casefold() != (
            self.get_user().casefold()
        ):

            print()

            print(
                "El usuario activo ha cambiado. "
                "He cancelado la acción por seguridad."
            )

            info(
                f"Confirmación bloqueada por cambio de usuario. "
                f"Solicitante: {requested_by}. "
                f"Usuario actual: {self.get_user()}."
            )

            return True

        tool = self.tool_registry.get(
            tool_name
        )

        if tool is None:

            print()

            print(
                "La herramienta solicitada ya no está disponible."
            )

            info(
                f"Herramienta confirmada no encontrada: "
                f"{tool_name}."
            )

            return True

        if (
            tool.requires_internet
            and not self.can_access_internet()
        ):

            print()

            print(
                "La herramienta necesita Internet, "
                "pero el acceso está desactivado."
            )

            return True

        result = self.tool_registry.execute(
            tool_name=tool_name,
            atlas=self,
            **arguments,
        )

        if not result.success:

            print()

            print(
                result.message
            )

            info(
                f"Error al ejecutar herramienta confirmada. "
                f"Herramienta: {tool_name}. "
                f"Error: {result.error}."
            )

            return True

        final_response = (
            self._generate_natural_tool_response(
                original_text=(
                    f"Ejecuta la acción confirmada "
                    f"{tool_name}."
                ),
                tool_name=tool_name,
                tool_result=result,
            )
        )

        current_ai_context = (
            self.get_current_ai_context()
        )

        current_ai_context.add_message(
            role="user",
            content=(
                f"Confirmo la acción {tool_name}."
            ),
        )

        current_ai_context.add_message(
            role="assistant",
            content=final_response,
        )

        print()

        print(
            final_response
        )

        info(
            f"Herramienta confirmada ejecutada correctamente. "
            f"Herramienta: {tool_name}. "
            f"Usuario: {self.get_user()}."
        )

        return True

    def _handle_tool(
        self,
        original_text: str,
    ) -> bool:
        """
        Intenta resolver una entrada mediante una herramienta local.

        Parámetros:
            original_text:
                Texto original escrito por el usuario.

        Devuelve:
            True:
                La entrada ha sido reconocida como una petición
                para una herramienta y ya ha sido procesada.

            False:
                Ninguna herramienta resulta adecuada o la capacidad
                de herramientas está desactivada.
        """

        # La capacidad debe estar activada explícitamente.
        if not self.can_use_tools():
            return False

        # Protección por si el registro o el selector
        # todavía no se encuentran configurados.
        if self.tool_registry is None:

            info(
                "Herramientas no disponibles: "
                "ToolRegistry no está configurado."
            )

            return False

        if self.tool_selector is None:

            info(
                "Herramientas no disponibles: "
                "ToolSelector no está configurado."
            )

            return False

        # Primero utilizamos el selector determinista.
        selection = self.tool_selector.select(
            original_text
        )

        selection_source = "deterministic"

        # Si las reglas no reconocen la frase, permitimos que
        # el modelo proponga una herramienta.
        if selection is None:

            provider_available = (
                self.ai_provider is not None
                and self.can_use_ai()
            )

            if provider_available:

                try:

                    provider_available = (
                        self.ai_provider.is_available()
                    )

                except (
                    RuntimeError,
                    ValueError,
                ):

                    provider_available = False

            if provider_available:

                selection = (
                    self.tool_selector.select_with_ai(
                        text=original_text,
                        provider=self.ai_provider,
                    )
                )

                selection_source = "ai"

        # Ningún selector encontró una herramienta adecuada.
        if selection is None:
            return False

        tool = self.tool_registry.get(
            selection.tool_name
        )

        # Esta situación no debería ocurrir porque ToolSelector
        # comprueba el registro, pero mantenemos la protección.
        if tool is None:

            info(
                f"Herramienta seleccionada pero no registrada: "
                f"{selection.tool_name}."
            )

            return False

        # ---------------------------------------------------------------------
        # COMPROBACIÓN DE INTERNET
        # ---------------------------------------------------------------------

        if (
            tool.requires_internet
            and not self.can_access_internet()
        ):

            print()

            print(
                "Esa herramienta necesita acceso a Internet, "
                "pero ahora mismo lo tengo desactivado."
            )

            info(
                f"Herramienta bloqueada por Internet desactivado. "
                f"Herramienta: {selection.tool_name}. "
                f"Usuario: {self.get_user()}."
            )

            return True

        # ---------------------------------------------------------------------
        # COMPROBACIÓN DE CONFIRMACIÓN
        # ---------------------------------------------------------------------

        # En esta primera versión no ejecutamos automáticamente
        # herramientas que necesiten confirmación.
        if tool.requires_confirmation:

            self.confirmations.create_confirmation(
                user=self.get_user(),
                action_type="tool",
                action_name=selection.tool_name,
                arguments=selection.arguments,
            )

            print()

            if tool.is_destructive:

                print(
                    "Esta acción puede modificar el sistema. "
                    "¿Quieres que continúe?"
                )

            else:

                print(
                    "Esta acción necesita tu autorización. "
                    "¿Quieres que continúe?"
                )

            print()

            print(
                "Responde «sí» para confirmar "
                "o «no» para cancelar."
            )

            info(
                f"Herramienta pendiente de confirmación. "
                f"Herramienta: {selection.tool_name}. "
                f"Usuario: {self.get_user()}."
            )

            return True

        # ---------------------------------------------------------------------
        # EJECUCIÓN
        # ---------------------------------------------------------------------

        result = self.tool_registry.execute(
            tool_name=selection.tool_name,
            atlas=self,
            **selection.arguments,
        )

        if not result.success:

            print()

            print(
                result.message
            )

            info(
                f"Error al ejecutar herramienta. "
                f"Herramienta: {selection.tool_name}. "
                f"Usuario: {self.get_user()}. "
                f"Error: {result.error}."
            )

            return True

        # ---------------------------------------------------------------------
        # REDACCIÓN NATURAL DEL RESULTADO
        # ---------------------------------------------------------------------

        # La herramienta ya ha proporcionado los datos reales.
        #
        # La IA únicamente los convierte en una respuesta más natural.
        # Si no está disponible, se conserva el mensaje técnico original.
        final_response = (
            self._generate_natural_tool_response(
                original_text=original_text,
                tool_name=selection.tool_name,
                tool_result=result,
            )
        )

        # ---------------------------------------------------------------------
        # CONTEXTO CONVERSACIONAL
        # ---------------------------------------------------------------------

        # Recuperamos el contexto temporal del usuario activo.
        current_ai_context = (
            self.get_current_ai_context()
        )

        # Guardamos la pregunta original.
        current_ai_context.add_message(
            role="user",
            content=original_text,
        )

        # Guardamos la respuesta final mostrada al usuario.
        #
        # Puede ser:
        #
        # - Una redacción natural creada por la IA.
        # - El mensaje técnico original si la IA no estaba disponible.
        current_ai_context.add_message(
            role="assistant",
            content=final_response,
        )

        # ---------------------------------------------------------------------
        # SALIDA Y LOG
        # ---------------------------------------------------------------------

        print()

        print(
            final_response
        )

        info(
            f"Herramienta ejecutada correctamente. "
            f"Herramienta: {selection.tool_name}. "
            f"Usuario: {self.get_user()}. "
            f"Selector: {selection_source}. "
            f"Confianza: {selection.confidence}. "
            f"Motivo: {selection.reason}. "
            f"Resultado añadido al contexto de IA."
        )

        return True

    def get_tools(
        self,
    ) -> list[str]:
        """
        Devuelve los nombres de las herramientas registradas.
        """

        if self.tool_registry is None:
            return []

        return self.tool_registry.list_names()

    def get_tool_count(
        self,
    ) -> int:
        """
        Devuelve el número de herramientas registradas.
        """

        if self.tool_registry is None:
            return 0

        return self.tool_registry.count()

    def get_tool_metadata(
        self,
    ) -> list[dict]:
        """
        Devuelve los metadatos públicos de todas las herramientas.
        """

        if self.tool_registry is None:
            return []

        return self.tool_registry.get_all_metadata()

    def execute_tool(
        self,
        tool_name: str,
        **kwargs,
    ):
        """
        Ejecuta directamente una herramienta registrada.

        Este método se utilizará principalmente desde pruebas,
        comandos internos o futuras capas de autorización.
        """

        if self.tool_registry is None:
            return None

        return self.tool_registry.execute(
            tool_name=tool_name,
            atlas=self,
            **kwargs,
        )