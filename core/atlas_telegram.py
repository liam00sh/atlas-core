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

    def _extract_telegram_target_user(self, original_text: str) -> str | None:
        """Obtiene de forma segura el perfil Atlas indicado tras «para».

        Si el usuario escribió un destino explícito que no puede resolverse,
        devuelve ``None``. Nunca sustituye silenciosamente ese destino por el
        usuario activo, porque eso podría vincular una cuenta familiar a Liam.
        """

        current_user = self.get_user()
        normalized = self._normalize_telegram_admin_text(original_text)
        # El destino puede expresarse con «para», «de», «al usuario»,
        # «usuario» o «a nombre de». El patrón exige que aparezca después
        # del código temporal para no confundir «código de Telegram» con
        # el nombre del perfil.
        code_match = self._TELEGRAM_LINK_CODE_RE.search(normalized.upper())
        suffix = (
            normalized[code_match.end():].strip()
            if code_match is not None
            else normalized
        )
        explicit_match = re.search(
            r"^(?:para|de|al usuario|usuario|a nombre de)\s+"
            r"(?:el\s+usuario\s+)?(.+?)\s*$",
            suffix,
        )
        if explicit_match is None:
            return current_user

        requested = explicit_match.group(1).strip(" .,:;!?¡¿")
        users = getattr(self, "users", None)
        profiles = getattr(users, "profiles", None)
        if not isinstance(profiles, dict):
            return None

        resolver = getattr(users, "resolve_user_name", None)
        if callable(resolver):
            resolved = resolver(requested)
            if resolved:
                return str(resolved)

        for profile_key, profile in profiles.items():
            if not isinstance(profile, dict):
                continue
            aliases = {str(profile_key), str(profile.get("name", ""))}
            for field in ("alias", "aliases", "nickname", "preferred_name"):
                value = profile.get(field)
                if isinstance(value, str):
                    aliases.add(value)
                elif isinstance(value, (list, tuple, set)):
                    aliases.update(str(item) for item in value)
            normalized_aliases = {
                self._normalize_telegram_admin_text(alias)
                for alias in aliases
                if str(alias).strip()
            }
            if requested in normalized_aliases:
                return str(profile.get("name") or profile_key)

        return None


    def _handle_profile_creation_request(self, original_text: str) -> bool:
        """Crea perfiles únicamente para personas ya conocidas y solo por Liam."""

        normalized = self._normalize_telegram_admin_text(original_text)
        match = re.match(
            r"^(?:crear|crea|anadir|añadir|anade|añade|dar de alta) "
            r"(?:un )?perfil(?: de usuario| atlas)? (?:para|a|de) (.+?)\s*$",
            normalized,
        )
        if match is None:
            return False

        requested_name = match.group(1).strip(" .,:;!?¡¿")
        success, message, _profile = self.create_profile_for_known_person(requested_name)
        print()
        print(message)
        info(
            "Alta de perfil de persona conocida "
            + ("completada." if success else "rechazada.")
        )
        return True

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
        if target_user is None:
            print()
            print(
                "No encuentro ese perfil de usuario en Atlas. Escribe el nombre "
                "exacto del perfil o créalo antes de vincular Telegram. No he "
                "vinculado la cuenta a ningún usuario."
            )
            return True

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
