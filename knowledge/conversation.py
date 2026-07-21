"""Reconocimiento determinista y acotado de preguntas de conocimiento."""

from dataclasses import dataclass
import re
import unicodedata


@dataclass(frozen=True, slots=True)
class KnowledgeIntent:
    question: str
    provenance_only: bool = False
    allow_sensitive: bool = False


class KnowledgeIntentRecognizer:
    """Convierte lenguaje natural conocido en una accion estructurada."""

    _SENSITIVE = re.compile(
        r"\b(dni|nie|iban|telefono|correo|direccion|nomina|medicacion)\b"
    )

    @staticmethod
    def _normalize(text: str) -> str:
        value = unicodedata.normalize("NFD", text.casefold())
        normalized = "".join(
            char for char in value
            if unicodedata.category(char) != "Mn"
        )
        return normalized.strip(" ¿?¡!.,")

    def recognize(self, text: str) -> KnowledgeIntent | None:
        normalized = self._normalize(text).strip()
        if re.fullmatch(r"(?:y )?(?:de donde|como) (?:lo )?sabes(?: eso)?\??", normalized):
            return KnowledgeIntent(text.strip(), provenance_only=True)
        markers = (
            "que sabes sobre",
            "que informacion tienes sobre",
            "como quiero que funcione",
            "que hemos decidido sobre",
            "que dice mi memoria",
            "resume lo que sabes sobre",
            "hay informacion contradictoria",
            "hablame de",
            "dime todo lo que recuerdas de",
            "dime todo lo que recuerdas sobre",
            "cuentame lo que sabes acerca de",
            "que recuerdas sobre",
            "junta todo lo que tengas sobre",
            "junta lo que sabes sobre",
        )
        if not any(marker in normalized for marker in markers):
            return None
        return KnowledgeIntent(
            text.strip(),
            allow_sensitive=bool(self._SENSITIVE.search(normalized)),
        )
