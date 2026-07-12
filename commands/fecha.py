"""
===============================================================================
Proyecto Atlas
Archivo: commands/fecha.py

Descripción:
    Implementa el comando "fecha".

    Su función es mostrar la fecha y la hora actuales del sistema.

    Este comando utiliza el reloj del sistema operativo, por lo que siempre
    mostrará la fecha y hora reales del equipo donde se esté ejecutando Atlas.

Ejemplos:

    Atlas > fecha

        Fecha: 11/07/2026
        Hora : 19:42:18

    Atlas > hora

        Fecha: 11/07/2026
        Hora : 19:42:18

Flujo:

    Usuario
        │
        ▼
    "fecha"
        │
        ▼
    command_manager
        │
        ▼
    execute()
        │
        ▼
    datetime.now()
        │
        ▼
    Mostrar fecha y hora
===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

# Importamos la clase datetime para obtener la fecha
# y la hora actuales del sistema.
from datetime import datetime


# =============================================================================
# METADATOS DEL COMANDO
# =============================================================================

# Todos los comandos de Atlas incluyen un diccionario COMMAND.
#
# command_manager.py utiliza esta información para registrar
# automáticamente el comando al iniciar Atlas.
COMMAND = {

    # Nombre principal del comando.
    "name": "fecha",

    # Breve descripción que aparecerá en futuras ayudas.
    "description": "Muestra la fecha y la hora actuales.",

    # Categoría del comando.
    "category": "Sistema",

    # Autor del comando.
    "author": "Liam",

    # Versión del propio comando.
    "version": "1.0",

    # Alias aceptados.
    #
    # Cualquiera de estos textos ejecutará exactamente
    # este mismo comando.
    "aliases": [

        "hora",

        "time",

    ],

    # Ejemplos de utilización.
    "examples": [

        "fecha",

        "hora",

    ],

}


def execute():
    """
    Ejecuta el comando "fecha".

    No recibe parámetros.

    No devuelve ningún valor.

    Funcionamiento:

        1. Obtiene la fecha y hora actuales.
        2. Las formatea como texto.
        3. Las muestra por pantalla.

    Al no devolver ningún valor, command_manager interpretará
    automáticamente que Atlas debe continuar funcionando.
    """

    # -------------------------------------------------------------------------
    # Obtenemos la fecha y hora actuales.
    #
    # Ejemplo:
    #
    # 2026-07-11 19:42:18.615432
    # -------------------------------------------------------------------------
    ahora = datetime.now()

    # Dejamos una línea en blanco para mejorar la presentación.
    print()

    # -------------------------------------------------------------------------
    # Mostramos la fecha.
    #
    # strftime() convierte la fecha en texto.
    #
    # "%d/%m/%Y"
    #
    # %d -> día
    # %m -> mes
    # %Y -> año completo
    #
    # Ejemplo:
    #
    # 11/07/2026
    # -------------------------------------------------------------------------
    print(
        "Fecha:",
        ahora.strftime("%d/%m/%Y"),
    )

    # -------------------------------------------------------------------------
    # Mostramos la hora.
    #
    # "%H:%M:%S"
    #
    # %H -> hora (24 horas)
    # %M -> minutos
    # %S -> segundos
    #
    # Ejemplo:
    #
    # 19:42:18
    # -------------------------------------------------------------------------
    print(
        "Hora :",
        ahora.strftime("%H:%M:%S"),
    )