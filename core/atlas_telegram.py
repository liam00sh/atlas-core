"""
===============================================================================
Proyecto Atlas
Archivo: core/atlas_telegram.py

Descripción:
    Gestión determinista de operaciones administrativas locales de Telegram.

    Evita que una petición de vinculación llegue al modelo de IA y que este
    invente páginas web o pasos inexistentes. La capacidad real continúa
    ejecutándose mediante Atlas Tools Framework.
===============================================================================
"""

from __future__ import annotations

import re
import unicodedata

from core.log_manager import info


class AtlasTelegramMixin:
    """Añade a Atlas comandos locales seguros para vincular Telegram."""

    _TELEGRAM_LINK_CODE_RE = re.compile(
        r"(?<![A-Z0-9])[A-HJ-NP-Z2-9]{10}(?![A-Z0-9])",
        re.IGNORECASE,
    )

    @staticmethod
    def _normalize_telegram_admin_text(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", str(text))
        normalized = "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        )
        return re.sub(r"\s+", " ", normalized.casefold()).strip()

    def _extract_telegram_target_user(self, original_text: str) -> str:
        """
        Obtiene el usuario de destino.

        Por seguridad, si no existe una referencia explícita válida se utiliza
        siempre el usuario local autenticado, nunca un nombre inventado por IA.
        """

        current_user = self.get_user()
        normalized = self._normalize_telegram_admin_text(original_text)

        users = getattr(self, "users", None)
        profiles = getattr(users, "profiles", None)
        if not isinstance(profiles, dict):
            return current_user

        for candidate in profiles:
            clean_candidate = str(candidate).strip()
            if not clean_candidate:
                continue
            normalized_candidate = self._normalize_telegram_admin_text(clean_candidate)
            patterns = (
                rf"\bpara\s+(?:el\s+usuario\s+)?{re.escape(normalized_candidate)}\b",
                rf"\bal\s+usuario\s+{re.escape(normalized_candidate)}\b",
                rf"\busuario\s+{re.escape(normalized_candidate)}\b",
            )
            if any(re.search(pattern, normalized) for pattern in patterns):
                return clean_candidate

        return current_user

    def _handle_telegram_link_request(self, original_text: str) -> bool:
        """
        Intercepta una vinculación local de Telegram antes de llegar a la IA.

        Devuelve ``True`` cuando la entrada pertenece al flujo de vinculación,
        incluso si faltan datos o la capacidad rechaza la operación.
        """

        normalized = self._normalize_telegram_admin_text(original_text)
        if "telegram" not in normalized:
            return False

        link_markers = (
            "vincula",
            "vincular",
            "vinculacion",
            "confirma",
            "confirmar",
            "autoriza",
            "autorizar",
            "codigo",
        )
        if not any(marker in normalized for marker in link_markers):
            return False

        code_match = self._TELEGRAM_LINK_CODE_RE.search(original_text.upper())
        if code_match is None:
            print()
            print(
                "Para vincular Telegram necesito el código temporal de "
                "10 caracteres que mostró el bot. Ejemplo: "
                "«Confirma el código de Telegram ABC234DEFG para Liam»."
            )
            return True

        code = code_match.group(0).upper()
        target_user = self._extract_telegram_target_user(original_text)

        result = self.execute_framework_tool(
            "telegram.link.confirm",
            arguments={
                "code": code,
                "atlas_user_id": target_user,
                "confirmed": True,
            },
            channel="cli",
            metadata={"source": "deterministic_telegram_link_command"},
        )

        print()
        print(result.message)

        if result.success:
            info(
                "Vinculación Telegram confirmada mediante comando local "
                f"determinista para el usuario {target_user}."
            )
        else:
            info(
                "Vinculación Telegram rechazada mediante comando local. "
                f"Error: {result.error}."
            )

        return True
