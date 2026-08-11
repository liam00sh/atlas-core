"""Comandos conversacionales para gestionar las preferencias de voz."""

from __future__ import annotations

from pathlib import Path
import re

from core import context
from voice.models import AssistantIdentity
from voice.preferences.manager import VoicePreferenceManager


COMMAND = {
    "name": "voz",
    "description": (
        "Consulta o cambia la voz, la velocidad, el volumen "
        "y el fallback del usuario activo."
    ),
    "category": "Voz",
    "author": "Alex",
    "version": "1.0",
    "aliases": [
        "voces",
        "configurar voz",
        "preferencias de voz",
        "ajustes de voz",
    ],
    "examples": [
        "voz",
        "voz estado",
        "voz daxter alex",
        "voz daxter santa",
        "voz coco dora",
        "voz velocidad 1.1",
        "voz volumen 0.8",
        "voz fallback activar",
    ],
}


VOICE_ALIASES = {
    "daxter oficial": "daxter_official",
    "daxter alex": "daxter_alex",
    "daxter santa": "daxter_santa",
    "coco oficial": "coco_official",
    "coco dora": "coco_dora",
}


def _manager() -> VoicePreferenceManager:
    atlas = context.atlas
    if atlas is None:
        raise RuntimeError("Atlas todavía no está inicializado.")

    project_root = Path(__file__).resolve().parent.parent
    return VoicePreferenceManager(
        storage_path=(
            project_root
            / "data"
            / "voice"
            / "user_preferences.json"
        ),
        user_provider=lambda: atlas.get_user(),
    )


def _show(preferences) -> None:
    print()
    print("Preferencias de voz")
    print(f"Daxter: {preferences.daxter_voice_id}")
    print(f"Coco: {preferences.coco_voice_id}")
    print(
        "Fallback: "
        + ("activado" if preferences.fallback_enabled else "desactivado")
    )
    print(f"Velocidad: {preferences.speech_rate:.2f}")
    print(f"Volumen: {preferences.speech_volume:.2f}")


def execute(argument: str | None = None):
    manager = _manager()
    text = (argument or "").strip().casefold()

    if not text or text in {
        "estado",
        "mostrar",
        "ver",
        "configuracion",
        "configuración",
    }:
        _show(manager.get_current())
        return

    if text in VOICE_ALIASES:
        voice_id = VOICE_ALIASES[text]
        identity = (
            AssistantIdentity.COCO
            if voice_id.startswith("coco_")
            else AssistantIdentity.DAXTER
        )
        manager.set_voice(
            identity=identity,
            voice_id=voice_id,
        )
        print()
        print(f"Voz guardada: {voice_id}")
        return

    fallback_match = re.fullmatch(
        r"fallback\s+(activar|activado|on|si|sí|desactivar|desactivado|off|no)",
        text,
    )
    if fallback_match:
        enabled = fallback_match.group(1) in {
            "activar",
            "activado",
            "on",
            "si",
            "sí",
        }
        manager.set_fallback_enabled(enabled)
        print()
        print(
            "Fallback "
            + ("activado." if enabled else "desactivado.")
        )
        return

    value_match = re.fullmatch(
        r"(velocidad|volumen)\s+([0-9]+(?:[.,][0-9]+)?)",
        text,
    )
    if value_match:
        field = value_match.group(1)
        value = float(value_match.group(2).replace(",", "."))

        try:
            if field == "velocidad":
                manager.set_speech_rate(value)
                print()
                print(f"Velocidad guardada: {value:.2f}")
            else:
                manager.set_speech_volume(value)
                print()
                print(f"Volumen guardado: {value:.2f}")
        except ValueError as exc:
            print()
            print(str(exc))
        return

    print()
    print("No he entendido la configuración de voz.")
    print("Ejemplos:")
    print("• voz daxter alex")
    print("• voz daxter santa")
    print("• voz coco dora")
    print("• voz velocidad 1.1")
    print("• voz volumen 0.8")
    print("• voz fallback activar")
