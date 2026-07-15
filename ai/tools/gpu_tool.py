"""
===============================================================================
Proyecto Atlas
Archivo: ai/tools/gpu_tool.py

Descripción:
    Implementa la herramienta encargada de consultar las tarjetas gráficas
    NVIDIA disponibles en el equipo donde se ejecuta Atlas.

    La información se obtiene mediante:

        core/system_info.py

    Actualmente proporciona:

    - Modelo de GPU.
    - Memoria de vídeo total.
    - Memoria de vídeo utilizada.
    - Memoria de vídeo disponible.
    - Porcentaje de utilización.
    - Temperatura.
    - Versión del controlador.

    La primera versión utiliza nvidia-smi y está orientada
    a tarjetas gráficas NVIDIA.

    No utiliza Internet.

    No modifica el sistema.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from ai.tools.base_tool import BaseTool
from ai.tools.base_tool import ToolResult

from core.system_info import get_gpu_info
from core.system_info import megabytes_to_gigabytes


class GPUTool(BaseTool):
    """
    Herramienta que proporciona información real
    sobre las GPU NVIDIA disponibles.
    """

    name = "get_gpu_info"

    description = (
        "Obtiene el modelo, la memoria, el uso, la temperatura "
        "y el controlador de las GPU NVIDIA del sistema."
    )

    requires_confirmation = False
    requires_internet = False
    is_destructive = False

    def execute(
        self,
        atlas,
        **kwargs,
    ) -> ToolResult:
        """
        Consulta el estado actual de las GPU.

        Parámetros:
            atlas:
                Instancia principal de Atlas.

            **kwargs:
                Argumentos adicionales reservados
                para futuras versiones.

        Devuelve:
            ToolResult:
                Resultado normalizado de la consulta.
        """

        try:

            gpu_info = get_gpu_info()

        except Exception as exception:

            return ToolResult(
                success=False,
                message=(
                    "No he podido consultar la información "
                    "de la tarjeta gráfica."
                ),
                error=str(exception),
            )

        if not gpu_info.get(
            "available",
            False,
        ):

            error = gpu_info.get(
                "error",
                "No se ha detectado ninguna GPU compatible.",
            )

            return ToolResult(
                success=False,
                message=(
                    "No he podido obtener información de una GPU NVIDIA. "
                    "Puede que el equipo no tenga una tarjeta compatible "
                    "o que nvidia-smi no esté disponible."
                ),
                data=gpu_info,
                error=str(error),
            )

        gpus = gpu_info.get(
            "gpus",
            [],
        )

        if not gpus:

            return ToolResult(
                success=False,
                message=(
                    "No he encontrado ninguna tarjeta gráfica "
                    "NVIDIA disponible."
                ),
                data=gpu_info,
                error="no_gpu_found",
            )

        message_blocks = []
        structured_gpus = []

        for gpu in gpus:

            total_gb = megabytes_to_gigabytes(
                gpu["memory_total_mb"]
            )

            used_gb = megabytes_to_gigabytes(
                gpu["memory_used_mb"]
            )

            free_gb = megabytes_to_gigabytes(
                gpu["memory_free_mb"]
            )

            message_blocks.append(
                (
                    f"GPU {gpu['index']}: {gpu['name']}\n"
                    f"Memoria total: {total_gb} GB\n"
                    f"Memoria utilizada: {used_gb} GB\n"
                    f"Memoria disponible: {free_gb} GB\n"
                    f"Uso actual: {gpu['utilization_percent']}%\n"
                    f"Temperatura: {gpu['temperature_celsius']} °C\n"
                    f"Controlador NVIDIA: {gpu['driver_version']}"
                )
            )

            structured_gpus.append(
                {
                    **gpu,
                    "memory_total_gb": total_gb,
                    "memory_used_gb": used_gb,
                    "memory_free_gb": free_gb,
                }
            )

        message = (
            "Información de la tarjeta gráfica:\n\n"
            + "\n\n".join(
                message_blocks
            )
        )

        return ToolResult(
            success=True,
            message=message,
            data={
                "provider": gpu_info.get(
                    "provider"
                ),
                "gpu_count": len(
                    structured_gpus
                ),
                "gpus": structured_gpus,
            },
        )