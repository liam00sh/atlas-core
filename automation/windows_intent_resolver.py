"""
Proyecto Atlas
Archivo: automation/windows_intent_resolver.py

Resolver determinista de lenguaje natural para acciones Windows cerradas.
No utiliza IA generativa y nunca produce comandos libres.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ResolvedWindowsIntent:
    action_id: str
    parameters: Mapping[str, object]
    confidence: float
    normalized_text: str


class WindowsIntentResolver:
    """Traduce frases conocidas a acciones del catálogo Windows."""

    _APPLICATION_PATTERNS = (
        re.compile(r"\b(?:abre|abrir|inicia|iniciar|lanza|lanzar)\b.*\bcalculadora\b"),
        re.compile(r"\b(?:abre|abrir|inicia|iniciar|lanza|lanzar)\b.*\bbloc de notas\b"),
        re.compile(r"\b(?:abre|abrir|inicia|iniciar|lanza|lanzar)\b.*\bnotepad\b"),
    )

    _DISK_PATTERNS = (
        re.compile(r"\b(?:cuanto|que) espacio libre\b"),
        re.compile(r"\bespacio disponible\b"),
        re.compile(r"\bcuanto almacenamiento(?: libre)?\b"),
        re.compile(r"\bespacio (?:me )?queda\b"),
    )

    _PROCESS_PATTERNS = (
        re.compile(r"\b(?:esta|sigue) abierto telegram\b"),
        re.compile(r"\btelegram esta abierto\b"),
        re.compile(r"\b(?:esta|sigue) ejecutandose telegram\b"),
        re.compile(r"\btelegram esta funcionando\b"),
    )

    def resolve(self, text: str) -> ResolvedWindowsIntent | None:
        normalized = self._normalize(text)
        if not normalized:
            return None

        if self._matches_any(normalized, self._APPLICATION_PATTERNS):
            app_id = (
                "calculator"
                if "calculadora" in normalized
                else "notepad"
            )
            return ResolvedWindowsIntent(
                action_id="windows.application.open",
                parameters={"app_id": app_id},
                confidence=1.0,
                normalized_text=normalized,
            )

        if self._matches_any(normalized, self._DISK_PATTERNS):
            return ResolvedWindowsIntent(
                action_id="windows.disk.space.read",
                parameters={},
                confidence=1.0,
                normalized_text=normalized,
            )

        if self._matches_any(normalized, self._PROCESS_PATTERNS):
            return ResolvedWindowsIntent(
                action_id="windows.process.status.read",
                parameters={"process_name": "Telegram.exe"},
                confidence=1.0,
                normalized_text=normalized,
            )

        return None

    @staticmethod
    def _matches_any(
        normalized: str,
        patterns: tuple[re.Pattern[str], ...],
    ) -> bool:
        return any(pattern.search(normalized) for pattern in patterns)

    @staticmethod
    def _normalize(text: str) -> str:
        value = unicodedata.normalize("NFKD", str(text))
        value = "".join(
            char for char in value
            if not unicodedata.combining(char)
        )
        value = value.casefold()
        value = re.sub(r"[^a-z0-9\s]", " ", value)
        value = re.sub(r"\s+", " ", value).strip()

        prefixes = (
            "daxter ",
            "coco ",
            "atlas ",
            "oye daxter ",
            "oye coco ",
            "oye atlas ",
        )
        for prefix in prefixes:
            if value.startswith(prefix):
                value = value[len(prefix):].strip()
                break
        return value
