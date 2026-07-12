"""
===============================================================================
Proyecto Atlas
Archivo: core/system_info.py

Descripción:
    Este módulo se encarga de obtener información básica del sistema donde
    se está ejecutando Atlas.

    Actualmente devuelve:

    - Sistema operativo.
    - Versión del sistema operativo.
    - Versión de Python.
    - Fecha actual.
    - Hora actual.

    Esta información se utiliza principalmente durante el proceso de arranque
    para mostrar el banner de bienvenida.

    En futuras versiones este módulo podrá ampliarse para obtener:

    - Procesador (CPU).
    - Memoria RAM.
    - Tarjeta gráfica (GPU).
    - Temperatura del sistema.
    - Espacio libre en disco.
    - Tiempo de funcionamiento (Uptime).
===============================================================================
"""

# =============================================================================
# IMPORTACIONES
# =============================================================================

# El módulo "platform" permite obtener información del sistema operativo
# donde se está ejecutando Python.
#
# Ejemplos:
#
# Windows
# Linux
# macOS
#
# También permite conocer la versión del sistema y de Python.
import platform

# Importamos la clase datetime para obtener la fecha
# y la hora actuales del sistema.
from datetime import datetime


def get_system_info():
    """
    Obtiene información básica del sistema.

    No recibe parámetros.

    Devuelve:
        dict

    Ejemplo del diccionario devuelto:

        {
            "os": "Windows",
            "os_version": "11",
            "python": "3.14.6",
            "date": "11/07/2026",
            "time": "18:42:15"
        }

    Esta función no muestra información por pantalla.
    Simplemente devuelve los datos para que otros módulos
    puedan utilizarlos.
    """

    return {

        # ---------------------------------------------------------------------
        # Nombre del sistema operativo.
        #
        # platform.system() puede devolver:
        #
        # Windows
        # Linux
        # Darwin (macOS)
        # ---------------------------------------------------------------------
        "os": platform.system(),

        # ---------------------------------------------------------------------
        # Versión o edición del sistema operativo.
        #
        # Ejemplos:
        #
        # Windows -> "11"
        # Linux -> versión del Kernel
        # ---------------------------------------------------------------------
        "os_version": platform.release(),

        # ---------------------------------------------------------------------
        # Devuelve la versión del intérprete de Python.
        #
        # Ejemplo:
        #
        # 3.14.6
        # ---------------------------------------------------------------------
        "python": platform.python_version(),

        # ---------------------------------------------------------------------
        # Fecha actual.
        #
        # datetime.now() obtiene la fecha y hora actuales.
        #
        # strftime() convierte esa información en texto.
        #
        # "%d/%m/%Y"
        #
        # Significa:
        #
        # %d -> día
        # %m -> mes
        # %Y -> año completo
        #
        # Ejemplo:
        #
        # 11/07/2026
        # ---------------------------------------------------------------------
        "date": datetime.now().strftime(
            "%d/%m/%Y"
        ),

        # ---------------------------------------------------------------------
        # Hora actual.
        #
        # "%H:%M:%S"
        #
        # Significa:
        #
        # %H -> hora (24 horas)
        # %M -> minutos
        # %S -> segundos
        #
        # Ejemplo:
        #
        # 18:42:15
        # ---------------------------------------------------------------------
        "time": datetime.now().strftime(
            "%H:%M:%S"
        ),
    }