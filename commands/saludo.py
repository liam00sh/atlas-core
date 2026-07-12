"""
===============================================================================
Proyecto Atlas
Archivo: commands/saludo.py

Descripción:
    Implementa el comando "saludo".

    Su función es mostrar un saludo sencillo del asistente.

    Actualmente el saludo está dirigido a Liam de forma fija, ya que fue uno
    de los primeros comandos creados durante el desarrollo de Atlas.

    En futuras versiones este comando utilizará el usuario activo almacenado
    en Atlas para personalizar automáticamente el saludo.

Ejemplo:

    Atlas > saludo

        ¡Hola Liam!
        Soy Daxter 😊

Flujo:

    Usuario
        │
        ▼
     saludo
        │
        ▼
    execute()
        │
        ▼
    Mostrar saludo
===============================================================================
"""


# =============================================================================
# METADATOS DEL COMANDO
# =============================================================================

# Todos los comandos incluyen un diccionario COMMAND.
#
# command_manager.py utiliza esta información para registrar
# automáticamente el comando al iniciar Atlas.
COMMAND = {

    # Nombre principal del comando.
    "name": "saludo",

    # Descripción que aparecerá en el comando "ayuda".
    "description": "Saluda al usuario.",

    # Categoría.
    "category": "General",

    # Autor del comando.
    "author": "Liam",

    # Versión del comando.
    "version": "1.0",

    # Alias aceptados.
    #
    # Todos ejecutarán exactamente este mismo comando.
    "aliases": [

        "hola",

        "saludar",

    ],

    # Ejemplos de uso.
    "examples": [

        "saludo",

        "hola",

    ],

}


def execute():
    """
    Ejecuta el comando "saludo".

    No recibe parámetros.

    No devuelve ningún valor.

    Funcionamiento:

        Muestra un saludo básico del asistente.

    Al no devolver ningún valor, command_manager interpretará
    automáticamente que Atlas debe continuar funcionando.
    """

    # Dejamos una línea en blanco para mejorar la presentación.
    print()

    # Saludo principal.
    #
    # Actualmente el nombre "Liam" está escrito de forma fija.
    #
    # En futuras versiones se obtendrá automáticamente mediante:
    #
    #     atlas.get_user()
    #
    # De esta forma el saludo cambiará según el usuario activo.
    print("¡Hola Liam!")

    # Presentación del asistente.
    print("Soy Daxter 😊")