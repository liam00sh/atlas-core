"""
===============================================================================
Proyecto Atlas
Archivo: ai/tools/disk_tool.py

Descripción:
    Implementa la herramienta encargada de consultar las unidades
    de almacenamiento del equipo donde se ejecuta Atlas.

    La información se obtiene mediante:

        core/system_info.py

    Actualmente proporciona:

    - Unidades disponibles.
    - Capacidad total.
    - Espacio utilizado.
    - Espacio libre.
    - Porcentaje de utilización.
    - Sistema de archivos.

    Puede consultar:

    - Todas las unidades disponibles.
    - Una unidad concreta, por ejemplo C:.

    No utiliza Internet.

    No modifica el sistema.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from ai.tools.base_tool import BaseTool
from ai.tools.base_tool import ToolResult

from core.system_info import bytes_to_gigabytes
from core.system_info import get_disk_info


class DiskTool(BaseTool):
    """
    Herramienta que proporciona información real
    sobre las unidades de almacenamiento.
    """

    name = "get_disk_info"

    description = (
        "Obtiene las unidades de almacenamiento, su capacidad, "
        "espacio usado, espacio disponible y porcentaje de ocupación."
    )

    requires_confirmation = False
    requires_internet = False
    is_destructive = False

    def execute(
        self,
        atlas,
        drive: str | None = None,
        **kwargs,
    ) -> ToolResult:
        """
        Consulta el estado actual de los discos.

        Parámetros:
            atlas:
                Instancia principal de Atlas.

            drive:
                Unidad concreta que debe consultarse.

                Ejemplos:
                    C:
                    D:
                    C:\\

                Si no se indica, se muestran todas las unidades.

            **kwargs:
                Argumentos adicionales reservados para futuras versiones.

        Devuelve:
            ToolResult:
                Resultado normalizado de la consulta.
        """

        try:

            disk_info = get_disk_info()

        except Exception as exception:

            return ToolResult(
                success=False,
                message=(
                    "No he podido consultar las unidades "
                    "de almacenamiento."
                ),
                error=str(exception),
            )

        partitions = disk_info.get(
            "partitions",
            [],
        )

        if not partitions:

            return ToolResult(
                success=False,
                message=(
                    "No he encontrado ninguna unidad "
                    "de almacenamiento accesible."
                ),
                error="no_accessible_partitions",
            )

        # ---------------------------------------------------------------------
        # FILTRO DE UNIDAD
        # ---------------------------------------------------------------------

        selected_partitions = partitions

        if drive:

            normalized_drive = self._normalize_drive(
                drive
            )

            selected_partitions = [
                partition
                for partition in partitions
                if self._partition_matches_drive(
                    partition=partition,
                    drive=normalized_drive,
                )
            ]

            if not selected_partitions:

                return ToolResult(
                    success=False,
                    message=(
                        f"No he encontrado una unidad accesible "
                        f"llamada {normalized_drive}."
                    ),
                    error="drive_not_found",
                )

        # ---------------------------------------------------------------------
        # FORMATEO
        # ---------------------------------------------------------------------

        message_blocks = []
        structured_partitions = []

        for partition in selected_partitions:

            total_gb = bytes_to_gigabytes(
                partition["total_bytes"]
            )

            used_gb = bytes_to_gigabytes(
                partition["used_bytes"]
            )

            free_gb = bytes_to_gigabytes(
                partition["free_bytes"]
            )

            usage_percent = partition[
                "usage_percent"
            ]

            device = (
                partition.get("device")
                or partition.get("mountpoint")
                or "Unidad desconocida"
            )

            mountpoint = partition.get(
                "mountpoint",
                "No disponible",
            )

            filesystem = (
                partition.get("filesystem")
                or "No disponible"
            )

            message_blocks.append(
                (
                    f"Unidad: {device}\n"
                    f"Punto de montaje: {mountpoint}\n"
                    f"Sistema de archivos: {filesystem}\n"
                    f"Capacidad total: {total_gb} GB\n"
                    f"Espacio utilizado: {used_gb} GB\n"
                    f"Espacio disponible: {free_gb} GB\n"
                    f"Uso actual: {usage_percent}%"
                )
            )

            structured_partitions.append(
                {
                    "device": device,
                    "mountpoint": mountpoint,
                    "filesystem": filesystem,
                    "total_bytes": partition["total_bytes"],
                    "used_bytes": partition["used_bytes"],
                    "free_bytes": partition["free_bytes"],
                    "total_gb": total_gb,
                    "used_gb": used_gb,
                    "free_gb": free_gb,
                    "usage_percent": usage_percent,
                }
            )

        if drive:

            header = (
                "Estado de la unidad solicitada:"
            )

        else:

            header = (
                "Unidades de almacenamiento disponibles:"
            )

        message = (
            f"{header}\n\n"
            + "\n\n".join(
                message_blocks
            )
        )

        return ToolResult(
            success=True,
            message=message,
            data={
                "requested_drive": drive,
                "partition_count": len(
                    structured_partitions
                ),
                "partitions": structured_partitions,
            },
        )

    @staticmethod
    def _normalize_drive(
        drive: str,
    ) -> str:
        """
        Normaliza el nombre de una unidad.

        Ejemplos:
            c
            c:
            C:\\

        Resultado:
            C:
        """

        normalized_drive = (
            drive
            .strip()
            .upper()
            .replace("\\", "")
            .replace("/", "")
        )

        if (
            len(normalized_drive) == 1
            and normalized_drive.isalpha()
        ):
            normalized_drive += ":"

        return normalized_drive

    @staticmethod
    def _partition_matches_drive(
        partition: dict,
        drive: str,
    ) -> bool:
        """
        Comprueba si una partición corresponde
        a la unidad solicitada.
        """

        device = str(
            partition.get(
                "device",
                "",
            )
        ).upper()

        mountpoint = str(
            partition.get(
                "mountpoint",
                "",
            )
        ).upper()

        return (
            device.startswith(drive)
            or mountpoint.startswith(drive)
        )