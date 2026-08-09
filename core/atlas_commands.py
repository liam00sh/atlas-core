"""
===============================================================================
Proyecto Atlas
Archivo: core/atlas_commands.py

Descripción:
    Contiene la integración entre Atlas y el sistema de comandos.
===============================================================================
"""

from assistant_identity.mode import CLASSIC_MODE, EMPATHETIC_MODE, FUN_MODE, MODE_LABELS, WORK_MODE

from console.command_help import handle_command_help_request, render_help_for_user
from console.command_manager import COMMANDS
from console.command_manager import resolve_command

from core.log_manager import info


class AtlasCommandsMixin:
    """Añade a Atlas la resolución y ejecución de comandos."""

    def _active_guest_session(self):
        manager = getattr(self, "guest_sessions", None)
        getter = getattr(manager, "get", None)
        return getter() if callable(getter) else None

    def _handle_command(
        self,
        original_text: str,
        normalized_text: str,
    ) -> bool | None:
        """
        Resuelve y ejecuta comandos simples o comandos con argumentos.
        """

        if normalized_text in {
            "vuelve a ia automatica", "volver a ia automatica",
            "vuelve a ia automatico", "volver a ia automatico",
        }:
            from commands import ai_model
            return ai_model.execute("auto")

        identity_result = self._handle_assistant_identity_command(
            original_text,
            normalized_text,
        )
        if identity_result is not None:
            return identity_result

        if handle_command_help_request(original_text) is not None:
            topic = None
            normalized_help = str(original_text).strip().casefold()
            for prefix in ("ayuda ", "help "):
                if normalized_help.startswith(prefix):
                    topic = original_text.strip()[len(prefix):].strip() or None
                    break

            request_context = getattr(self, "channel_request_context", None)
            channel = getattr(request_context, "channel", None) or "pc"
            help_user = self.get_effective_help_user()
            print(
                render_help_for_user(
                    help_user,
                    topic=topic,
                    channel=channel,
                    guest_session=self.guest_sessions.get(),
                    own_bot=bool(help_user.get("own_bot", True)),
                    request_text=original_text,
                )
            )
            return True

        resolved_command = resolve_command(
            normalized_text
        )
        command_argument = None

        if resolved_command is None:
            normalized_words = normalized_text.split()
            original_words = original_text.split()

            for index in range(len(normalized_words) - 1, 0, -1):
                candidate = " ".join(
                    normalized_words[:index]
                )
                resolved_command = resolve_command(
                    candidate
                )

                if resolved_command is not None:
                    command_argument = " ".join(
                        original_words[index:]
                    ).strip()
                    break

        if resolved_command is None:
            return None

        info(
            f"Comando ejecutado: {resolved_command}"
        )

        command_module = COMMANDS[resolved_command]

        if command_argument:
            try:
                result = command_module.execute(
                    command_argument
                )
            except TypeError:
                result = command_module.execute()
        else:
            result = command_module.execute()

        if result is None:
            return True

        return result

    def _handle_assistant_identity_command(
        self,
        original_text: str,
        normalized_text: str,
    ) -> bool | None:
        """Procesa órdenes exactas de identidad, personalidad y modo."""
        identity_commands = {
            "daxter": "daxter", "pon a daxter": "daxter",
            "ponme a daxter": "daxter", "cambia a daxter": "daxter",
            "cambiar a daxter": "daxter", "quiero a daxter": "daxter",
            "quiero hablar con daxter": "daxter", "dejame hablar con daxter": "daxter",
            "activa a daxter": "daxter", "identidad daxter": "daxter",
            "usa a daxter": "daxter", "vuelve a daxter": "daxter",
            "coco": "coco", "pon a coco": "coco", "ponme a coco": "coco",
            "cambia a coco": "coco", "cambiar a coco": "coco",
            "quiero a coco": "coco", "quiero hablar con coco": "coco",
            "dejame hablar con coco": "coco", "activa a coco": "coco",
            "identidad coco": "coco", "usa a coco": "coco", "vuelve a coco": "coco",
        }
        identity_name = identity_commands.get(normalized_text)
        if identity_name is not None:
            return self._change_assistant_identity(identity_name, original_text)

        if normalized_text in {
            "identidad predeterminada", "vuelve a la identidad predeterminada",
            "restaura la identidad", "restaura la identidad predeterminada",
            "reinicia la identidad",
        }:
            self.identity_manager.reset_identity()
            print(f"\nIdentidad predeterminada restaurada: {self.identity_manager.get_active_display_name()}.")
            return True

        mode_name = self._resolve_manual_mode_command(normalized_text)
        if mode_name is not None:
            return self._change_assistant_mode(mode_name, original_text)

        if normalized_text in {
            "vuelve al modo predeterminado", "volver al modo predeterminado",
            "modo predeterminado", "restaura el modo", "restaura el modo predeterminado",
            "libera el modo y vuelve al predeterminado",
        }:
            guest = self._active_guest_session()
            if guest is not None:
                guest.mode_name = CLASSIC_MODE
                print(f"\nHe vuelto al modo {MODE_LABELS[CLASSIC_MODE]} en esta sesión invitada.")
                return True
            self.identity_manager.return_to_default_mode()
            print(f"\nHe vuelto al modo {self.identity_manager.get_active_mode_label()}.")
            return True

        if normalized_text in {
            "libera el modo", "desbloquea el modo", "quita el bloqueo del modo",
            "permite cambios automaticos", "deja que cambies de modo",
            "puedes volver a cambiar de modo solo", "puedes cambiar de modo automaticamente",
        }:
            if self._active_guest_session() is not None:
                print("\nEl modo invitado ya es temporal y no altera la preferencia del propietario.")
                return True
            self.identity_manager.unlock_manual_mode()
            print("\nHe liberado el modo actual. Ya puedo volver a cambiarlo automáticamente.")
            return True

        automatic_commands = {
            "activa el cambio automatico": True, "activar cambio automatico": True,
            "activa los modos automaticos": True, "activar modos automaticos": True,
            "cambia de modo automaticamente": True, "puedes cambiar de modo solo": True,
            "elige el modo automaticamente": True, "modo automatico activado": True,
            "desactiva el cambio automatico": False, "desactivar cambio automatico": False,
            "desactiva los modos automaticos": False, "desactivar modos automaticos": False,
            "no cambies de modo automaticamente": False, "no cambies de modo solo": False,
            "mantente en este modo": False, "modo automatico desactivado": False,
        }
        if normalized_text in automatic_commands:
            if self._active_guest_session() is not None:
                print("\nEl cambio automático no modifica preferencias desde una sesión invitada.")
                return True
            automatic = automatic_commands[normalized_text]
            self.identity_manager.set_automatic_mode(automatic)
            state = "activado" if automatic else "desactivado"
            print(f"\nCambio automático de modo {state}.")
            return True

        if normalized_text in {
            "quien eres", "quien esta hablando", "que identidad tienes",
            "que identidad esta activa", "cual es tu identidad", "eres daxter o coco",
            "estoy hablando con daxter o coco", "con quien estoy hablando",
        }:
            self._show_active_assistant_identity()
            return True

        if normalized_text in {
            "que modo tienes", "que modo esta activo", "en que modo estas",
            "cual es tu modo", "que modo estas usando", "estas en modo trabajo",
            "estas en modo clasico", "estas en modo divertido", "estas en modo bromista",
            "estas en modo empatico", "dime en que modo estas", "en que modo te encuentras",
        }:
            self._show_active_assistant_mode()
            return True

        return None

    @staticmethod
    def _resolve_manual_mode_command(normalized_text: str) -> str | None:
        mode_commands = {
            CLASSIC_MODE: {
                "modo clasico", "modo normal", "cambia a modo clasico",
                "cambia al modo clasico", "cambiar a modo clasico", "cambia a modo normal",
                "cambia al modo normal", "cambiar a modo normal", "activa el modo clasico",
                "activa el modo normal", "ponte en modo clasico", "ponte en modo normal",
                "vuelve al modo clasico", "vuelve al modo normal", "habla normal",
            },
            WORK_MODE: {
                "modo trabajo", "cambia a modo trabajo", "cambia al modo trabajo",
                "cambiar a modo trabajo", "activa el modo trabajo", "ponte en modo trabajo",
                "ponte serio", "vamos a trabajar", "modo aplicado", "ponte aplicado",
            },
            FUN_MODE: {
                "modo divertido", "modo bromista", "modo fiesta", "cambia a modo divertido",
                "cambia al modo divertido", "cambiar a modo divertido", "cambia a modo bromista",
                "cambia al modo bromista", "cambiar a modo bromista", "cambia a modo fiesta",
                "cambia al modo fiesta", "activa el modo divertido", "activa el modo fiesta",
                "ponte en modo divertido", "ponte divertido", "ponte gracioso", "vamos a divertirnos",
            },
            EMPATHETIC_MODE: {
                "modo empatico", "cambia a modo empatico", "cambia al modo empatico",
                "cambiar a modo empatico", "activa el modo empatico", "ponte en modo empatico",
                "ponte empatico", "ponte comprensivo", "ponte comprensiva",
                "quiero que seas mas comprensivo", "quiero que seas mas comprensiva",
            },
        }
        return next((mode for mode, commands in mode_commands.items() if normalized_text in commands), None)

    def _change_assistant_identity(self, identity_name: str, original_text: str) -> bool:
        guest = self._active_guest_session()
        if guest is not None:
            guest.assistant_name = identity_name.capitalize()
            print(f"\nIdentidad {guest.assistant_name} activada para esta sesión invitada.")
            return True
        previous = self.identity_manager.get_active_display_name()
        if not self.identity_manager.change_identity(identity_name):
            print(f"\nNo existe ninguna identidad llamada «{identity_name}».")
            return True
        active = self.identity_manager.get_active_display_name()
        print(f"\nIdentidad {active} activada.")
        info(f"Cambio de identidad del asistente: {previous} -> {active}. Entrada original: {original_text}.")
        return True

    def _change_assistant_mode(self, mode_name: str, original_text: str) -> bool:
        guest = self._active_guest_session()
        if guest is not None:
            guest.mode_name = mode_name
            print(f"\nModo {MODE_LABELS[mode_name]} activado para esta sesión invitada.")
            return True
        previous = self.identity_manager.get_active_mode_name()
        changed = self.identity_manager.set_mode(
            mode_name=mode_name,
            manual=True,
            temporary=False,
            save_preference=True,
        )
        if not changed:
            print(f"\nNo he podido activar el modo «{mode_name}».")
            return True
        print(f"\nModo {self.identity_manager.get_active_mode_label()} activado.")
        info(f"Cambio manual de modo: {previous} -> {mode_name}. Entrada original: {original_text}.")
        return True

    def _show_active_assistant_identity(self) -> None:
        guest = self._active_guest_session()
        if guest is not None:
            print(f"\nAhora estás hablando con {guest.assistant_name} en una sesión invitada.")
            return
        identity = self.identity_manager.get_active_identity()
        print(f"\nAhora estás hablando con {identity.display_name}.\n\n{identity.description}")

    def _show_active_assistant_mode(self) -> None:
        guest = self._active_guest_session()
        if guest is not None:
            label = MODE_LABELS.get(guest.mode_name, guest.mode_name)
            print(f"\nModo activo de la sesión invitada: {label}.")
            return
        automatic = "activado" if self.identity_manager.is_automatic_mode_enabled() else "desactivado"
        manual = "sí" if self.identity_manager.is_manual_mode_locked() else "no"
        temporary = "sí" if self.identity_manager.is_temporary_mode_active() else "no"
        print(
            f"\nModo activo: {self.identity_manager.get_active_mode_label()}.\n"
            f"Cambio automático: {automatic}.\n"
            f"Bloqueado manualmente: {manual}.\n"
            f"Modo temporal: {temporary}."
        )
