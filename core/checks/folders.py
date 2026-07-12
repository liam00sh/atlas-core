"""
===============================================================================
Proyecto Atlas
Archivo: core/checks/folders.py

Descripción:
    Este módulo comprueba que existan las carpetas principales del proyecto.

    Se utiliza durante el arranque de Atlas para verificar que la estructura
    del proyecto es correcta antes de comenzar a trabajar.

    Actualmente comprueba la existencia de:

    - ai/
    - memory/
    - automation/
    - api/
    - utils/
    - tests/

    El resultado se devuelve como un diccionario indicando si cada carpeta
    existe o no.

Ejemplo:

    {
        "ai": True,
        "memory": True,
        "automation": True,
        "api": True,
        "utils": True,
        "tests": True,
    }

Importante:
    Este módulo únicamente comprueba que las carpetas existan.
    No comprueba su contenido.
===============================================================================
"""

# =============================================================================
# IMPORTACIONES
# =============================================================================

# pathlib es la forma moderna y recomendada de trabajar con rutas en Python.
#
# Permite construir rutas de forma segura tanto en:
#
# Windows
# Linux
# macOS
#
# sin preocuparnos de usar "\" o "/".
from pathlib import Path


def check_project_folders():
    """
    Comprueba que existan las carpetas principales del proyecto.

    No recibe parámetros.

    Devuelve:
        dict

    Ejemplo:

        {
            "memory": True,
            "tests": False,
        }

    True  -> La carpeta existe.

    False -> La carpeta no existe.
    """

    # -------------------------------------------------------------------------
    # Lista de carpetas que deben existir dentro del proyecto.
    #
    # Si en el futuro se añaden nuevas carpetas importantes,
    # bastará con añadirlas aquí.
    # -------------------------------------------------------------------------
    folders = [

        "ai",

        "memory",

        "automation",

        "api",

        "utils",

        "tests",

    ]

    # Diccionario donde iremos almacenando el resultado final.
    #
    # Ejemplo:
    #
    # {
    #     "memory": True,
    #     "tests": False
    # }
    result = {}

    # -------------------------------------------------------------------------
    # Obtener la carpeta raíz del proyecto.
    #
    # __file__
    #     Ruta del archivo actual.
    #
    # resolve()
    #     Convierte la ruta en absoluta.
    #
    # parent
    #     Sube un nivel de carpeta.
    #
    # En este caso:
    #
    # folders.py
    #      ↓
    # checks
    #      ↓
    # core
    #      ↓
    # atlas_core  ← carpeta raíz
    # -------------------------------------------------------------------------
    base = Path(__file__).resolve().parent.parent.parent

    # -------------------------------------------------------------------------
    # Recorremos una por una todas las carpetas que queremos comprobar.
    # -------------------------------------------------------------------------
    for folder in folders:

        # Construimos la ruta completa.
        #
        # Ejemplo:
        #
        # atlas_core / memory
        #
        # pathlib utiliza "/" para unir rutas de forma segura,
        # independientemente del sistema operativo.
        path = base / folder

        # exists() devuelve:
        #
        # True  -> existe
        #
        # False -> no existe
        result[folder] = path.exists()

    # Devolvemos el diccionario con todos los resultados.
    return result