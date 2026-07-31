"""
===============================================================================
Proyecto Atlas
Archivo: commands/help.py

Descripción:
    Implementa el comando "ayuda".

    Su función es mostrar la ayuda contextual construida por
    console.command_help según el usuario y sus permisos efectivos.

Ejemplo:

    Atlas > ayuda

        fecha          Muestra la fecha y la hora actuales.
        salir          Finaliza Atlas o cierra el perfil temporal.
        version        Muestra la versión instalada de Atlas.

Flujo:

    Usuario
        │
        ▼
      ayuda
        │
        ▼
command_help.py
        │
        ▼
Catálogo contextual y permisos
        │
        ▼
Recorrer comandos
        │
        ▼
Mostrar listado
===============================================================================
"""


# =============================================================================
# METADATOS DEL COMANDO
# =============================================================================

COMMAND = {

    # Nombre principal.
    "name": "ayuda",

    # Descripción mostrada al usuario.
    "description": "Muestra todos los comandos disponibles.",

    # Categoría.
    "category": "Sistema",

    # Autor.
    "author": "REDACTED_2c7b6821719d",

    # Versión del comando.
    "version": "1.0",

    # Alias aceptados.
    "aliases": [

        "help",

        "?",

    ],

    # Ejemplos.
    "examples": [

        "ayuda",

    ],

}


def execute():
    """Muestra la ayuda completa generada desde el catálogo central."""
    from console.command_help import render_help
    print()
    print(render_help())
