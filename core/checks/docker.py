"""
===============================================================================
Proyecto Atlas
Archivo: core/checks/docker.py

Descripción:
    Este módulo comprueba si Docker está instalado y disponible en el sistema.

    Se utiliza durante el arranque de Atlas para informar al usuario de si
    Docker puede utilizarse.

    Actualmente solo verifica que el ejecutable "docker" pueda encontrarse
    mediante la variable de entorno PATH.

Importante:
    Esta comprobación NO verifica que Docker esté funcionando.

    Puede ocurrir que:

        ✔ Docker esté instalado.
        ✖ El servicio de Docker esté detenido.

    En ese caso esta función seguirá devolviendo True.

    En futuras versiones podrá ampliarse para comprobar:

    - Que Docker Desktop esté iniciado.
    - Que el daemon responda correctamente.
    - La versión instalada.
    - Los contenedores disponibles.
===============================================================================
"""

# =============================================================================
# IMPORTACIONES
# =============================================================================

# shutil contiene diversas utilidades relacionadas con archivos,
# carpetas y programas del sistema.
#
# En este caso utilizaremos la función "which()",
# que permite localizar un programa instalado en el ordenador.
import shutil


def check_docker():
    """
    Comprueba si Docker está disponible en el sistema.

    No recibe parámetros.

    Devuelve:
        True
            Si encuentra el ejecutable "docker".

        False
            Si no puede localizarlo.

    Funcionamiento:

        shutil.which("docker")

    busca el programa "docker" dentro de las carpetas
    incluidas en la variable PATH del sistema operativo.

    Ejemplos:

        Windows:
            C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe

        Linux:
            /usr/bin/docker

    Si no encuentra el ejecutable devuelve None.
    """

    # -------------------------------------------------------------------------
    # shutil.which()
    #
    # Busca un programa utilizando el PATH del sistema.
    #
    # Puede devolver:
    #
    # "C:\\Program Files\\Docker\\..."
    #
    # o
    #
    # None
    #
    # Nosotros únicamente queremos saber si existe,
    # por eso comprobamos:
    #
    # is not None
    #
    # El resultado final será un valor booleano:
    #
    # True
    # False
    # -------------------------------------------------------------------------
    return shutil.which("docker") is not None