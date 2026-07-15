"""
===============================================================================
Proyecto Atlas
Archivo: commands/info.py

Descripción:
    Implementa el comando "info".

    Su función es mostrar información básica sobre la instancia de Atlas
    que se está ejecutando.

    La información mostrada incluye:

    - Nombre del asistente.
    - Nombre del proyecto.
    - Versión instalada.
    - Estado actual.

    Los datos se obtienen directamente desde la instancia principal de
    Atlas almacenada en core.context.
===============================================================================
"""

# =============================================================================
# IMPORTACIONES
# =============================================================================

from core import context


# =============================================================================
# METADATOS DEL COMANDO
# =============================================================================

COMMAND = {

    "name": "info",

    "description": "Información del asistente.",

    "category": "Sistema",

    "author": "Liam",

    "version": "1.0",

    "aliases": [

        "acerca",

        "about",

    ],

    "examples": [

        "info",

    ],

}


def execute() -> None:
    """
    Ejecuta el comando "info".
    """

    # Recuperamos la instancia actual de Atlas.
    atlas = context.atlas

    # Protección adicional por si el comando se ejecutara
    # antes de inicializar Atlas.
    if atlas is None:

        print()

        print(
            "Atlas todavía no está inicializado."
        )

        return

    print()

    print(
        f"Asistente : {atlas.get_name()}"
    )

    print(
        f"Proyecto  : {atlas.get_project()}"
    )

    print(
        f"Versión   : {atlas.get_version()}"
    )

    print(
        "Estado    : Operativo"
    )