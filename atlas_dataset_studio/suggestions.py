from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from .models import Sample


@dataclass(slots=True)
class Suggestion:
    emotion: str = "neutral"
    intention: str = "indeterminada"
    energy: str = "media"
    personality_tags: list[str] = field(default_factory=list)
    conversation_use: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


class DatasetSuggestionProvider(ABC):
    @abstractmethod
    def suggest(self, sample: Sample) -> Suggestion: ...


class HeuristicSuggestionProvider(DatasetSuggestionProvider):
    """Asistencia determinista; nunca modifica la muestra por sí sola."""

    def suggest(self, sample: Sample) -> Suggestion:
        text = sample.normalized_text.casefold()
        result = Suggestion()
        if "?" in text:
            result.intention = "pregunta"
            result.conversation_use.append("pregunta")
        elif "!" in text:
            result.intention = "exclamacion"
            result.energy = "alta"
            result.conversation_use.append("reaccion")
        elif any(word in text for word in ("hola", "buenas")):
            result.intention = "saludo"
            result.conversation_use.append("saludo")
        elif any(word in text for word in ("adiós", "hasta luego")):
            result.intention = "despedida"
            result.conversation_use.append("despedida")
        if any(word in text for word in ("jaja", "broma", "gracioso", "reír")):
            result.emotion = "sonriente"
            result.personality_tags.append("humor")
            result.conversation_use.append("humor")
        if any(word in text for word in ("miedo", "socorro", "ayuda")):
            result.emotion = "asustado"
        if any(word in text for word in ("ganar", "carrera", "mejor que")):
            result.personality_tags.append("competitivo")
            result.conversation_use.append("competicion")
        if "jak" in text:
            result.personality_tags.append("autorreferencial")
        result.personality_tags = list(dict.fromkeys(result.personality_tags))
        result.conversation_use = list(dict.fromkeys(result.conversation_use))
        result.reasons.append("Reglas locales por texto y puntuación; requiere confirmación humana.")
        return result


class OllamaSuggestionProvider(DatasetSuggestionProvider):
    """Punto de extensión deliberadamente desactivado en v1."""

    def suggest(self, sample: Sample) -> Suggestion:
        raise RuntimeError("Ollama está desactivado en Atlas Dataset Studio v1")
