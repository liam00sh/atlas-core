"""Contrato estricto entre el contenido factual de Atlas y su presentación."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import re
import unicodedata


_NUMBER_RE = re.compile(r"(?<!\w)\d+(?:[.,]\d+)?(?:\s*%)?(?!\w)")
_NAME_RE = re.compile(r"\b[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]{2,}\b")
_PROTECTED_MARKERS = (
    "no ", "error", "fall", "bloque", "permiso", "autoriz", "confirm",
    "incertid", "no sé", "no se ", "puede que", "probablemente", "quizá",
    "correctamente", "complet", "encendid", "apagad", "disponible",
)


def _plain(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value).casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


@dataclass(frozen=True, slots=True)
class BaseResponse:
    text: str
    facts: tuple[str, ...] = ()
    action_result: str | None = None
    uncertainty: str | None = None
    permissions: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @classmethod
    def from_text(cls, text: str) -> "BaseResponse":
        clean = str(text).strip()
        if not clean:
            raise ValueError("La respuesta base no puede estar vacía")
        facts = tuple(dict.fromkeys((*_NUMBER_RE.findall(clean), *_NAME_RE.findall(clean))))
        return cls(text=clean, facts=facts)


class PersonalityStrengthValue(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class StyledResponse:
    base_text: str
    styled_text: str
    emotion: str
    intensity: str
    personality_strength: str
    reason: str
    facts_preserved: bool
    validation_issues: tuple[str, ...] = field(default_factory=tuple)

    @property
    def personality_strength_used(self) -> PersonalityStrengthValue:
        return PersonalityStrengthValue(self.personality_strength)


class FactPreservationValidator:
    """Comprueba evidencia textual; nunca decide que un hecho puede cambiar."""

    @staticmethod
    def _contains(haystack: str, needle: str) -> bool:
        return _plain(needle) in _plain(haystack)

    def validate(self, base: BaseResponse, styled_text: str) -> tuple[bool, tuple[str, ...]]:
        issues: list[str] = []
        for fact in base.facts:
            if fact and not self._contains(styled_text, fact):
                issues.append(f"fact:{fact}")
        for label, values in (
            ("permission", base.permissions),
            ("error", base.errors),
        ):
            for value in values:
                if value and not self._contains(styled_text, value):
                    issues.append(f"{label}:{value}")
        for label, value in (
            ("action_result", base.action_result),
            ("uncertainty", base.uncertainty),
        ):
            if value and not self._contains(styled_text, value):
                issues.append(f"{label}:{value}")

        base_plain = _plain(base.text)
        styled_plain = _plain(styled_text)
        for marker in _PROTECTED_MARKERS:
            normalized = _plain(marker)
            if normalized in base_plain and normalized not in styled_plain:
                issues.append(f"marker:{marker.strip()}")
        return not issues, tuple(dict.fromkeys(issues))
