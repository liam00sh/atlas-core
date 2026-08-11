"""Conservative normalization for spoken text and local transcripts."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from voice.stt import STTConfidence, STTResult


class SpeechTextNormalizer:
    """Build a spoken version without changing the visible response."""

    _CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
    _PATH = re.compile(r"(?<!\w)(?:[A-Za-z]:\\|/)[^\s,;]+")
    _MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
    _SENTENCE = re.compile(r".*?(?:[.!?](?=\s|$)|$)", re.DOTALL)

    _CONSOLE_CLOSURE = "Te muestro el resto en la consola."
    _LONG_CLOSURE = "La respuesta completa es extensa. Te muestro los detalles en la consola."

    @classmethod
    def normalize(
        cls,
        text: str,
        *,
        max_sentences: int = 2,
        max_chars: int = 360,
    ) -> str:
        value = unicodedata.normalize("NFC", str(text))
        value = cls._CODE_BLOCK.sub(" Se omite un bloque de codigo en la locucion. ", value)
        value = cls._MARKDOWN_LINK.sub(r"\1", value)
        value = cls._PATH.sub(" una ruta local ", value)
        value = re.sub(r"`([^`]+)`", r"\1", value)
        value = re.sub(r"(?m)^\s*(?:[-*+] |\d+[.)]\s+)", "", value)
        value = value.replace("#", " ").replace("_", " ")
        value = "".join(
            char for char in value
            if unicodedata.category(char) not in {"So", "Sk", "Cs", "Co", "Cn"}
        )
        value = re.sub(r"\s+", " ", value).strip()
        if not value:
            return ""
        sentences = [match.group(0).strip() for match in cls._SENTENCE.finditer(value) if match.group(0).strip()]
        sentence_limit = max(1, int(max_sentences))
        char_limit = max(120, int(max_chars))
        if not sentences:
            return ""
        if len(sentences[0]) > char_limit:
            return cls._LONG_CLOSURE

        selected: list[str] = []
        content_limit = sentence_limit if len(sentences) <= sentence_limit else max(1, sentence_limit - 1)
        for sentence in sentences:
            if len(selected) >= content_limit:
                break
            candidate = " ".join((*selected, sentence)).strip()
            if len(candidate) > char_limit:
                break
            selected.append(sentence)

        truncated = len(selected) < len(sentences)
        if truncated:
            while selected and len(" ".join((*selected, cls._CONSOLE_CLOSURE))) > char_limit:
                selected.pop()
            if not selected:
                return cls._LONG_CLOSURE
            selected.append(cls._CONSOLE_CLOSURE)
        result = " ".join(selected).strip()
        if result and result[-1] not in ".!?":
            result += "."
        return result


class ContextualTranscriptNormalizer:
    """Correct known vocabulary only; never invent a sensitive action."""

    _SAFE_WORDS = {
        "ciste": "chiste",
        "teleramo": "telegram",
        "t\u00e9leramo": "telegram",
        "exicame": "expl\u00edcame",
    }

    @classmethod
    def normalize(cls, result: STTResult, *, pending_confirmation: bool = False) -> STTResult:
        text = unicodedata.normalize("NFC", " ".join(result.text.split())).strip()
        text = re.sub(r"^(?:oye\s+)?daxter[\s,.:;-]+", "", text, flags=re.IGNORECASE)
        confidence = result.confidence
        if pending_confirmation:
            canonical = cls._confirmation_word(text)
            if canonical is not None:
                text = canonical
                confidence = STTConfidence.HIGH
        if result.confidence is STTConfidence.HIGH:
            for source, target in cls._SAFE_WORDS.items():
                text = re.sub(rf"\b{re.escape(source)}\b", target, text, flags=re.IGNORECASE)
        values = {name: getattr(result, name) for name in result.__dataclass_fields__}
        values["text"] = text
        values["confidence"] = confidence
        return STTResult(**values)

    @staticmethod
    def _plain(text: str) -> str:
        value = unicodedata.normalize("NFKD", text.casefold())
        value = "".join(char for char in value if not unicodedata.combining(char))
        return " ".join(re.sub(r"[^a-z]+", " ", value).split())

    @classmethod
    def _confirmation_word(cls, text: str) -> str | None:
        value = cls._plain(text)
        exact = {
            "si": "si",
            "confirmar": "confirmar",
            "confirmo": "confirmar",
            "adelante": "confirmar",
            "no": "no",
            "cancelar": "cancelar",
            "cancelado": "cancelar",
            "cancelada": "cancelar",
            "cancela": "cancelar",
            "dejalo": "cancelar",
        }
        if value in exact:
            return exact[value]
        if " " in value or not value:
            return None
        candidates = {
            "confirmar": "confirmar",
            "confirmo": "confirmar",
            "cancelar": "cancelar",
            "cancelado": "cancelar",
            "cancela": "cancelar",
        }
        match, score = max(
            ((target, SequenceMatcher(None, value, source).ratio()) for source, target in candidates.items()),
            key=lambda item: item[1],
        )
        return match if score >= 0.62 else None
