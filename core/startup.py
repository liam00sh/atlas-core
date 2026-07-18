"""Secuencia visual de arranque de Atlas Core."""


import time


from assistant_identity.phrase_bank import STARTUP
from core.checks.docker import check_docker
from core.checks.folders import check_project_folders
from core.system_info import get_system_info
from core.version import PROJECT_NAME, VERSION




def show_banner(atlas):
    info = get_system_info()
    print("=" * 60)
    print(PROJECT_NAME.center(60))
    print("=" * 60)
    print()
    print(f"Asistente............. {atlas.get_name()}")
    print(f"Versión............... {VERSION}")
    print()
    print(f"Sistema Operativo..... {info['os']} {info['os_version']}")
    print(f"Python................ {info['python']}")
    print()
    print(f"Fecha................. {info['date']}")
    print(f"Hora.................. {info['time']}")
    print()
    print("=" * 60)
    print()




def initialize():
    print("Inicializando Atlas Core...")
    time.sleep(0.5)
    print()
    print("Comprobando estructura del proyecto...")
    time.sleep(0.3)


    for folder, status in check_project_folders().items():
        print(f"{'✓' if status else '✗'} {folder}")
        time.sleep(0.1)


    print()
    print("Comprobando Docker...")
    time.sleep(0.3)
    print("✓ Docker encontrado" if check_docker() else "⚠ Docker no encontrado")
    time.sleep(0.3)
    print()
    print("✓ Configuración cargada")
    time.sleep(0.2)
    print("✓ Logger iniciado")
    time.sleep(0.2)
    print("✓ Sistema preparado")
    time.sleep(0.2)
    print()




def welcome(atlas):
    print("=" * 60)
    print()


    startup_phrase = atlas.identity_manager.get_phrase(
        STARTUP,
        default="Estoy listo.",
        user=atlas.get_user(),
    )


    if atlas.get_name().casefold() == "coco":
        follow_up = "Cuéntame, ¿qué reto ponemos hoy en orden?"
    else:
        follow_up = "Venga, dispara: ¿qué misión tenemos hoy?"


    print(f"{startup_phrase}\n\n{follow_up}")
    print()
    print("=" * 60)




def startup(atlas):
    show_banner(atlas)
    initialize()
    welcome(atlas)