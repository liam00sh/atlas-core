"""
===============================================================================
Proyecto Atlas
Archivo: core/system_info.py

Descripción:
    Obtiene información básica y actual del sistema donde se ejecuta Atlas.

    Actualmente devuelve:

    - Sistema operativo.
    - Versión del sistema operativo.
    - Versión de Python.
    - Fecha actual.
    - Hora actual.
    - Día de la semana.

    Además proporciona funciones específicas para consultar:

    - Procesador.
    - Memoria RAM.
    - Discos.
    - Red.
    - Tiempo de funcionamiento.

    Esta información se utiliza:

    - Durante el arranque de Atlas.
    - Para proporcionar datos reales al modelo de IA.
    - Para las herramientas del sistema.
    - Para evitar que el modelo invente información.

===============================================================================
"""

# =============================================================================
# IMPORTACIONES
# =============================================================================

import platform
import csv
import io
import subprocess
import socket

import os

import psutil

from datetime import datetime


# =============================================================================
# CONSTANTES
# =============================================================================

WEEKDAYS = {

    0: "lunes",

    1: "martes",

    2: "miércoles",

    3: "jueves",

    4: "viernes",

    5: "sábado",

    6: "domingo",

}


# =============================================================================
# INFORMACIÓN GENERAL
# =============================================================================

def get_system_info() -> dict[str, str]:
    """
    Obtiene información básica y actual del sistema.
    """

    now = datetime.now()

    return {

        "os": platform.system(),

        "os_version": platform.release(),

        "python": platform.python_version(),

        "date": now.strftime(
            "%d/%m/%Y"
        ),

        "time": now.strftime(
            "%H:%M:%S"
        ),

        "weekday": WEEKDAYS[
            now.weekday()
        ],

    }


def format_system_info_for_ai(
    system_info: dict[str, str],
) -> str:
    """
    Convierte la información del sistema en un texto legible
    para el modelo de IA.
    """

    return "\n".join(

        [

            (
                "Fecha actual: "
                f"{system_info.get('date', 'No disponible')}"
            ),

            (
                "Día de la semana: "
                f"{system_info.get('weekday', 'No disponible')}"
            ),

            (
                "Hora actual: "
                f"{system_info.get('time', 'No disponible')}"
            ),

            (
                "Sistema operativo: "
                f"{system_info.get('os', 'No disponible')} "
                f"{system_info.get('os_version', '')}"
            ),

            (
                "Versión de Python: "
                f"{system_info.get('python', 'No disponible')}"
            ),

        ]

    )


# =============================================================================
# CPU
# =============================================================================

def get_cpu_info() -> dict[str, object]:
    """
    Devuelve información real y actual del procesador.

    Actualmente obtiene:

    - Modelo del procesador.
    - Arquitectura.
    - Tipo de sistema, por ejemplo 64 bits.
    - Número de núcleos físicos.
    - Número de procesadores lógicos.
    - Frecuencia actual.
    - Frecuencia mínima y máxima.
    - Porcentaje de utilización actual.

    La información procede directamente del sistema
    mediante platform y psutil.
    """

    # En Windows, PROCESSOR_IDENTIFIER suele proporcionar
    # un nombre más completo que platform.processor().
    processor_name = (
        platform.processor()
        or os.environ.get(
            "PROCESSOR_IDENTIFIER",
            "",
        )
        or platform.uname().processor
        or "No disponible"
    )

    physical_cores = psutil.cpu_count(
        logical=False
    )

    logical_cores = psutil.cpu_count(
        logical=True
    )

    frequency = psutil.cpu_freq()

    if frequency is None:

        current_frequency_mhz = None
        minimum_frequency_mhz = None
        maximum_frequency_mhz = None

    else:

        current_frequency_mhz = round(
            frequency.current,
            2,
        )

        minimum_frequency_mhz = round(
            frequency.min,
            2,
        )

        maximum_frequency_mhz = round(
            frequency.max,
            2,
        )

    # interval=0.2 toma una muestra breve para evitar
    # que el primer resultado sea siempre 0.
    usage_percent = psutil.cpu_percent(
        interval=0.2
    )

    return {
        "processor": processor_name,
        "architecture": platform.machine(),
        "system_bits": platform.architecture()[0],
        "physical_cores": physical_cores,
        "logical_cores": logical_cores,
        "current_frequency_mhz": current_frequency_mhz,
        "minimum_frequency_mhz": minimum_frequency_mhz,
        "maximum_frequency_mhz": maximum_frequency_mhz,
        "usage_percent": usage_percent,
    }


# =============================================================================
# MEMORIA RAM
# =============================================================================

def get_ram_info() -> dict[str, int | float]:
    """
    Devuelve información actual de la memoria RAM.

    Los valores en bytes proceden directamente del sistema.

    Devuelve:
        dict:
            Información sobre:

            - Memoria total.
            - Memoria disponible.
            - Memoria utilizada.
            - Porcentaje de uso.
    """

    memory = psutil.virtual_memory()

    return {
        "total_bytes": memory.total,
        "available_bytes": memory.available,
        "used_bytes": memory.used,
        "usage_percent": memory.percent,
    }

def bytes_to_gigabytes(
    value: int,
) -> float:
    """
    Convierte una cantidad de bytes a gigabytes.

    Utiliza unidades binarias:

        1 GiB = 1024³ bytes
    """

    return round(
        value / (1024 ** 3),
        2,
    )

def megabytes_to_gigabytes(
    value: int,
) -> float:
    """
    Convierte megabytes a gigabytes.

    Se utiliza principalmente para mostrar
    la memoria de vídeo de las GPU.
    """

    return round(
        value / 1024,
        2,
    )


# =============================================================================
# DISCOS
# =============================================================================

def get_disk_info() -> dict[str, list[dict]]:
    """
    Devuelve información actual de las unidades de almacenamiento.

    Para cada unidad accesible obtiene:

    - Dispositivo.
    - Punto de montaje.
    - Sistema de archivos.
    - Capacidad total.
    - Espacio utilizado.
    - Espacio disponible.
    - Porcentaje de utilización.

    Las unidades inaccesibles o vacías se omiten para evitar
    que un error puntual interrumpa la consulta completa.
    """

    partitions = []
    processed_mountpoints = set()

    for partition in psutil.disk_partitions(
        all=False
    ):

        mountpoint = partition.mountpoint

        # Evitamos registrar dos veces el mismo punto de montaje.
        if mountpoint in processed_mountpoints:
            continue

        processed_mountpoints.add(
            mountpoint
        )

        # Omitimos unidades ópticas vacías.
        if "cdrom" in partition.opts.lower():
            continue

        try:

            usage = psutil.disk_usage(
                mountpoint
            )

        except (
            PermissionError,
            FileNotFoundError,
            OSError,
        ):
            continue

        partitions.append(
            {
                "device": partition.device,
                "mountpoint": mountpoint,
                "filesystem": partition.fstype,
                "options": partition.opts,
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "usage_percent": usage.percent,
            }
        )

    return {
        "partitions": partitions,
    }


# =============================================================================
# RED
# =============================================================================

def get_network_info() -> dict[str, object]:
    """
    Devuelve información actual de la red local.

    Actualmente obtiene:

    - Nombre del equipo.
    - Nombre completo del host.
    - Interfaces de red.
    - Estado de cada interfaz.
    - Velocidad del adaptador.
    - Direcciones IPv4.
    - Direcciones IPv6.
    - Direcciones MAC.
    - Máscaras de red.

    Esta función consulta únicamente información local.

    No comprueba:

    - La IP pública.
    - La conectividad real con Internet.
    - La velocidad efectiva de la conexión.
    """

    hostname = socket.gethostname()

    try:

        fully_qualified_domain_name = (
            socket.getfqdn()
        )

    except OSError:

        fully_qualified_domain_name = hostname

    interface_addresses = (
        psutil.net_if_addrs()
    )

    interface_statistics = (
        psutil.net_if_stats()
    )

    interfaces = []

    for interface_name, addresses in (
        interface_addresses.items()
    ):

        statistics = interface_statistics.get(
            interface_name
        )

        interface_data = {
            "name": interface_name,
            "is_up": (
                statistics.isup
                if statistics is not None
                else False
            ),
            "duplex": (
                statistics.duplex
                if statistics is not None
                else None
            ),
            "speed_mbps": (
                statistics.speed
                if statistics is not None
                else 0
            ),
            "mtu": (
                statistics.mtu
                if statistics is not None
                else None
            ),
            "ipv4": [],
            "ipv6": [],
            "mac_addresses": [],
        }

        for address in addresses:

            address_family = address.family

            if address_family == socket.AF_INET:

                interface_data["ipv4"].append(
                    {
                        "address": address.address,
                        "netmask": address.netmask,
                        "broadcast": address.broadcast,
                    }
                )

            elif address_family == socket.AF_INET6:

                interface_data["ipv6"].append(
                    {
                        "address": address.address,
                        "netmask": address.netmask,
                        "broadcast": address.broadcast,
                    }
                )

            elif address_family == psutil.AF_LINK:

                interface_data[
                    "mac_addresses"
                ].append(
                    address.address
                )

        interfaces.append(
            interface_data
        )

    return {
        "hostname": hostname,
        "fqdn": fully_qualified_domain_name,
        "interface_count": len(
            interfaces
        ),
        "interfaces": interfaces,
    }


# =============================================================================
# UPTIME
# =============================================================================

def get_uptime_info() -> dict[str, object]:
    """
    Devuelve información sobre el tiempo de funcionamiento
    del sistema.

    Actualmente obtiene:

    - Fecha y hora de inicio del sistema.
    - Segundos totales de funcionamiento.
    - Días completos.
    - Horas restantes.
    - Minutos restantes.
    - Segundos restantes.

    Devuelve:
        dict[str, object]:
            Información estructurada sobre el arranque
            y el tiempo de actividad.
    """

    # psutil.boot_time() devuelve la fecha y hora de arranque
    # como una marca de tiempo Unix.
    boot_timestamp = psutil.boot_time()

    # Convertimos la marca de tiempo en un objeto datetime local.
    boot_datetime = datetime.fromtimestamp(
        boot_timestamp
    )

    # Obtenemos el momento actual.
    now = datetime.now()

    # Calculamos el tiempo transcurrido desde el arranque.
    uptime_delta = now - boot_datetime

    # Total de segundos transcurridos.
    total_seconds = max(
        0,
        int(
            uptime_delta.total_seconds()
        ),
    )

    # Dividimos el tiempo en días, horas, minutos y segundos.
    days, remaining_seconds = divmod(
        total_seconds,
        86400,
    )

    hours, remaining_seconds = divmod(
        remaining_seconds,
        3600,
    )

    minutes, seconds = divmod(
        remaining_seconds,
        60,
    )

    return {
        "boot_timestamp": boot_timestamp,

        "boot_datetime": boot_datetime.isoformat(
            timespec="seconds"
        ),

        "boot_date": boot_datetime.strftime(
            "%d/%m/%Y"
        ),

        "boot_time": boot_datetime.strftime(
            "%H:%M:%S"
        ),

        "total_seconds": total_seconds,

        "days": days,

        "hours": hours,

        "minutes": minutes,

        "seconds": seconds,
    }


# =============================================================================
# GPU
# =============================================================================

def get_gpu_info() -> dict[str, object]:
    """
    Devuelve información de las GPU NVIDIA disponibles.

    La consulta se realiza mediante nvidia-smi, incluido
    normalmente con los controladores oficiales de NVIDIA.

    Actualmente obtiene:

    - Nombre del modelo.
    - Memoria total.
    - Memoria utilizada.
    - Memoria disponible.
    - Porcentaje de utilización.
    - Temperatura.
    - Versión del controlador.

    Devuelve:
        dict:
            Diccionario con:

            available:
                Indica si se pudo consultar alguna GPU.

            provider:
                Método utilizado para obtener la información.

            gpus:
                Lista de GPU detectadas.

            error:
                Mensaje técnico si la consulta falla.
    """

    command = [
        "nvidia-smi",
        (
            "--query-gpu="
            "name,"
            "memory.total,"
            "memory.used,"
            "memory.free,"
            "utilization.gpu,"
            "temperature.gpu,"
            "driver_version"
        ),
        "--format=csv,noheader,nounits",
    ]

    try:

        completed_process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )

    except FileNotFoundError:

        return {
            "available": False,
            "provider": "nvidia-smi",
            "gpus": [],
            "error": (
                "nvidia-smi no está instalado "
                "o no se encuentra en PATH."
            ),
        }

    except subprocess.TimeoutExpired:

        return {
            "available": False,
            "provider": "nvidia-smi",
            "gpus": [],
            "error": (
                "La consulta de la GPU superó "
                "el tiempo máximo permitido."
            ),
        }

    except subprocess.CalledProcessError as exception:

        error_message = (
            exception.stderr.strip()
            if exception.stderr
            else str(exception)
        )

        return {
            "available": False,
            "provider": "nvidia-smi",
            "gpus": [],
            "error": error_message,
        }

    output = completed_process.stdout.strip()

    if not output:

        return {
            "available": False,
            "provider": "nvidia-smi",
            "gpus": [],
            "error": (
                "nvidia-smi no devolvió información "
                "sobre ninguna GPU."
            ),
        }

    reader = csv.reader(
        io.StringIO(output)
    )

    gpus = []

    for index, row in enumerate(
        reader
    ):

        if len(row) != 7:
            continue

        values = [
            value.strip()
            for value in row
        ]

        (
            name,
            memory_total_mb,
            memory_used_mb,
            memory_free_mb,
            utilization_percent,
            temperature_celsius,
            driver_version,
        ) = values

        try:

            gpu_data = {
                "index": index,
                "name": name,
                "memory_total_mb": int(
                    memory_total_mb
                ),
                "memory_used_mb": int(
                    memory_used_mb
                ),
                "memory_free_mb": int(
                    memory_free_mb
                ),
                "utilization_percent": int(
                    utilization_percent
                ),
                "temperature_celsius": int(
                    temperature_celsius
                ),
                "driver_version": driver_version,
            }

        except ValueError:
            continue

        gpus.append(
            gpu_data
        )

    if not gpus:

        return {
            "available": False,
            "provider": "nvidia-smi",
            "gpus": [],
            "error": (
                "La respuesta de nvidia-smi "
                "no tenía un formato válido."
            ),
        }

    return {
        "available": True,
        "provider": "nvidia-smi",
        "gpus": gpus,
        "error": None,
    }

# =============================================================================
# BATERÍA
# =============================================================================

def get_battery_info() -> dict[str, object]:
    """
    Devuelve información sobre la batería del sistema.

    Actualmente obtiene:

    - Si el equipo dispone de batería.
    - Porcentaje de carga.
    - Si está conectado a la corriente.
    - Tiempo restante estimado.
    - Estado de la estimación de autonomía.

    En equipos de sobremesa, psutil normalmente devuelve None.
    """

    battery = psutil.sensors_battery()

    if battery is None:

        return {
            "available": False,
            "percent": None,
            "power_plugged": None,
            "seconds_left": None,
            "time_status": "not_available",
        }

    seconds_left = battery.secsleft

    if seconds_left == psutil.POWER_TIME_UNLIMITED:

        normalized_seconds_left = None
        time_status = "unlimited"

    elif seconds_left == psutil.POWER_TIME_UNKNOWN:

        normalized_seconds_left = None
        time_status = "unknown"

    else:

        normalized_seconds_left = max(
            0,
            int(seconds_left),
        )

        time_status = "estimated"

    return {
        "available": True,
        "percent": float(
            battery.percent
        ),
        "power_plugged": battery.power_plugged,
        "seconds_left": normalized_seconds_left,
        "time_status": time_status,
    }