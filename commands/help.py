"""
===============================================================================
Proyecto Atlas
Archivo: commands/help.py

Descripción:
    Implementa el comando "ayuda".

    Su función es mostrar un listado con todos los comandos disponibles
    registrados en Atlas junto con una breve descripción.

    El listado se genera automáticamente a partir del registro de comandos
    creado por command_manager.py.

    Esto significa que, al crear un nuevo comando dentro de la carpeta
    commands/, aparecerá automáticamente en la ayuda sin modificar este
    archivo.

Ejemplo:

    Atlas > ayuda

        fecha          Muestra la fecha y la hora actuales.
        salir          Finaliza Atlas o cierra el perfil temporal.
        version        Muestra la versión instalada de Atlas.

Flujo:

    Usuario
        │
        ▼
      ayuda
        │
        ▼
command_manager.py
        │
        ▼
Diccionario COMMANDS
        │
        ▼
Recorrer comandos
        │
        ▼
Mostrar listado
===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

# Importamos el diccionario global donde command_manager registra
# automáticamente todos los comandos disponibles.
#
# Ejemplo:
#
# COMMANDS = {
#     "fecha": commands.fecha,
#     "hora": commands.fecha,
#     "salir": commands.exit,
#     "help": commands.help,
# }
from console.command_manager import COMMANDS


# =============================================================================
# METADATOS DEL COMANDO
# =============================================================================

COMMAND = {

    # Nombre principal.
    "name": "ayuda",

    # Descripción mostrada al usuario.
    "description": "Muestra todos los comandos disponibles.",

    # Categoría.
    "category": "Sistema",

    # Autor.
    "author": "Liam",

    # Versión del comando.
    "version": "1.0",

    # Alias aceptados.
    "aliases": [

        "help",

        "?",

    ],

    # Ejemplos.
    "examples": [

        "ayuda",

    ],

}


def execute():
    """
    Ejecuta el comando "ayuda".

    No recibe parámetros.

    No devuelve ningún valor.

    Funcionamiento:

        1. Obtiene todos los comandos registrados.
        2. Los ordena alfabéticamente.
        3. Elimina duplicados producidos por los alias.
        4. Muestra el nombre y la descripción de cada uno.

    Al no devolver ningún valor,
    command_manager interpretará automáticamente
    que Atlas debe continuar funcionando.
    """

    # Línea en blanco para mejorar la presentación.
    print()

    # Título del listado.
    print("Comandos disponibles:\n")

    # -------------------------------------------------------------------------
    # Conjunto donde almacenaremos los comandos ya mostrados.
    #
    # ¿Por qué es necesario?
    #
    # Porque COMMANDS contiene tanto los nombres principales
    # como los alias.
    #
    # Ejemplo:
    #
    # "fecha"
    # "hora"
    # "time"
    #
    # Todos apuntan al mismo módulo.
    #
    # Sin este conjunto aparecerían varias veces.
    # -------------------------------------------------------------------------
    mostrados = set()

    # -------------------------------------------------------------------------
    # Recorremos todos los módulos registrados.
    #
    # sorted() los ordena alfabéticamente utilizando
    # el nombre principal del comando.
    #
    # key=lambda...
    #
    # indica que el criterio de ordenación será:
    #
    # command.COMMAND["name"]
    # -------------------------------------------------------------------------
    for command in sorted(

        COMMANDS.values(),

        key=lambda c: c.COMMAND["name"]

    ):

        # Si ese comando ya ha sido mostrado,
        # lo ignoramos.
        if command.COMMAND["name"] in mostrados:
            continue

        # Marcamos el comando como mostrado.
        mostrados.add(

            command.COMMAND["name"]

        )

        # Mostramos:
        #
        # Nombre del comando.
        # Descripción.
        #
        # El especificador:
        #
        # <15
        #
        # significa:
        #
        # "Reserva 15 caracteres alineando el texto
        # hacia la izquierda."
        #
        # Gracias a ello todas las descripciones
        # comienzan en la misma columna.
        print(

            f'{command.COMMAND["name"]:<15}'

            f'{command.COMMAND["description"]}'

        )