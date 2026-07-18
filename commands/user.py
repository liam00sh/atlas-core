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

    - Usuario principal (Liam)
    - Usuarios temporales (Saray, Lidia, etc.)

Ejemplo:

    Atlas > usuario

        Usuario activo: Liam

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
from conversation.personality import current_user_identity
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
    "author": "Liam",

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

    Funcionamiento:

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
    # Usuario activo: Liam
    # Usuario activo: Saray
    # Usuario activo: Lidia
    print(
        current_user_identity(
            user=context.atlas.get_user(),
            assistant_name=context.atlas.get_name(),
        )
    )