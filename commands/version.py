"""
===============================================================================
Proyecto Atlas
Archivo: commands/version.py

Descripción:
    Implementa el comando "version".

    Su función es mostrar el nombre del proyecto y la versión instalada
    de Atlas.

    La información se obtiene directamente desde el módulo core.version,
    que centraliza todos los datos relacionados con la identidad del
    proyecto.

    De esta forma, si la versión cambia, solo será necesario modificar
    un único archivo.

Ejemplo:

    Atlas > version

        Atlas Project
        Versión 0.3.1

Flujo:

    Usuario
        │
        ▼
     version
        │
        ▼
core.version
        │
        ▼
PROJECT_NAME
VERSION
        │
        ▼
Mostrar información
===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

# Importamos el nombre oficial del proyecto.
#
# Ejemplo:
#
# Atlas Project
from core.version import PROJECT_NAME

# Importamos la versión actual del proyecto.
#
# Ejemplo:
#
# 0.3.1
from core.version import VERSION


# =============================================================================
# METADATOS DEL COMANDO
# =============================================================================

# Información utilizada por command_manager.py para registrar
# automáticamente el comando.
COMMAND = {

    # Nombre principal del comando.
    "name": "version",

    # Descripción mostrada en el comando "ayuda".
    "description": "Muestra la versión instalada de Atlas.",

    # Categoría.
    "category": "Sistema",

    # Autor.
    "author": "Liam",

    # Versión del propio comando.
    "version": "1.0",

    # Alias disponibles.
    #
    # Todos ejecutarán exactamente este mismo comando.
    "aliases": [

        "ver",

        "v",

    ],

    # Ejemplos de utilización.
    "examples": [

        "version",

        "ver",

    ],

}


def execute():
    """
    Ejecuta el comando "version".

    No recibe parámetros.

    No devuelve ningún valor.

    Funcionamiento:

        Muestra el nombre del proyecto y la versión
        actualmente instalada.

    Al no devolver ningún valor, command_manager interpretará
    automáticamente que Atlas debe continuar funcionando.
    """

    # Línea en blanco para mejorar la presentación.
    print()

    # Mostramos el nombre oficial del proyecto.
    #
    # Ejemplo:
    #
    # Atlas Project
    print(PROJECT_NAME)

    # Mostramos la versión instalada.
    #
    # Ejemplo:
    #
    # Versión 0.3.1
    print(f"Versión {VERSION}")