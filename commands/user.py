"""
===============================================================================
Proyecto Atlas
Archivo: commands/user.py

Descripción:
    Implementa el comando "usuario".

    Su función es mostrar el usuario que está utilizando Atlas
    en este momento.

    Este comando consulta directamente la instancia principal de Atlas
    mediante el contexto compartido (core.context).

    Gracias al sistema de usuarios, Atlas puede diferenciar entre:

    - Usuario principal (REDACTED_2c7b6821719d)
    - Usuarios temporales (REDACTED_bc04a68d9192, REDACTED_0392c3d1b4d3, etc.)

Ejemplo:

    Atlas > usuario

        Usuario activo: REDACTED_2c7b6821719d

Flujo:

    Usuario
        │
        ▼
    usuario
        │
        ▼
context.atlas
        │
        ▼
get_user()
        │
        ▼
Mostrar usuario activo
===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

# Importamos el contexto global del proyecto.
#
# Desde aquí podemos acceder a la única instancia de Atlas creada
# en main.py mediante:
#
#     context.atlas
#
# Esto permite consultar información del asistente sin necesidad
# de pasar la instancia como parámetro.
from core import context


# =============================================================================
# METADATOS DEL COMANDO
# =============================================================================

# Información utilizada por command_manager.py para registrar
# automáticamente el comando.
COMMAND = {

    # Nombre principal del comando.
    "name": "usuario",

    # Descripción que aparecerá en el comando "ayuda".
    "description": "Muestra el usuario activo.",

    # Categoría.
    "category": "Sistema",

    # Autor.
    "author": "REDACTED_2c7b6821719d",

    # Versión del comando.
    "version": "1.1",

    # Alias disponibles.
    #
    # Todos ejecutarán exactamente este mismo comando.
    "aliases": [

        "quien soy",

        "quién soy",

        "perfil",

    ],

    # Ejemplos de utilización.
    "examples": [

        "usuario",

        "quien soy",

    ],

}


def execute():
    """
    Ejecuta el comando "usuario".

    No recibe parámetros.

    No devuelve ningún valor.

    REDACTED_0f38c2ded26fnamiento:

        Consulta el usuario activo almacenado en Atlas
        y lo muestra por pantalla.

    Al no devolver ningún valor, command_manager interpretará
    automáticamente que Atlas debe continuar funcionando.
    """

    # Línea en blanco para mejorar la presentación.
    print()

    # Mostramos el usuario que está utilizando Atlas
    # en este momento.
    #
    # Ejemplos:
    #
    # Usuario activo: REDACTED_2c7b6821719d
    # Usuario activo: REDACTED_bc04a68d9192
    # Usuario activo: REDACTED_0392c3d1b4d3
    print(

        f"Usuario activo: "

        f"{context.atlas.get_user()}"

    )