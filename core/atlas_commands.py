"""
===============================================================================
Proyecto Atlas
Archivo: core/atlas_commands.py

Descripción:
    Contiene la integración entre Atlas y el sistema de comandos.

    Gestiona dos grupos de órdenes:

    1. Comandos generales registrados en:

        console.command_manager

    2. Órdenes internas relacionadas con la identidad del asistente:

        - Cambiar entre Daxter y Coco.
        - Cambiar manualmente de modo.
        - Volver al modo predeterminado.
        - Activar o desactivar el cambio automático.
        - Liberar un modo bloqueado manualmente.
        - Consultar la identidad y el modo activos.

    Las órdenes de identidad se procesan antes que los comandos
    generales para impedir que terminen tratándose como conversación
    normal o como una petición para la inteligencia artificial.

    Esta clase se utiliza como mixin de la clase principal Atlas.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from assistant_identity.mode import CLASSIC_MODE
from assistant_identity.mode import EMPATHETIC_MODE
from assistant_identity.mode import FUN_MODE
from assistant_identity.mode import WORK_MODE

from assistant_identity.phrase_bank import IDENTITY_CHANGED
from assistant_identity.phrase_bank import MODE_CHANGED

from console.command_manager import COMMANDS
from console.command_manager import execute
from console.command_manager import resolve_command

from core.log_manager import info


# =============================================================================
# MIXIN DE COMANDOS
# =============================================================================

class AtlasCommandsMixin:
    """
    Añade a Atlas la resolución y ejecución de comandos.
    """

    # =========================================================================
    # GESTIÓN PRINCIPAL
    # =========================================================================

    def _handle_command(
        self,
        original_text: str,
        normalized_text: str,
    ) -> bool | None:
        """
        Resuelve y ejecuta una orden.

        Orden de procesamiento:

            1. Órdenes de identidad del asistente.
            2. Órdenes de modo.
            3. Configuración del cambio automático.
            4. Consultas sobre identidad y modo.
            5. Comandos generales registrados.

        Devuelve:
            None:
                La entrada no era un comando.

            True:
                Atlas debe continuar.

            False:
                Atlas debe finalizar.
        """

        # ---------------------------------------------------------------------
        # 1. ÓRDENES DE IDENTIDAD Y PERSONALIDAD
        # ---------------------------------------------------------------------

        identity_result = (
            self._handle_assistant_identity_command(
                original_text=original_text,
                normalized_text=normalized_text,
            )
        )

        if identity_result is not None:
            return identity_result

        # ---------------------------------------------------------------------
        # 2. COMANDOS GENERALES
        # ---------------------------------------------------------------------

        resolved_command = resolve_command(
            normalized_text
        )

        if resolved_command is None:
            return None

        info(
            f"Comando ejecutado: {resolved_command}. "
            f"Entrada original: {original_text}"
        )

        return execute(
            resolved_command
        )

    # =========================================================================
    # IDENTIDAD DEL ASISTENTE
    # =========================================================================

    def _handle_assistant_identity_command(
        self,
        original_text: str,
        normalized_text: str,
    ) -> bool | None:
        """
        Procesa órdenes relacionadas con Daxter, Coco y sus modos.

        Devuelve:
            True:
                La orden ha sido reconocida y procesada.

            None:
                La entrada no era una orden de identidad.
        """

        # ---------------------------------------------------------------------
        # CAMBIO A DAXTER
        # ---------------------------------------------------------------------

        daxter_commands = {
            "daxter",
            "pon a daxter",
            "ponme a daxter",
            "cambia a daxter",
            "cambiar a daxter",
            "quiero a daxter",
            "quiero hablar con daxter",
            "dejame hablar con daxter",
            "activa a daxter",
            "identidad daxter",
            "usa a daxter",
            "vuelve a daxter",
        }

        if normalized_text in daxter_commands:

            return self._change_assistant_identity(
                identity_name="daxter",
                original_text=original_text,
            )

        # ---------------------------------------------------------------------
        # CAMBIO A COCO
        # ---------------------------------------------------------------------

        coco_commands = {
            "coco",
            "pon a coco",
            "ponme a coco",
            "cambia a coco",
            "cambiar a coco",
            "quiero a coco",
            "quiero hablar con coco",
            "dejame hablar con coco",
            "activa a coco",
            "identidad coco",
            "usa a coco",
            "vuelve a coco",
        }

        if normalized_text in coco_commands:

            return self._change_assistant_identity(
                identity_name="coco",
                original_text=original_text,
            )

        # ---------------------------------------------------------------------
        # RESTAURAR IDENTIDAD PREDETERMINADA
        # ---------------------------------------------------------------------

        reset_identity_commands = {
            "identidad predeterminada",
            "vuelve a la identidad predeterminada",
            "restaura la identidad",
            "restaura la identidad predeterminada",
            "reinicia la identidad",
        }

        if normalized_text in reset_identity_commands:

            self.identity_manager.reset_identity()

            active_identity = (
                self.identity_manager
                .get_active_display_name()
            )

            print()
            print(
                f"Identidad predeterminada restaurada: "
                f"{active_identity}."
            )

            info(
                f"Identidad del asistente restaurada. "
                f"Entrada original: {original_text}. "
                f"Identidad activa: {active_identity}."
            )

            return True

        # ---------------------------------------------------------------------
        # CAMBIO MANUAL DE MODO
        # ---------------------------------------------------------------------

        mode_name = (
            self._resolve_manual_mode_command(
                normalized_text
            )
        )

        if mode_name is not None:

            return self._change_assistant_mode(
                mode_name=mode_name,
                original_text=original_text,
            )

        # ---------------------------------------------------------------------
        # VOLVER AL MODO PREDETERMINADO
        # ---------------------------------------------------------------------

        default_mode_commands = {
            "vuelve al modo predeterminado",
            "volver al modo predeterminado",
            "modo predeterminado",
            "restaura el modo",
            "restaura el modo predeterminado",
            "libera el modo y vuelve al predeterminado",
        }

        if normalized_text in default_mode_commands:

            self.identity_manager.return_to_default_mode()

            mode_label = (
                self.identity_manager
                .get_active_mode_label()
            )

            print()
            print(
                f"He vuelto al modo "
                f"{mode_label}."
            )

            info(
                f"Modo predeterminado restaurado. "
                f"Entrada original: {original_text}. "
                f"Modo activo: "
                f"{self.identity_manager.get_active_mode_name()}."
            )

            return True

        # ---------------------------------------------------------------------
        # LIBERAR BLOQUEO MANUAL
        # ---------------------------------------------------------------------

        unlock_mode_commands = {
            "libera el modo",
            "desbloquea el modo",
            "quita el bloqueo del modo",
            "permite cambios automaticos",
            "deja que cambies de modo",
            "puedes volver a cambiar de modo solo",
            "puedes cambiar de modo automaticamente",
        }

        if normalized_text in unlock_mode_commands:

            self.identity_manager.unlock_manual_mode()

            print()
            print(
                "He liberado el modo actual. "
                "Ya puedo volver a cambiarlo automáticamente."
            )

            info(
                f"Bloqueo manual de modo liberado. "
                f"Entrada original: {original_text}."
            )

            return True

        # ---------------------------------------------------------------------
        # ACTIVAR CAMBIO AUTOMÁTICO
        # ---------------------------------------------------------------------

        enable_automatic_commands = {
            "activa el cambio automatico",
            "activar cambio automatico",
            "activa los modos automaticos",
            "activar modos automaticos",
            "cambia de modo automaticamente",
            "puedes cambiar de modo solo",
            "elige el modo automaticamente",
            "modo automatico activado",
        }

        if normalized_text in enable_automatic_commands:

            self.identity_manager.set_automatic_mode(
                True
            )

            print()
            print(
                "Cambio automático de modo activado."
            )

            if (
                self.identity_manager
                .is_manual_mode_locked()
            ):

                print(
                    "El modo actual sigue bloqueado manualmente. "
                    "Puedes decir «libera el modo» para permitir "
                    "que cambie automáticamente."
                )

            info(
                f"Cambio automático de modo activado. "
                f"Entrada original: {original_text}."
            )

            return True

        # ---------------------------------------------------------------------
        # DESACTIVAR CAMBIO AUTOMÁTICO
        # ---------------------------------------------------------------------

        disable_automatic_commands = {
            "desactiva el cambio automatico",
            "desactivar cambio automatico",
            "desactiva los modos automaticos",
            "desactivar modos automaticos",
            "no cambies de modo automaticamente",
            "no cambies de modo solo",
            "mantente en este modo",
            "modo automatico desactivado",
        }

        if normalized_text in disable_automatic_commands:

            self.identity_manager.set_automatic_mode(
                False
            )

            print()
            print(
                "Cambio automático de modo desactivado."
            )

            info(
                f"Cambio automático de modo desactivado. "
                f"Entrada original: {original_text}."
            )

            return True

        # ---------------------------------------------------------------------
        # CONSULTAR IDENTIDAD ACTIVA
        # ---------------------------------------------------------------------

        identity_query_commands = {
            "quien eres",
            "quien esta hablando",
            "que identidad tienes",
            "que identidad esta activa",
            "cual es tu identidad",
            "eres daxter o coco",
            "estoy hablando con daxter o coco",
            "con quien estoy hablando",
        }

        if normalized_text in identity_query_commands:

            self._show_active_assistant_identity()

            return True

        # ---------------------------------------------------------------------
        # CONSULTAR MODO ACTIVO
        # ---------------------------------------------------------------------

        mode_query_commands = {
            "que modo tienes",
            "que modo esta activo",
            "en que modo estas",
            "cual es tu modo",
            "que modo estas usando",
            "estas en modo trabajo",
            "estas en modo clasico",
            "estas en modo divertido",
            "estas en modo bromista",
            "estas en modo empatico",
            "dime en que modo estas",
            "en que modo te encuentras",
        }

        if normalized_text in mode_query_commands:

            self._show_active_assistant_mode()

            return True

        # ---------------------------------------------------------------------
        # CONSULTAR ESTADO COMPLETO
        # ---------------------------------------------------------------------

        state_query_commands = {
            "estado de personalidad",
            "estado de identidad",
            "muestra tu personalidad",
            "muestra el estado de personalidad",
            "muestra el estado de identidad",
            "que personalidad estas usando",
            "configuracion de personalidad",
        }

        if normalized_text in state_query_commands:

            self._show_assistant_identity_state()

            return True

        return None

    # =========================================================================
    # RESOLUCIÓN DE MODOS
    # =========================================================================

    @staticmethod
    def _resolve_manual_mode_command(
        normalized_text: str,
    ) -> str | None:
        """
        Convierte una orden manual en el nombre interno del modo.

        Devuelve:
            str:
                Nombre interno del modo.

            None:
                La entrada no coincide con ninguna orden manual.
        """

        mode_commands = {
            CLASSIC_MODE: {
                "modo clasico",
                "modo normal",
                "cambia a modo clasico",
                "cambia al modo clasico",
                "cambiar a modo clasico",
                "cambia a modo normal",
                "cambia al modo normal",
                "cambiar a modo normal",
                "activa el modo clasico",
                "activa el modo normal",
                "ponte en modo clasico",
                "ponte en modo normal",
                "vuelve al modo clasico",
                "vuelve al modo normal",
                "habla normal",
            },

            WORK_MODE: {
                "modo trabajo",
                "cambia a modo trabajo",
                "cambia al modo trabajo",
                "cambiar a modo trabajo",
                "activa el modo trabajo",
                "ponte en modo trabajo",
                "ponte serio",
                "vamos a trabajar",
                "modo aplicado",
                "ponte aplicado",
            },

            FUN_MODE: {
                "modo divertido",
                "modo bromista",
                "modo fiesta",
                "cambia a modo divertido",
                "cambia al modo divertido",
                "cambiar a modo divertido",
                "cambia a modo bromista",
                "cambia al modo bromista",
                "cambiar a modo bromista",
                "cambia a modo fiesta",
                "cambia al modo fiesta",
                "activa el modo divertido",
                "activa el modo fiesta",
                "ponte en modo divertido",
                "ponte divertido",
                "ponte gracioso",
                "vamos a divertirnos",
            },

            EMPATHETIC_MODE: {
                "modo empatico",
                "cambia a modo empatico",
                "cambia al modo empatico",
                "cambiar a modo empatico",
                "activa el modo empatico",
                "ponte en modo empatico",
                "ponte empatico",
                "ponte comprensivo",
                "ponte comprensiva",
                "quiero que seas mas comprensivo",
                "quiero que seas mas comprensiva",
            },
        }

        for mode_name, commands in mode_commands.items():

            if normalized_text in commands:
                return mode_name

        return None

    # =========================================================================
    # CAMBIOS
    # =========================================================================

    def _change_assistant_identity(
        self,
        identity_name: str,
        original_text: str,
    ) -> bool:
        """
        Cambia la identidad activa y muestra el resultado.
        """

        previous_identity = (
            self.identity_manager
            .get_active_display_name()
        )

        changed = (
            self.identity_manager
            .change_identity(
                identity_name
            )
        )

        if not changed:

            print()
            print(
                f"No existe ninguna identidad llamada "
                f"«{identity_name}»."
            )

            return True

        active_identity = (
            self.identity_manager
            .get_active_display_name()
        )

        phrase = self.identity_manager.get_phrase(
            category=IDENTITY_CHANGED,
            default=(
                f"Identidad {active_identity} activada."
            ),
        )

        print()
        print(phrase)

        info(
            f"Cambio de identidad del asistente: "
            f"{previous_identity} -> {active_identity}. "
            f"Entrada original: {original_text}."
        )

        return True

    def _change_assistant_mode(
        self,
        mode_name: str,
        original_text: str,
    ) -> bool:
        """
        Cambia manualmente el modo activo.

        El modo queda bloqueado frente a cambios automáticos
        hasta que el usuario lo libere o vuelva al modo
        predeterminado.
        """

        previous_mode = (
            self.identity_manager
            .get_active_mode_name()
        )

        changed = self.identity_manager.set_mode(
            mode_name=mode_name,
            manual=True,
            temporary=False,
            save_preference=True,
        )

        if not changed:

            print()
            print(
                f"No he podido activar el modo "
                f"«{mode_name}»."
            )

            return True

        mode_label = (
            self.identity_manager
            .get_active_mode_label()
        )

        phrase = self.identity_manager.get_phrase(
            category=MODE_CHANGED,
            default=(
                f"Modo {mode_label} activado."
            ),
            mode=mode_label,
        )

        print()
        print(phrase)

        info(
            f"Cambio manual de modo: "
            f"{previous_mode} -> {mode_name}. "
            f"Entrada original: {original_text}."
        )

        return True

    # =========================================================================
    # INFORMACIÓN DEL ESTADO
    # =========================================================================

    def _show_active_assistant_identity(
        self,
    ) -> None:
        """
        Muestra la identidad activa del asistente.
        """

        identity = (
            self.identity_manager
            .get_active_identity()
        )

        print()
        print(
            f"Ahora estás hablando con "
            f"{identity.display_name}."
        )

        print()
        print(
            identity.description
        )

    def _show_active_assistant_mode(
        self,
    ) -> None:
        """
        Muestra el modo activo y su estado.
        """

        mode_label = (
            self.identity_manager
            .get_active_mode_label()
        )

        automatic_state = (
            "activado"
            if (
                self.identity_manager
                .is_automatic_mode_enabled()
            )
            else "desactivado"
        )

        manual_lock_state = (
            "sí"
            if (
                self.identity_manager
                .is_manual_mode_locked()
            )
            else "no"
        )

        temporary_state = (
            "sí"
            if (
                self.identity_manager
                .is_temporary_mode_active()
            )
            else "no"
        )

        print()
        print(
            f"Modo activo: {mode_label}."
        )

        print(
            f"Cambio automático: "
            f"{automatic_state}."
        )

        print(
            f"Bloqueado manualmente: "
            f"{manual_lock_state}."
        )

        print(
            f"Modo temporal: "
            f"{temporary_state}."
        )

    def _show_assistant_identity_state(
        self,
    ) -> None:
        """
        Muestra el estado completo de identidad
        y personalidad del asistente.
        """

        state = (
            self.identity_manager
            .get_state()
        )

        automatic_state = (
            "activado"
            if state["automatic_mode"]
            else "desactivado"
        )

        manual_lock_state = (
            "sí"
            if state["manual_mode_lock"]
            else "no"
        )

        temporary_state = (
            "sí"
            if state["temporary_mode"]
            else "no"
        )

        print()
        print(
            "Estado de identidad del asistente:"
        )

        print()
        print(
            f"- Interlocutor: "
            f"{state['user'] or 'No cargado'}"
        )

        print(
            f"- Identidad: "
            f"{state['identity_display_name']}"
        )

        print(
            f"- Modo predeterminado: "
            f"{state['default_mode']}"
        )

        print(
            f"- Modo activo: "
            f"{state['current_mode_label']}"
        )

        print(
            f"- Cambio automático: "
            f"{automatic_state}"
        )

        print(
            f"- Bloqueo manual: "
            f"{manual_lock_state}"
        )

        print(
            f"- Modo temporal: "
            f"{temporary_state}"
        )

    # =========================================================================
    # API DE COMANDOS GENERALES
    # =========================================================================

    def execute(
        self,
        command: str,
    ) -> bool:
        """
        Ejecuta directamente un comando general.
        """

        return execute(
            command
        )

    def get_commands(
        self,
    ) -> dict:
        """
        Devuelve todos los comandos generales registrados.

        Las órdenes internas de identidad no forman parte
        todavía de COMMANDS.
        """

        return COMMANDS