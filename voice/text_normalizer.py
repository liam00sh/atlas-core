"""Conservative normalization for spoken text and local transcripts."""

from __future__ import annotations

import re
import unicodedata

from voice.stt import STTConfidence, STTResult


class SpeechTextNormalizer:
    """Build a spoken version without changing the visible response."""

    _CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
    _PATH = re.compile(r"(?<!\w)(?:[A-Za-z]:\\|/)[^\s,;]+")
    _MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
    _SENTENCE = re.compile(r".*?(?:[.!?](?=\s|$)|$)", re.DOTALL)

    @classmethod
    def normalize(cls, text: str, *, max_sentences: int = 3) -> str:
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
        return " ".join(sentences[: max(1, int(max_sentences))]).strip()


class ContextualTranscriptNormalizer:
    """Correct known vocabulary only; never invent a sensitive action."""

    _SAFE_WORDS = {
        "ciste": "chiste",
        "teleramo": "telegram",
        "t\u00e9leramo": "telegram",
        "exicame": "expl\u00edcame",
    }

    @classmethod
    def normalize(cls, result: STTResult) -> STTResult:
        text = unicodedata.normalize("NFC", " ".join(result.text.split())).strip()
        text = re.sub(r"^(?:oye\s+)?daxter[\s,.:;-]+", "", text, flags=re.IGNORECASE)
        if result.confidence is STTConfidence.HIGH:
            for source, target in cls._SAFE_WORDS.items():
                text = re.sub(rf"\b{re.escape(source)}\b", target, text, flags=re.IGNORECASE)
        values = {name: getattr(result, name) for name in result.__dataclass_fields__}
        values["text"] = text
        return STTResult(**values)
