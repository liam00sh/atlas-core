"""
===============================================================================
Proyecto Atlas
Archivo: main.py

Punto de entrada de Atlas Core.

Este módulo crea una única instancia de Atlas, la publica en el contexto global,
ejecuta la secuencia de inicio y abre la consola interactiva.
===============================================================================
"""

from console.shell import start_shell
from core import context
from core.atlas import Atlas
from core.startup import startup


def main() -> None:
    """Inicia Atlas y mantiene activa su consola interactiva."""

    # Se crea una única instancia del núcleo para toda la aplicación.
    atlas = Atlas()

    # Los comandos pueden consultar esta instancia mediante core.context.
    context.atlas = atlas

    # Prepara el entorno y muestra la información de inicio.
    startup(atlas)

    # Mantiene Atlas esperando órdenes hasta que el usuario decide salir.
    start_shell(atlas)


if __name__ == "__main__":
    main()
