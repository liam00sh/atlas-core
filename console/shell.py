"""
===============================================================================
Proyecto Atlas
Archivo: console/shell.py

Descripción:
    Implementa la consola interactiva de Atlas.

    La consola recibe las entradas del usuario y las envía
    al núcleo mediante Atlas.process().

    El valor devuelto por Atlas.process() determina si la consola
    debe continuar funcionando o finalizar.
===============================================================================
"""


def start_shell(atlas) -> None:
    """
    Inicia el bucle principal de la consola.

    Atlas.process() devuelve:

        True:
            La consola continúa funcionando.

        False:
            La consola finaliza.
    """

    running = True

    while running:

        try:

            command = input(
                "\nAtlas > "
            )

            # Es fundamental guardar el resultado.
            #
            # El comando "salir" devuelve False cuando
            # está activo el usuario principal.
            running = atlas.process(
                command
            )

        except KeyboardInterrupt:

            print()
            print()
            print(
                "Atlas se ha cerrado manualmente."
            )

            running = False
