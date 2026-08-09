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
from ai.models.roles import ModelRole, ModelRoleRegistry
from ai.routing.runtime import AIModelRuntime

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


def build_atlas() -> Atlas:
    """
    Construye y publica una única instancia de Atlas.
    """

    model_registry = ModelRegistry()
    default_model = model_registry.get_default_model_name()

    role_registry = ModelRoleRegistry()
    # Se crean objetos ligeros; Ollama carga cada modelo únicamente al usarlo.
    deep_definition = role_registry.resolve(ModelRole.DEEP)
    reasoning_definition = role_registry.resolve(ModelRole.REASONING)
    deep_provider = OllamaProvider(model_name=str(deep_definition.model), timeout=900)
    reasoning_provider = OllamaProvider(model_name=str(reasoning_definition.model), timeout=240)

    ai_provider = OllamaProvider(
        model_name=default_model,
        timeout=180,
    )

    atlas = Atlas(
        ai_provider=ai_provider
    )
    atlas.ai_runtime = AIModelRuntime(
        providers={
            ModelRole.FAST: ai_provider,
            ModelRole.REASONING: reasoning_provider,
            ModelRole.DEEP: deep_provider,
        },
        registry=role_registry,
    )
    atlas.model_role_registry = role_registry

    context.atlas = atlas
    return atlas


def main_background() -> None:
    """
    Inicia el núcleo de Atlas sin abrir la consola interactiva.

    Este modo está pensado para ejecutarse con pythonw.exe o desde
    atlas_launcher.py.
    """

    import signal
    import threading

    atlas = build_atlas()

    # En segundo plano evitamos la secuencia visual de inicio.
    # Los servicios permanentes y las interfaces remotas son gestionados
    # por atlas_launcher.py.
    stop_event = threading.Event()

    def _stop(*_args) -> None:
        stop_event.set()

    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, _stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _stop)

    while not stop_event.wait(1.0):
        pass


def main() -> None:
    """
    Inicia Atlas con consola interactiva.
    """

    atlas = build_atlas()

    startup(
        atlas
    )

    start_shell(
        atlas
    )


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Proyecto Atlas",
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="Ejecuta Atlas sin abrir la consola interactiva.",
    )
    args = parser.parse_args()

    if args.background:
        main_background()
    else:
        main()


if __name__ == "__main__":
    cli()
