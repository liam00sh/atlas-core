"""
===============================================================================
Proyecto Atlas
Archivo: core/startup.py

Descripción:
    Este archivo controla la secuencia de arranque visual de Atlas.

    Sus responsabilidades principales son:

    1. Mostrar el banner con información del proyecto.
    2. Comprobar la estructura de carpetas.
    3. Comprobar si Docker está disponible.
    4. Mostrar mensajes de inicialización.
    5. Saludar al usuario activo con la identidad seleccionada.

Flujo de ejecución:

    startup(atlas)
        │
        ├── show_banner()
        ├── initialize()
        └── welcome(atlas)

Este archivo no contiene la lógica principal del asistente.
Solo prepara y presenta el entorno antes de abrir la consola interactiva.
===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

# Importamos el módulo time para poder introducir pequeñas pausas
# durante el arranque.
#
# Estas pausas hacen que la inicialización parezca más natural
# y permiten leer mejor los mensajes que aparecen en pantalla.
import time


# Importamos la función que genera el saludo inicial del asistente.
#
# El saludo puede variar según la personalidad configurada
# y el usuario que esté activo.
from conversation.personality import initial_welcome


# Importamos la función que comprueba si Docker está disponible
# en el sistema operativo.
from core.checks.docker import check_docker

# Importamos la función que comprueba si existen las carpetas
# principales del proyecto.
from core.checks.folders import check_project_folders

# Importamos la función que obtiene información del equipo:
#
# - Sistema operativo.
# - Versión del sistema.
# - Versión de Python.
# - Fecha.
# - Hora.
from core.system_info import get_system_info

# Importamos las constantes generales del proyecto.
from core.version import PROJECT_NAME
from core.version import VERSION


def show_banner(atlas):
    """
    Muestra la cabecera principal del Proyecto Atlas.

    La información mostrada incluye:

    - Nombre del proyecto.
    - Nombre del asistente.
    - Versión de Atlas.
    - Sistema operativo.
    - Versión de Python.
    - Fecha y hora actuales.

    Parámetros:
        atlas:
            Instancia principal utilizada para consultar la identidad
            activa del asistente.
    """

    # Obtenemos un diccionario con la información del sistema.
    #
    # Ejemplo:
    #
    # {
    #     "os": "Windows",
    #     "os_version": "11",
    #     "python": "3.14.6",
    #     "date": "11/07/2026",
    #     "time": "20:30:15"
    # }
    info = get_system_info()

    # Imprime una línea de 60 signos "=".
    print("=" * 60)

    # Centra el nombre del proyecto dentro de un ancho de 60 caracteres.
    print(PROJECT_NAME.center(60))

    # Cierra visualmente la cabecera superior.
    print("=" * 60)

    # Línea en blanco para separar bloques.
    print()

    # Muestra el nombre del asistente.
    print(f"Asistente............. {atlas.get_name()}")

    # Muestra la versión actual del proyecto.
    print(f"Versión............... {VERSION}")

    print()

    # Muestra el sistema operativo y su versión.
    print(
        f"Sistema Operativo..... "
        f"{info['os']} {info['os_version']}"
    )

    # Muestra la versión de Python utilizada.
    print(f"Python................ {info['python']}")

    print()

    # Muestra la fecha actual.
    print(f"Fecha................. {info['date']}")

    # Muestra la hora actual.
    print(f"Hora.................. {info['time']}")

    print()

    # Línea inferior del banner.
    print("=" * 60)

    print()


def initialize():
    """
    Ejecuta las comprobaciones iniciales de Atlas.

    Actualmente comprueba:

    - Que existan las carpetas principales del proyecto.
    - Que Docker esté disponible.
    - Que la configuración, el logger y el sistema estén preparados.

    Las pausas con time.sleep() son únicamente visuales.
    No son necesarias para el funcionamiento interno.
    """

    # Mensaje de inicio del proceso de inicialización.
    print("Inicializando Atlas Core...")

    # Pausa de medio segundo.
    time.sleep(0.5)

    print()

    # Informa de que se comprobará la estructura de carpetas.
    print("Comprobando estructura del proyecto...")

    time.sleep(0.3)

    # Obtiene un diccionario con el estado de las carpetas.
    #
    # Ejemplo:
    #
    # {
    #     "ai": True,
    #     "memory": True,
    #     "automation": False
    # }
    folders = check_project_folders()

    # Recorremos cada carpeta y su estado.
    #
    # folder:
    #     Nombre de la carpeta.
    #
    # status:
    #     True si existe.
    #     False si no existe.
    for folder, status in folders.items():

        # Si la carpeta existe, mostramos un símbolo correcto.
        if status:
            print(f"✓ {folder}")

        # Si no existe, mostramos un símbolo de error.
        else:
            print(f"✗ {folder}")

        # Pequeña pausa entre cada resultado.
        time.sleep(0.1)

    print()

    # Informa de que se comprobará Docker.
    print("Comprobando Docker...")

    time.sleep(0.3)

    # check_docker() devuelve True si encuentra Docker.
    if check_docker():
        print("✓ Docker encontrado")

    # Si devuelve False, Docker no está instalado
    # o no está disponible en la variable PATH.
    else:
        print("⚠ Docker no encontrado")

    time.sleep(0.3)

    print()

    # Estos tres mensajes representan servicios internos preparados.
    #
    # Actualmente son mensajes informativos.
    # Más adelante podrán corresponder a comprobaciones reales.
    print("✓ Configuración cargada")

    time.sleep(0.2)

    print("✓ Logger iniciado")

    time.sleep(0.2)

    print("✓ Sistema preparado")

    time.sleep(0.2)

    print()


def welcome(atlas):
    """
    Muestra el saludo inicial de la identidad activa.

    Parámetros:
        atlas:
            Instancia principal de la clase Atlas.

    Se utiliza la instancia para obtener:

    - El usuario activo.
    - El nombre del asistente.

    La frase se genera mediante el sistema de personalidad.
    """

    # Línea superior de separación.
    print("=" * 60)

    print()

    # Generamos y mostramos el saludo inicial.
    #
    # Ejemplo:
    #
    # Hola Liam.
    #
    # Soy Daxter.
    #
    # ¡A darle caña!
    #
    # ¿Qué hacemos hoy?
    print(
        initial_welcome(
            user=atlas.get_user(),
            assistant_name=atlas.get_name(),
        )
    )

    print()

    # Línea inferior de separación.
    print("=" * 60)


def startup(atlas):
    """
    Ejecuta la secuencia completa de arranque.

    Parámetros:
        atlas:
            Instancia principal del núcleo de Atlas.

    Orden de ejecución:

        1. Mostrar el banner.
        2. Realizar comprobaciones.
        3. Mostrar el saludo personalizado.
    """

    # Muestra la información general del proyecto y del sistema.
    show_banner(atlas)

    # Ejecuta las comprobaciones de arranque.
    initialize()

    # Saluda al usuario activo.
    welcome(atlas)