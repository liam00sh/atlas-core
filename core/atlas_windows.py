"""
Proyecto Atlas
Archivo: core/atlas_windows.py

Mixin conversacional para acciones Windows deterministas.
"""

from __future__ import annotations

from automation.windows_intent_service import WindowsIntentService


class AtlasWindowsMixin:
    """Añade a Atlas la resolución conversacional segura de Windows."""

    windows_intent_service: WindowsIntentService | None = None

    def configure_windows_intents(
        self,
        service: WindowsIntentService,
    ) -> None:
        self.windows_intent_service = service

    def _handle_windows_intent(
        self,
        original_text: str,
        *,
        user_id: str,
        channel: str = "cli",
    ) -> bool:
        service = self.windows_intent_service
        if service is None:
            return False

        outcome = service.handle(
            original_text,
            user_id=user_id,
            channel=channel,
        )
        if not outcome.handled:
            return False

        self._emit_windows_response(outcome.message)
        return True

    def _emit_windows_response(self, message: str) -> None:
        print()
        print(message)
