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

Ejemplo:

    Atlas > info

        Asistente : Daxter
        Proyecto  : Atlas Project
        Versión   : 0.2.0
        Estado    : Operativo

Flujo:

    Usuario
        │
        ▼
      info
        │
        ▼
context.atlas
        │
        ▼
get_name()
get_project()
get_version()
        │
        ▼
Mostrar información
===============================================================================
"""

# =============================================================================
# IMPORTACIONES
# =============================================================================

# Importamos la referencia compartida a la instancia principal de Atlas.
#
# Esta variable es inicializada en main.py:
#
#     atlas = Atlas()
#     context.atlas = atlas
#
# Gracias a ello, cualquier comando puede consultar información del núcleo
# sin necesidad de recibir la instancia como parámetro.
from core.context import atlas


# =============================================================================
# METADATOS DEL COMANDO
# =============================================================================

COMMAND = {

    # Nombre principal del comando.
    "name": "info",

    # Descripción mostrada en el comando "ayuda".
    "description": "Información del asistente.",

    # Categoría.
    "category": "Sistema",

    # Autor.
    "author": "Liam",

    # Versión del comando.
    "version": "1.0",

    # Alias disponibles.
    "aliases": [

        "acerca",

        "about",

    ],

    # Ejemplos de uso.
    "examples": [

        "info",

    ],

}


def execute():
    """
    Ejecuta el comando "info".

    No recibe parámetros.

    No devuelve ningún valor.

    Funcionamiento:

        Consulta la instancia principal de Atlas y muestra
        información general sobre el asistente.

    Al no devolver ningún valor, command_manager interpretará
    automáticamente que Atlas debe continuar funcionando.
    """

    # Línea en blanco para mejorar la presentación.
    print()

    # -------------------------------------------------------------------------
    # Mostramos el nombre del asistente.
    #
    # Ejemplo:
    #
    # Daxter
    # -------------------------------------------------------------------------
    print(
        f"Asistente : {atlas.get_name()}"
    )

    # -------------------------------------------------------------------------
    # Mostramos el nombre del proyecto.
    #
    # Ejemplo:
    #
    # Atlas Project
    # -------------------------------------------------------------------------
    print(
        f"Proyecto  : {atlas.get_project()}"
    )

    # -------------------------------------------------------------------------
    # Mostramos la versión actual de Atlas.
    #
    # Ejemplo:
    #
    # 0.2.0
    # -------------------------------------------------------------------------
    print(
        f"Versión   : {atlas.get_version()}"
    )

    # -------------------------------------------------------------------------
    # Estado del asistente.
    #
    # Actualmente siempre es "Operativo".
    #
    # En futuras versiones podría indicar estados como:
    #
    # - Operativo
    # - Inicializando
    # - Modo mantenimiento
    # - IA desconectada
    # - Sin conexión
    # - Error
    # -------------------------------------------------------------------------
    print(
        "Estado    : Operativo"
    )