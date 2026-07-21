"""Herramienta local para confirmar o revocar cuentas Telegram."""

from __future__ import annotations

from tools.base_tool import BaseTool, ToolRisk
from tools.capability import Capability
from tools.context import ToolContext
from tools.result import ToolResult
from telegram_interface.identity_linker import TelegramIdentityLinker, TelegramLinkError
from telegram_interface.audit import TelegramAuditLogger


class TelegramAccountTool(BaseTool):
    tool_id = "atlas.telegram.accounts"
    name = "Administracion local de cuentas Telegram"
    capabilities = (
        Capability("telegram.link.confirm"),
        Capability("telegram.admin.revoke"),
    )
    required_permissions = frozenset()
    risk = ToolRisk.HIGH

    def __init__(self, linker: TelegramIdentityLinker, *, user_exists, audit: TelegramAuditLogger | None = None) -> None:
        super().__init__()
        self.linker = linker
        self.user_exists = user_exists
        self.audit = audit

    def validate_arguments(self, arguments: dict) -> None:
        super().validate_arguments(arguments)
        if arguments.get("confirmed") is not True:
            raise ValueError("La operacion requiere confirmacion explicita.")

    def execute(self, capability: Capability, arguments: dict, context: ToolContext) -> ToolResult:
        requested = str(capability)
        permission = "telegram.admin_link" if requested == "telegram.link.confirm" else "telegram.admin_revoke"
        if not context.has_permission(permission):
            return ToolResult.fail("No tienes permiso para administrar cuentas Telegram.", error="permission_denied")
        try:
            if requested == "telegram.link.confirm":
                result = self.linker.confirm_code(
                    str(arguments.get("code", "")),
                    str(arguments.get("atlas_user_id", "")),
                    user_exists=self.user_exists,
                )
                if self.audit is not None:
                    account = self.linker.get_account(result["telegram_user_id"])
                    self.audit.record(
                        action="admin_link",
                        result="linked",
                        telegram_user_id=result["telegram_user_id"],
                        chat_id=account.get("chat_id", "unknown"),
                        atlas_user_id=result["atlas_user_id"],
                    )
                return ToolResult.ok(
                    "La cuenta Telegram ha sido vinculada.",
                    data={"atlas_user_id": result["atlas_user_id"], "linked": True},
                )
            revoked = self.linker.revoke(
                telegram_user_id=(str(arguments["telegram_user_id"]) if arguments.get("telegram_user_id") else None),
                atlas_user_id=(str(arguments["atlas_user_id"]) if arguments.get("atlas_user_id") else None),
            )
            if self.audit is not None:
                self.audit.record(
                    action="admin_revoke",
                    result="revoked" if revoked else "not_found",
                    telegram_user_id=arguments.get("telegram_user_id", "by-atlas-user"),
                    chat_id="local-admin",
                    atlas_user_id=context.requested_by,
                )
            return ToolResult.ok("La cuenta Telegram ha sido revocada.", data={"revoked": revoked})
        except TelegramLinkError as exc:
            if self.audit is not None:
                self.audit.record(
                    action="admin_link" if requested == "telegram.link.confirm" else "admin_revoke",
                    result="rejected",
                    telegram_user_id="unknown",
                    chat_id="local-admin",
                    atlas_user_id=context.requested_by,
                    error_code=exc.code,
                )
            return ToolResult.fail(str(exc), error=exc.code)
