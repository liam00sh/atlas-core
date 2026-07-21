"""
===============================================================================
Proyecto Atlas
Archivo: commands/help.py

Descripción:
    Implementa el comando "ayuda".

    Su función es mostrar un listado con todos los comandos disponibles
    registrados en Atlas junto con una breve descripción.

    El listado se genera automáticamente a partir del registro de comandos
    creado por command_manager.py.

    Esto significa que, al crear un nuevo comando dentro de la carpeta
    commands/, aparecerá automáticamente en la ayuda sin modificar este
    archivo.

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
command_manager.py
        │
        ▼
Diccionario COMMANDS
        │
        ▼
Recorrer comandos
        │
        ▼
Mostrar listado
===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

# Importamos el diccionario global donde command_manager registra
# automáticamente todos los comandos disponibles.
#
# Ejemplo:
#
# COMMANDS = {
#     "fecha": commands.fecha,
#     "hora": commands.fecha,
#     "salir": commands.exit,
#     "help": commands.help,
# }
from console.command_manager import COMMANDS


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
    "author": "Liam",

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
