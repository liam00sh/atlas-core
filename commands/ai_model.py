"""Control de desarrollo del selector multimodelo local de Atlas."""
from __future__ import annotations

from core import context
from commands.admin_policy import require_admin_user

COMMAND = {
    "name": "modelo ia",
    "description": "Consulta o cambia el selector local auto/fast/reasoning/deep de esta sesión.",
    "category": "Inteligencia artificial",
    "owner_only": True,
    "capability": "atlas_admin",
    "aliases": [
        "usar ia", "usa modelo", "cambia ia a", "vuelve a ia automatica",
        "vuelve a ia automática",
    ],
}

VALID = {"auto", "fast", "reasoning", "deep"}


def _show(atlas) -> None:
    mode = atlas.conversation_manager.get_ai_override()
    models = atlas.ai_runtime.registry.as_dict()
    print("\nSELECTOR DE IA")
    print(f"Modo de esta sesión: {mode}")
    for role in ("fast", "reasoning", "deep"):
        definition = models[role]
        print(f"• {role}: {definition['model']} ({definition['provider']})")
    print("• external: deshabilitado")


def execute(argument: str | None = None) -> bool:
    if not require_admin_user():
        return True
    atlas = getattr(context, "atlas", None)
    if atlas is None or getattr(atlas, "ai_runtime", None) is None:
        print("\nEl runtime multimodelo local no está disponible.")
        return True
    requested = str(argument or "").strip().casefold()
    if not requested:
        _show(atlas)
        return True
    if requested not in VALID:
        print("\nModo no válido. Usa: modelo ia auto, fast, reasoning o deep.")
        return True
    atlas.conversation_manager.set_ai_override(requested)
    print(f"\nSelector de IA de esta sesión: {requested}.")
    return True
