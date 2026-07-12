"""Comando que muestra un resumen operativo de Atlas."""

from core.context import atlas


COMMAND = {
    "name": "estado",
    "description": "Resumen del estado del sistema.",
    "category": "Sistema",
    "author": "Liam",
    "version": "1.0",
    "aliases": ["status"],
    "examples": ["estado"],
}


def _availability(enabled: bool, unavailable: str = "No disponible") -> str:
    """Convierte una capacidad booleana en un texto legible."""

    return "Disponible" if enabled else unavailable


def execute():
    """Muestra de un vistazo el estado actual de Atlas."""

    active_user = atlas.get_user()
    memory_count = atlas.memory.count_memories(active_user)

    # COMMANDS contiene nombres y alias; contamos módulos únicos para no inflar
    # la cifra mostrada al usuario.
    command_count = len({id(module) for module in atlas.get_commands().values()})

    print()
    print(f"Atlas {atlas.get_version()}")
    print(f"Usuario activo : {active_user}")
    print(f"Memorias       : {memory_count}")
    print(f"Comandos       : {command_count}")
    print(f"IA             : {_availability(atlas.can_use_ai())}")
    print(f"Voz            : {_availability(atlas.can_use_voice())}")
    print(
        "Internet       : "
        + ("Activado" if atlas.can_access_internet() else "Desactivado")
    )
    print("Plugins        : 0")
    print("Estado         : Todo operativo.")
