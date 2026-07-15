"""
===============================================================================
Proyecto Atlas
Archivo: main.py

Punto de entrada de Atlas Core.

Este módulo:

- Consulta el modelo predeterminado registrado.
- Crea el proveedor local de Ollama.
- Crea una única instancia de Atlas.
- Publica esa instancia en el contexto global.
- Ejecuta la secuencia de inicio.
- Abre la consola interactiva.

La creación del proveedor se realiza fuera de la clase Atlas para mantener
el núcleo desacoplado de Ollama.

===============================================================================
"""


# =============================================================================
# INTELIGENCIA ARTIFICIAL
# =============================================================================

# Registro que contiene los modelos conocidos por Atlas.
from ai.models.model_registry import ModelRegistry

# Proveedor que permite comunicarse con la instalación local de Ollama.
from ai.providers.ollama_provider import OllamaProvider


# =============================================================================
# CONSOLA
# =============================================================================

# Inicia la consola interactiva.
from console.shell import start_shell


# =============================================================================
# NÚCLEO
# =============================================================================

# Contexto global utilizado por los comandos y otros módulos.
from core import context

# Clase principal del Proyecto Atlas.
from core.atlas import Atlas

# Ejecuta la secuencia visual y técnica de inicio.
from core.startup import startup


def main() -> None:
    """
    Inicia Atlas y mantiene activa su consola interactiva.

    Flujo:

        1. Se consulta el modelo predeterminado.
        2. Se crea el proveedor de Ollama.
        3. Se crea una única instancia de Atlas.
        4. Se publica la instancia en core.context.
        5. Se ejecuta la secuencia de inicio.
        6. Se abre la consola interactiva.
    """

    # -------------------------------------------------------------------------
    # REGISTRO DE MODELOS
    # -------------------------------------------------------------------------

    # Crea el registro de modelos conocidos por Atlas.
    model_registry = ModelRegistry()

    # Obtiene el nombre del modelo configurado como predeterminado.
    #
    # Actualmente:
    #
    #     qwen2.5:7b
    default_model = (
        model_registry.get_default_model_name()
    )

    # -------------------------------------------------------------------------
    # PROVEEDOR DE INTELIGENCIA ARTIFICIAL
    # -------------------------------------------------------------------------

    # Crea el proveedor encargado de comunicarse con Ollama.
    #
    # El proveedor todavía no ejecuta ninguna consulta durante
    # la creación. Solo conserva la configuración necesaria.
    ai_provider = OllamaProvider(
        model_name=default_model,
        timeout=180,
    )

    # -------------------------------------------------------------------------
    # INSTANCIA PRINCIPAL DE ATLAS
    # -------------------------------------------------------------------------

    # Se crea una única instancia del núcleo para toda la aplicación.
    #
    # El proveedor se inyecta desde fuera para evitar que core/atlas.py
    # dependa directamente de Ollama.
    atlas = Atlas(
        ai_provider=ai_provider
    )

    # -------------------------------------------------------------------------
    # CONTEXTO GLOBAL
    # -------------------------------------------------------------------------

    # Los comandos y otros módulos pueden consultar esta instancia
    # mediante core.context.
    context.atlas = atlas

    # -------------------------------------------------------------------------
    # INICIALIZACIÓN
    # -------------------------------------------------------------------------

    # Prepara el entorno y muestra la información de inicio.
    startup(
        atlas
    )

    # -------------------------------------------------------------------------
    # CONSOLA
    # -------------------------------------------------------------------------

    # Mantiene Atlas esperando órdenes hasta que el usuario decide salir.
    start_shell(
        atlas
    )


if __name__ == "__main__":
    main()