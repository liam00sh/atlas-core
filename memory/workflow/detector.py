"""Detector conservador y determinista de candidatos de memoria."""

import re
import unicodedata

from identity.relationship import PARTNER
from memory.workflow.models import CandidateResult


def normalize(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value).casefold())
    return " ".join(
        "".join(char for char in text if unicodedata.category(char) != "Mn").split()
    )


class CandidateDetector:
    """Extrae solo afirmaciones propias, estables o explícitamente solicitadas."""

    EXPLICIT_PREFIXES = (
        "recuerda que ", "guarda que ", "apunta que ",
        "quiero que recuerdes que ", "quiero que recuerdes esto: ",
    )
    FALSE_POSITIVE_MARKERS = (
        "quiza ", "quizas ", "tal vez ", "supongamos ", "imagina ",
        "por ejemplo", "en una pelicula", "en un cuento", "mi amigo dice",
        "mi amiga dice", "alguien dice", "segun internet", "segun drive",
    )
    SECRET_PATTERNS = (
        r"\b(contrasena|password|token|api[ -]?key|clave secreta|cvv)\b",
        r"\b(codigo de recuperacion|numero de tarjeta|credenciales?)\b",
    )
    MEDICAL_PATTERN = re.compile(
        r"\b(diagnostico|enfermedad|medicacion|medicamento|salud|medico)\b",
        re.IGNORECASE,
    )
    FINANCIAL_PATTERN = re.compile(
        r"\b(iban|nomina|salario|cuenta bancaria|deuda|inversion)\b",
        re.IGNORECASE,
    )

    def contains_secret(self, text: str) -> bool:
        """Detecta categorías que nunca deben persistirse ni registrarse en claro."""

        return any(re.search(pattern, normalize(text)) for pattern in self.SECRET_PATTERNS)

    def detect(self, text: str) -> CandidateResult | None:
        original = str(text).strip()
        normalized = normalize(original)
        if not original or original.endswith("?") or normalized.startswith(
            ("que ", "como ", "cuando ", "donde ", "quien ", "por que ")
        ):
            return None
        if any(marker in normalized for marker in self.FALSE_POSITIVE_MARKERS):
            return None

        explicit = False
        content = original
        for prefix in self.EXPLICIT_PREFIXES:
            if normalized.startswith(prefix):
                explicit = True
                # Los prefijos normalizados tienen la misma longitud útil en estos casos.
                content = re.sub(
                    r"^(recuerda|guarda|apunta)\s+que\s+|^quiero\s+que\s+recuerdes(?:\s+que|\s+esto:?)\s+",
                    "",
                    original,
                    count=1,
                    flags=re.IGNORECASE,
                ).strip()
                break

        clean = content.rstrip(". ").strip()
        clean_normalized = normalize(clean)
        if not clean:
            return None
        if self.contains_secret(clean_normalized):
            return None

        sensitive = "normal"
        reinforced = False
        if self.MEDICAL_PATTERN.search(clean_normalized) or self.FINANCIAL_PATTERN.search(clean_normalized):
            if not explicit:
                return None
            sensitive = "sensitive"
            reinforced = True

        metadata: dict[str, object] = {"explicit_request": explicit}
        category = "other"
        confidence = 0.99 if explicit else 0.0
        temporal_scope = "permanent"

        patterns = (
            (r"^mi color favorito es (.+)$", "preference", "favorite_color"),
            (r"^prefiero (.+)$", "preference", None),
            (r"^no quiero que (.+)$", "instruction", None),
            (r"^(?:yo )?trabajo (?:como |con )?(.+)$", "personal_fact", None),
            (r"^vivo en (.+)$", "personal_fact", "residence"),
            (r"^normalmente (.+)$", "routine", None),
            (r"^usaremos (.+)$", "project_decision", None),
            (r"^la raspberry pi se llamara (.+)$", "project_decision", "raspberry_name"),
        )
        for pattern, candidate_category, key in patterns:
            match = re.match(pattern, clean_normalized, re.IGNORECASE)
            if match:
                category = candidate_category
                confidence = max(confidence, 0.9)
                if key:
                    metadata["memory_key"] = key
                break

        relationship = re.match(r"^([\wáéíóúüñ -]+) es mi pareja$", clean, re.IGNORECASE)
        if relationship:
            category = "relationship"
            confidence = max(confidence, 0.96)
            metadata.update(
                {
                    "target_name": relationship.group(1).strip(),
                    "relationship_type": PARTNER,
                    "memory_key": "relationship:partner",
                }
            )

        if re.match(r"^(esta semana|hoy|manana|mañana)\b", clean_normalized):
            category = "temporary_state"
            temporal_scope = "temporary"
            confidence = max(confidence, 0.86)

        if not explicit and confidence < 0.85:
            return None
        return CandidateResult(
            content=clean,
            category=category,
            confidence=confidence,
            sensitivity=sensitive,
            temporal_scope=temporal_scope,
            metadata=metadata,
            reinforced_confirmation=reinforced,
        )
