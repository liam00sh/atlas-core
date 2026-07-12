"""
===============================================================================
Proyecto Atlas
Archivo: core/context.py

Descripción:
    Este archivo actúa como contexto compartido del proyecto.

    Su función es almacenar una referencia a la instancia principal de Atlas
    para que otros módulos puedan acceder al mismo objeto sin tener que
    recibirlo continuamente como parámetro.

Ejemplo de uso:

    from core import context

    context.atlas.get_user()
    context.atlas.change_user("Saray")

Importante:
    La variable atlas empieza con el valor None porque, al importar este
    archivo, todavía no se ha creado la instancia principal de Atlas.

    Más tarde, en main.py, se asigna la instancia real:

        atlas = Atlas()
        context.atlas = atlas

    A partir de ese momento, todos los módulos que importen core.context
    podrán acceder al mismo objeto Atlas.
===============================================================================
"""


# Referencia compartida a la instancia principal de Atlas.
#
# Inicialmente vale None porque Daxter todavía no ha sido creado.
#
# Después, main.py sustituye este valor por la instancia real:
#
#     context.atlas = atlas
#
# Tipo esperado durante la ejecución:
#     Atlas
#
# Valor inicial:
#     None
atlas = None