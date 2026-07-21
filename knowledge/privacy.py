"""Clasificacion y filtrado testeable de conocimiento sensible."""

from dataclasses import replace
from enum import Enum
import re

from knowledge.fragment import KnowledgeFragment


class Sensitivity(str, Enum):
    NONE = "none"
    PERSONAL = "personal"
    FINANCIAL = "financial"
    MEDICAL = "medical"
    SECRET = "secret"


class KnowledgePrivacyFilter:
    """Aplica politica explicita; la deteccion es solo una defensa adicional."""

    _PATTERNS = {
        Sensitivity.SECRET: re.compile(
            r"(?i)\b(password|contrase(?:n|ñ)a|token|api[_ -]?key|secret)\b\s*[:=]?\s*\S+"
        ),
        Sensitivity.FINANCIAL: re.compile(
            r"(?i)\b(?:ES\d{22}|iban|nomina|n[oó]mina)\b"
        ),
        Sensitivity.MEDICAL: re.compile(
            r"(?i)\b(diagn[oó]stico|historial m[eé]dico|medicaci[oó]n)\b"
        ),
        Sensitivity.PERSONAL: re.compile(
            r"(?i)\b(?:DNI|NIE|tel[eé]fono|direcci[oó]n|correo)\b|"
            r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"
        ),
    }
    _MASK_VALUE = re.compile(r"(?<=[:=])\s*\S+(?:\s+\S+){0,3}")

    def classify(self, fragment: KnowledgeFragment) -> Sensitivity:
        declared = str(fragment.metadata.get("sensitivity", "")).casefold()
        for level in Sensitivity:
            if declared == level.value:
                return level
        for level, pattern in self._PATTERNS.items():
            if pattern.search(fragment.content):
                return level
        return Sensitivity.PERSONAL if fragment.sensitive else Sensitivity.NONE

    def filter(
        self,
        fragments: list[KnowledgeFragment],
        *,
        allow_sensitive: bool,
        has_permission: bool,
        mask_sensitive: bool = True,
    ) -> tuple[list[KnowledgeFragment], int]:
        selected: list[KnowledgeFragment] = []
        excluded = 0
        for fragment in fragments:
            level = self.classify(fragment)
            if level is Sensitivity.NONE:
                selected.append(fragment)
                continue
            if not allow_sensitive or not has_permission:
                excluded += 1
                continue
            if mask_sensitive:
                content = self._MASK_VALUE.sub(" [DATO PROTEGIDO]", fragment.content)
                selected.append(replace(fragment, content=content, sensitive=True))
            else:
                selected.append(replace(fragment, sensitive=True))
        return selected, excluded
