"""
===============================================================================
Proyecto Atlas
Archivo: core/atlas_commands.py

Descripción:
    Contiene la integración entre Atlas y el sistema de comandos.
===============================================================================
"""

from console.command_manager import COMMANDS
from console.command_manager import resolve_command

from core.log_manager import info


class AtlasCommandsMixin:
    """Añade a Atlas la resolución y ejecución de comandos."""

    def _handle_command(
        self,
        original_text: str,
        normalized_text: str,
    ) -> bool | None:
        """
        Resuelve y ejecuta comandos simples o comandos con argumentos.
        """

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
