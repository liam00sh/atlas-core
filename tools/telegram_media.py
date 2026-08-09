"""Herramientas internas separadas para envíos Telegram controlados."""
from __future__ import annotations

from tools.base_tool import BaseTool, ToolRisk
from tools.capability import Capability
from tools.context import ToolContext
from tools.result import ToolResult
from telegram_interface.outbound import TelegramOutboundError, TelegramOutboundMediaService


class TelegramSendMediaTool(BaseTool):
    risk = ToolRisk.HIGH

    def __init__(self, media_type: str, service: TelegramOutboundMediaService) -> None:
        super().__init__()
        self.media_type = media_type
        self.service = service
        self.tool_id = f"atlas.telegram.send_{media_type}"
        self.name = f"Enviar {media_type} a Telegram"
        self.capabilities = (Capability(f"telegram.send_{media_type}"),)
        self.required_permissions = frozenset({f"telegram.send_{media_type}"})

    def validate_arguments(self, arguments: dict) -> None:
        super().validate_arguments(arguments)
        if not str(arguments.get("root", "")).strip() or not str(arguments.get("relative_path", "")).strip():
            raise ValueError("Se requieren una raíz autorizada y una ruta relativa.")

    def execute(self, capability: Capability, arguments: dict, context: ToolContext) -> ToolResult:
        permission = f"telegram.send_{self.media_type}"
        if str(capability) != permission or not context.has_permission(permission):
            return ToolResult.fail("No tienes permiso para enviar este tipo de archivo.", error="permission_denied")
        try:
            self.validate_arguments(arguments)
            result = self.service.send(
                requested_by=context.requested_by,
                media_type=self.media_type,
                root_name=str(arguments["root"]),
                relative_path=str(arguments["relative_path"]),
                contains_personal_data=arguments.get("contains_personal_data") is True,
                confirmed=arguments.get("confirmed") is True,
                delete_after_send=arguments.get("delete_after_send") is True,
            )
            return ToolResult.ok(
                "El archivo se ha enviado al chat vinculado.",
                data={"media_type": result.media_type, "mime_type": result.mime_type, "byte_size": result.byte_size},
            )
        except (TelegramOutboundError, ValueError) as exc:
            code = getattr(exc, "code", "invalid_arguments")
            return ToolResult.fail(str(exc), error=code)


def build_telegram_media_tools(service: TelegramOutboundMediaService) -> tuple[TelegramSendMediaTool, ...]:
    return tuple(TelegramSendMediaTool(kind, service) for kind in ("photo", "voice", "audio", "document"))
