"""Diagnóstico seguro de la última selección del router de IA."""
from __future__ import annotations

from core import context
from commands.admin_policy import require_admin_user

COMMAND = {
    "name": "estado ia",
    "description": "Muestra modo de sesión, última ruta, modelo, fallback y latencia sin razonamiento privado.",
    "category": "Inteligencia artificial",
    "owner_only": True,
    "capability": "atlas_admin",
    "aliases": ["estado modelo ia", "diagnostico ia", "diagnóstico ia"],
}


def execute() -> bool:
    if not require_admin_user():
        return True
    atlas = getattr(context, "atlas", None)
    if atlas is None:
        print("\nNo encuentro la instancia activa de Atlas.")
        return True
    mode = atlas.conversation_manager.get_ai_override()
    trace = getattr(atlas, "last_ai_trace", None)
    print("\nESTADO DE IA")
    print(f"Modo de esta sesión: {mode}")
    if trace is None:
        print("Última ruta: todavía no hay una consulta generativa en esta sesión.")
        return True
    print(f"Última ruta: {trace.final_role.value}")
    print(f"Modelo físico: {trace.model}")
    print(f"Fallback: {'sí' if trace.fallback else 'no'}")
    print(f"Latencia: {trace.latency_seconds:.3f} s")
    return True
