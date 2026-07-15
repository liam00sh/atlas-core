"""
===============================================================================
Proyecto Atlas
Archivo: ai/tools/network_tool.py

Descripción:
    Implementa la herramienta encargada de consultar información
    local de red del equipo donde se ejecuta Atlas.

    La información se obtiene mediante:

        core/system_info.py

    Actualmente proporciona:

    - Nombre del equipo.
    - Nombre completo del host.
    - Interfaces de red.
    - Estado de cada interfaz.
    - Direcciones IPv4.
    - Direcciones IPv6.
    - Direcciones MAC.
    - Máscara de red.
    - Velocidad del adaptador.

    Esta herramienta consulta únicamente información local.

    No obtiene:

    - IP pública.
    - Proveedor de Internet.
    - Velocidad real de conexión.
    - Estado garantizado de Internet.

    No utiliza Internet.

    No modifica el sistema.

===============================================================================
"""


# =============================================================================
# IMPORTACIONES
# =============================================================================

from ai.tools.base_tool import BaseTool
from ai.tools.base_tool import ToolResult

from core.system_info import get_network_info


class NetworkTool(BaseTool):
    """
    Herramienta que proporciona información real
    sobre la configuración local de red.
    """

    name = "get_network_info"

    description = (
        "Obtiene el nombre del equipo, las interfaces de red, "
        "sus direcciones IP, direcciones MAC, estado y velocidad."
    )

    requires_confirmation = False
    requires_internet = False
    is_destructive = False

    def execute(
        self,
        atlas,
        interface: str | None = None,
        only_active: bool = True,
        **kwargs,
    ) -> ToolResult:
        """
        Consulta la información actual de red.

        Parámetros:
            atlas:
                Instancia principal de Atlas.

            interface:
                Nombre concreto de una interfaz.

                Ejemplos:
                    Ethernet
                    Wi-Fi

                Si no se indica, se muestran todas
                las interfaces correspondientes al filtro.

            only_active:
                Si es True, muestra únicamente interfaces activas.

            **kwargs:
                Argumentos adicionales reservados
                para futuras versiones.

        Devuelve:
            ToolResult:
                Resultado normalizado de la consulta.
        """

        try:

            network_info = get_network_info()

        except Exception as exception:

            return ToolResult(
                success=False,
                message=(
                    "No he podido consultar la información "
                    "de red del sistema."
                ),
                error=str(exception),
            )

        interfaces = network_info.get(
            "interfaces",
            [],
        )

        if interface:

            normalized_interface = (
                interface.strip().casefold()
            )

            interfaces = [
                current_interface
                for current_interface in interfaces
                if normalized_interface
                in current_interface.get(
                    "name",
                    "",
                ).casefold()
            ]

        elif only_active:

            interfaces = [
                current_interface
                for current_interface in interfaces
                if current_interface.get(
                    "is_up",
                    False,
                )
            ]

        if not interfaces:

            if interface:

                message = (
                    f"No he encontrado ninguna interfaz "
                    f"de red llamada «{interface}»."
                )

                error = "interface_not_found"

            else:

                message = (
                    "No he encontrado ninguna interfaz "
                    "de red activa."
                )

                error = "no_active_interfaces"

            return ToolResult(
                success=False,
                message=message,
                data=network_info,
                error=error,
            )

        message_blocks = []
        structured_interfaces = []

        for current_interface in interfaces:

            interface_name = current_interface.get(
                "name",
                "Interfaz desconocida",
            )

            is_up = current_interface.get(
                "is_up",
                False,
            )

            state = (
                "Activa"
                if is_up
                else "Inactiva"
            )

            speed_mbps = current_interface.get(
                "speed_mbps",
                0,
            )

            mtu = current_interface.get(
                "mtu"
            )

            ipv4_addresses = current_interface.get(
                "ipv4",
                [],
            )

            ipv6_addresses = current_interface.get(
                "ipv6",
                [],
            )

            mac_addresses = current_interface.get(
                "mac_addresses",
                [],
            )

            lines = [
                f"Interfaz: {interface_name}",
                f"Estado: {state}",
            ]

            if speed_mbps and speed_mbps > 0:

                lines.append(
                    f"Velocidad del enlace: "
                    f"{speed_mbps} Mbps"
                )

            else:

                lines.append(
                    "Velocidad del enlace: "
                    "No disponible"
                )

            if mtu is not None:

                lines.append(
                    f"MTU: {mtu}"
                )

            if mac_addresses:

                lines.append(
                    "Dirección MAC: "
                    + ", ".join(
                        mac_addresses
                    )
                )

            else:

                lines.append(
                    "Dirección MAC: No disponible"
                )

            if ipv4_addresses:

                lines.append(
                    "Direcciones IPv4:"
                )

                for ipv4 in ipv4_addresses:

                    address = ipv4.get(
                        "address",
                        "No disponible",
                    )

                    netmask = ipv4.get(
                        "netmask",
                        "No disponible",
                    )

                    lines.append(
                        f"- {address} "
                        f"(máscara: {netmask})"
                    )

            else:

                lines.append(
                    "Direcciones IPv4: "
                    "No disponibles"
                )

            if ipv6_addresses:

                lines.append(
                    "Direcciones IPv6:"
                )

                for ipv6 in ipv6_addresses:

                    address = ipv6.get(
                        "address",
                        "No disponible",
                    )

                    lines.append(
                        f"- {address}"
                    )

            else:

                lines.append(
                    "Direcciones IPv6: "
                    "No disponibles"
                )

            message_blocks.append(
                "\n".join(
                    lines
                )
            )

            structured_interfaces.append(
                current_interface
            )

        hostname = network_info.get(
            "hostname",
            "No disponible",
        )

        fqdn = network_info.get(
            "fqdn",
            hostname,
        )

        message = (
            "Información local de red:\n\n"
            f"Nombre del equipo: {hostname}\n"
            f"Nombre completo del host: {fqdn}\n\n"
            + "\n\n".join(
                message_blocks
            )
        )

        return ToolResult(
            success=True,
            message=message,
            data={
                "hostname": hostname,
                "fqdn": fqdn,
                "interface_count": len(
                    structured_interfaces
                ),
                "interfaces": (
                    structured_interfaces
                ),
                "only_active": only_active,
                "requested_interface": interface,
            },
        )