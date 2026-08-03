"""
===============================================================================
Proyecto Atlas
Archivo: console/shell.py

Descripción:
    Implementa la consola interactiva de Atlas.

    La consola recibe las entradas del usuario y las envía
    al núcleo mediante Atlas.process().

    Cuando la voz está habilitada, captura la salida visible de cada turno,
    la conserva en pantalla y la reproduce mediante el servicio TTS.
===============================================================================
"""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import sys

from voice.config import VOICE_SPEAK_CONSOLE_OUTPUT
from voice.models import AssistantIdentity
from voice.runtime import build_voice_service


class _TeeOutput:
    """Escribe simultáneamente en la consola y en un búfer."""

    def __init__(self, original, buffer: StringIO) -> None:
        self.original = original
        self.buffer = buffer

    def write(self, text: str) -> int:
        self.original.write(text)
        self.buffer.write(text)
        return len(text)

    def flush(self) -> None:
        self.original.flush()
        self.buffer.flush()


def _active_identity(atlas) -> AssistantIdentity:
    try:
        name = atlas.identity_manager.get_active_identity_name()
    except (AttributeError, RuntimeError):
        return AssistantIdentity.DAXTER

    normalized = str(name).strip().casefold()
    if normalized == AssistantIdentity.COCO.value:
        return AssistantIdentity.COCO
    return AssistantIdentity.DAXTER


def start_shell(atlas) -> None:
    """Inicia el bucle principal de la consola."""

    running = True
    voice_service = build_voice_service()

    while running:
        try:
            command = input("\nAtlas > ")

            if (
                voice_service is None
                or not VOICE_SPEAK_CONSOLE_OUTPUT
            ):
                running = atlas.process(command)
                continue

            captured = StringIO()
            tee = _TeeOutput(sys.stdout, captured)

            with redirect_stdout(tee):
                running = atlas.process(command)

            spoken_text = voice_service.clean_console_text(
                captured.getvalue()
            )
            if spoken_text:
                result = voice_service.speak(
                    spoken_text,
                    identity=_active_identity(atlas),
                )
                if not result.success and result.error:
                    print(
                        "\n[Voz no disponible: "
                        f"{result.error}]"
                    )

        except KeyboardInterrupt:
            print()
            print()
            print("Atlas se ha cerrado manualmente.")
            running = False
