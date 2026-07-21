"""
===============================================================================
Proyecto Atlas
Archivo: tools/atlas_adapter.py

Descripción:
    Adaptador entre la clase Atlas y el nuevo Atlas Tools Framework.

    Traduce el estado actual de Atlas a un ToolContext seguro y delega la
    ejecución en ToolManager. No selecciona herramientas desde lenguaje
    natural y no sustituye el sistema heredado.
===============================================================================
"""

from collections.abc import Callable
from typing import Any, Protocol

from tools.context import ToolContext
from tools.exceptions import ToolError
from tools.manager import ToolManager
from tools.result import ToolResult


class AtlasLike(Protocol):
    """Contrato mínimo utilizado por el adaptador."""

    def get_user(self) -> str:
        ...

    def get_name(self) -> str:
        ...

    def can_use_tools(self) -> bool:
        ...

    def can_access_internet(self) -> bool:
        ...


PermissionResolver = Callable[[AtlasLike], set[str]]


class AtlasToolAdapter:
    """
    Conecta Atlas con ToolManager sin acoplar las herramientas al núcleo.

    Los permisos no se deducen automáticamente a partir del nombre de la
    capacidad solicitada. Solo se conceden los permisos que devuelve el
    resolvedor configurado.
    """

    SAFE_READ_PERMISSIONS = frozenset(
        {
            "filesystem.read",
            "google.drive.read",
            "knowledge.read",
            "system.status.read",
        }
    )

    def __init__(
        self,
        manager: ToolManager,
        permission_resolver: PermissionResolver | None = None,
    ) -> None:
        self.manager = manager
        self.permission_resolver = (
            permission_resolver
            or self._default_permission_resolver
        )

    @classmethod
    def _default_permission_resolver(
        cls,
        atlas: AtlasLike,
    ) -> set[str]:
        """
        Concede únicamente permisos de lectura aprobados explícitamente.

        Si la capacidad general de herramientas está desactivada, no concede
        ningún permiso.
        """

        if not atlas.can_use_tools():
            return set()

        permissions = set(cls.SAFE_READ_PERMISSIONS)
        people_manager = getattr(atlas, "people_manager", None)
        if people_manager is not None:
            try:
                person = people_manager.find_person_by_user_profile(
                    atlas.get_user()
                )
            except (AttributeError, LookupError, RuntimeError, TypeError, ValueError):
                person = None
            if person is not None and getattr(person, "status", None) == "user":
                permissions.update(
                    {
                        "memory.read",
                        "memory.propose",
                        "memory.write",
                        "memory.update",
                        "memory.delete",
                        "memory.audit.read",
                    }
                )

                users = getattr(atlas, "users", None)
                profile = (
                    users.get_profile(atlas.get_user())
                    if users is not None and hasattr(users, "get_profile")
                    else {}
                )
                roles = {
                    str(role).strip().casefold()
                    for role in profile.get("roles", ())
                }
                if roles & {"owner", "admin"}:
                    permissions.update(
                        {
                            "telegram.admin_link",
                            "telegram.admin_revoke",
                        }
                    )

        # memory.sensitive.write no se concede nunca de forma implícita.
        return permissions

    def build_context(
        self,
        atlas: AtlasLike,
        *,
        channel: str = "cli",
        metadata: dict[str, Any] | None = None,
    ) -> ToolContext:
        """Construye el contexto seguro que recibirá la herramienta."""

        request_context = getattr(atlas, "channel_request_context", None)
        if request_context is not None:
            channel = str(getattr(request_context, "channel", channel))

        safe_metadata = {
            "assistant_name": atlas.get_name(),
            "tools_enabled": atlas.can_use_tools(),
            "internet_enabled": atlas.can_access_internet(),
        }

        if metadata:
            safe_metadata.update(metadata)

        # La identidad autenticada del canal es autoritativa y no puede ser
        # sustituida por metadatos proporcionados por una herramienta.
        if request_context is not None:
            safe_metadata.update(
                {
                    "session_id": getattr(request_context, "session_id", None),
                    "telegram_user_id": getattr(request_context, "telegram_user_id", None),
                    "chat_id": getattr(request_context, "chat_id", None),
                    "message_id": getattr(request_context, "message_id", None),
                    "authentication_state": str(
                        getattr(request_context, "authentication_state", "")
                    ),
                }
            )

        permissions = self.permission_resolver(atlas)
        if request_context is not None:
            channel_permissions = {
                str(item).strip().casefold()
                for item in getattr(request_context, "permissions", ())
            }
            permissions = {
                permission
                for permission in permissions
                if permission.casefold() in channel_permissions
            }

        return ToolContext(
            requested_by=atlas.get_user(),
            channel=channel,
            permissions=permissions,
            metadata=safe_metadata,
        )

    def execute(
        self,
        atlas: AtlasLike,
        capability: str,
        *,
        arguments: dict[str, Any] | None = None,
        channel: str = "cli",
        metadata: dict[str, Any] | None = None,
    ) -> ToolResult:
        """
        Ejecuta una capacidad mediante ToolManager.

        Los errores controlados del framework se convierten en ToolResult para
        que Atlas pueda tratarlos sin depender de excepciones internas.
        """

        if not atlas.can_use_tools():
            return ToolResult.fail(
                "Las herramientas están desactivadas.",
                error="tools_disabled",
            )

        context = self.build_context(
            atlas,
            channel=channel,
            metadata=metadata,
        )

        try:
            return self.manager.execute(
                capability,
                arguments=arguments,
                context=context,
            )
        except ToolError as exception:
            result = ToolResult.fail(
                "No se pudo ejecutar la capacidad solicitada.",
                error=str(exception),
            )
            result.capability = capability
            return result
