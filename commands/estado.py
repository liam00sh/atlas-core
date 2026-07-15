"""
===============================================================================
Proyecto Atlas
Archivo: commands/estado.py

Descripción:
    Implementa el comando "estado".

    Muestra un resumen del estado operativo actual de Atlas:

    - Versión.
    - Usuario activo.
    - Número de recuerdos.
    - Número de comandos.
    - Estado de la inteligencia artificial.
    - Proveedor de IA.
    - Modelo configurado.
    - Disponibilidad de Ollama.
    - Instalación del modelo.
    - Tamaño del contexto temporal.
    - Estado de la voz.
    - Estado de Internet.
    - Plugins.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

# Importamos el módulo completo para acceder siempre a la instancia actual
# de Atlas publicada desde main.py.
#
# No debe utilizarse:
#
#     from core import context
#
# porque durante la carga inicial de los comandos esa variable todavía
# puede valer None.
from core import context


# =============================================================================
# METADATOS DEL COMANDO
# =============================================================================

COMMAND = {
    "name": "estado",
    "description": "Resumen del estado del sistema.",
    "category": "Sistema",
    "author": "Liam",
    "version": "1.1",
    "aliases": [
        "status",
    ],
    "examples": [
        "estado",
    ],
}


def _availability(
    enabled: bool,
    unavailable: str = "No disponible",
) -> str:
    """
    Convierte una capacidad booleana en un texto legible.

    Parámetros:
        enabled:
            Indica si la capacidad está disponible.

        unavailable:
            Texto mostrado cuando no está disponible.

    Devuelve:
        "Disponible" si está activa.

        El texto indicado en unavailable si está inactiva.
    """

    return (
        "Disponible"
        if enabled
        else unavailable
    )


def _connection_state(
    connected: bool,
) -> str:
    """
    Convierte un estado de conexión en texto legible.
    """

    return (
        "Conectado"
        if connected
        else "No conectado"
    )


def _installation_state(
    installed: bool,
) -> str:
    """
    Convierte el estado de instalación de un modelo
    en texto legible.
    """

    return (
        "Instalado"
        if installed
        else "No instalado"
    )


def execute() -> None:
    """
    Muestra de un vistazo el estado actual de Atlas.
    """

    # Recuperamos la instancia actual desde el contexto global.
    atlas = context.atlas

    # Protección adicional por si el comando se ejecutase antes
    # de que main.py publicara la instancia.
    if atlas is None:

        print()

        print(
            "Atlas todavía no está inicializado."
        )

        return

    # =========================================================================
    # INFORMACIÓN GENERAL
    # =========================================================================

    active_user = atlas.get_user()

    memory_count = atlas.memory.count_memories(
        active_user
    )

    # COMMANDS contiene nombres principales y alias.
    #
    # Contamos módulos únicos para no considerar cada alias
    # como un comando diferente.
    command_count = len(
        {
            id(module)
            for module in atlas.get_commands().values()
        }
    )

    # =========================================================================
    # ESTADO DE LA INTELIGENCIA ARTIFICIAL
    # =========================================================================

    ai_enabled = atlas.can_use_ai()

    ai_provider = atlas.ai_provider

    provider_name = "No configurado"
    model_name = "No configurado"

    provider_available = False
    model_installed = False

    ai_warning = False

    # Solo podemos comprobar la conexión cuando existe
    # un proveedor configurado.
    if ai_provider is not None:

        provider_name = (
            ai_provider.get_provider_name()
        )

        model_name = (
            ai_provider.get_model_name()
        )

        try:

            provider_available = (
                ai_provider.is_available()
            )

        except RuntimeError:

            provider_available = False

        # Solo intentamos comprobar el modelo cuando
        # el proveedor está disponible.
        if provider_available:

            try:

                model_installed = (
                    ai_provider.is_model_installed()
                )

            except RuntimeError:

                model_installed = False

    # Detectamos configuraciones incompletas.
    if ai_enabled:

        if ai_provider is None:
            ai_warning = True

        elif not provider_available:
            ai_warning = True

        elif not model_installed:
            ai_warning = True

    # Número de mensajes almacenados en el contexto
    # temporal del usuario activo.
    ai_context_size = (
        atlas.get_ai_context_size()
    )

    # =========================================================================
    # ESTADO GENERAL
    # =========================================================================

    if ai_warning:

        general_status = (
            "Operativo con avisos."
        )

    else:

        general_status = (
            "Todo operativo."
        )

    # =========================================================================
    # SALIDA
    # =========================================================================

    print()

    print(
        f"Atlas {atlas.get_version()}"
    )

    print()

    print(
        f"Usuario activo : {active_user}"
    )

    print(
        f"Memorias       : {memory_count}"
    )

    print(
        f"Comandos       : {command_count}"
    )

    print()

    print(
        "IA             : "
        f"{_availability(ai_enabled, 'Inactiva')}"
    )

    print(
        f"Proveedor      : {provider_name}"
    )

    print(
        f"Modelo         : {model_name}"
    )

    print(
        "Ollama         : "
        f"{_connection_state(provider_available)}"
    )

    print(
        "Modelo local   : "
        f"{_installation_state(model_installed)}"
    )

    print(
        f"Contexto IA    : {ai_context_size} mensajes"
    )

    print()

    print(
        "Voz            : "
        f"{_availability(atlas.can_use_voice())}"
    )

    print(
        "Internet       : "
        + (
            "Activado"
            if atlas.can_access_internet()
            else "Desactivado"
        )
    )

    print(
        "Herramientas   : "
        f"{atlas.get_tool_count()}"
    )

    print(
        "Plugins        : 0"
    )

    print()

    print(
        f"Estado         : {general_status}"
    )