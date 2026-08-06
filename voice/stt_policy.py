"""Decisión STT común: palabras y propósito se evalúan por separado."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re
import unicodedata
from typing import Protocol

from voice.stt import STTConfidence, STTResult


class IntentConfidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class STTDecisionKind(StrEnum):
    PROCESS = "process"
    CONFIRM = "confirm"
    REPEAT = "repeat"
    CLARIFY = "clarify"


@dataclass(frozen=True, slots=True)
class STTIntentContext:
    """Contexto temporal ya existente; nunca se persiste desde la política."""

    immediate_history: tuple[str, ...] = ()
    pending_slots: tuple[str, ...] = ()
    has_temporary_memory: bool = False


@dataclass(frozen=True, slots=True)
class IntentResolution:
    confidence: IntentConfidence
    intent: str
    clarification_question: str | None = None
    entities: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class STTDecision:
    kind: STTDecisionKind
    text: str
    response: str | None = None
    speech_confidence: STTConfidence = STTConfidence.HIGH
    intent_confidence: IntentConfidence = IntentConfidence.HIGH
    intent: str = "general"
    sensitive: bool = False


class IntentConfidenceResolver(Protocol):
    def resolve(self, text: str, context: STTIntentContext | None = None) -> IntentResolution: ...


def _plain(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())


_SENSITIVE_PATTERNS = (
    r"^(?:recuerda|recuerdame|guarda|apunta|olvida|borra)(?:\s|$)",
    r"^(?:enciende|apaga|abre|cierra|activa|desactiva|reinicia)(?:\s|$)",
    r"^(?:envia|manda|comparte|publica|elimina)(?:\s|$)",
    r"^(?:desbloquea|vincula|desvincula|modifica|cambia|pon|modo)(?:\s|$)",
)


def is_sensitive_stt_command(text: str) -> bool:
    normalized = _plain(text)
    return any(re.match(pattern, normalized) for pattern in _SENSITIVE_PATTERNS)


def missing_required_slot(text: str) -> str | None:
    normalized = _plain(text)
    if re.fullmatch(r"(?:enciende|apaga)(?:\s+(?:el|la|los|las))?", normalized):
        action = "encienda" if normalized.startswith("enciende") else "apague"
        return f"¿Qué elemento quieres que {action}?"
    if re.fullmatch(r"pon(?:\s+(?:el|la|los|las))?", normalized):
        return "¿Qué elemento quieres que ponga: la luz, la televisión o la música?"
    if re.fullmatch(r"abre(?:\s+(?:el|la|los|las))?", normalized):
        return "¿Qué quieres que abra?"
    if re.fullmatch(r"cierra(?:\s+(?:el|la|los|las))?", normalized):
        return "¿Qué quieres que cierre?"
    if re.fullmatch(r"(?:recuerdame|avisame)(?:\s+que)?", normalized):
        return "¿Qué quieres que te recuerde?"
    return None


class AtlasIntentConfidenceResolver:
    """Coordina resolvers puros existentes; no ejecuta Atlas ni herramientas."""

    _DEICTIC = frozenset({"eso", "esto", "aquello", "hazlo", "ponlo", "abrelo", "apágalo", "apagalo"})

    def resolve(self, text: str, context: STTIntentContext | None = None) -> IntentResolution:
        context = context or STTIntentContext()
        normalized = _plain(text)
        if not normalized:
            return IntentResolution(IntentConfidence.LOW, "empty", "¿Puedes repetir lo que necesitas?")
        if question := missing_required_slot(text):
            return IntentResolution(IntentConfidence.LOW, "incomplete_command", question)
        tokens = normalized.split()
        if normalized in self._DEICTIC:
            if context.pending_slots:
                return IntentResolution(IntentConfidence.HIGH, "pending_slot_answer", entities=context.pending_slots)
            if context.immediate_history or context.has_temporary_memory:
                return IntentResolution(IntentConfidence.MEDIUM, "context_reference", "¿A qué te refieres exactamente?")
            return IntentResolution(IntentConfidence.LOW, "ambiguous_reference", "¿A qué te refieres exactamente?")

        home = self._resolve_home(text)
        if home is not None:
            return home
        windows = self._resolve_windows(text)
        if windows is not None:
            return windows
        command = self._resolve_registered_command(text)
        if command is not None:
            return command

        executive = self._resolve_executive(text)
        if executive is not None and executive.confidence is IntentConfidence.LOW:
            return executive
        if re.match(r"^(?:recuerdame|avisame)\b", normalized) and not re.search(
            r"\b(?:a las|mañana|hoy|en \d+|el lunes|el martes|el miercoles|el jueves|el viernes|el sabado|el domingo)\b",
            normalized,
        ):
            return IntentResolution(IntentConfidence.MEDIUM, "reminder", "¿Cuándo quieres que te lo recuerde?")
        if len(tokens) >= 3 or normalized.endswith("?"):
            intent = executive.intent if executive is not None else "general"
            return IntentResolution(IntentConfidence.HIGH, intent)
        if len(tokens) == 2 and tokens[0] in {
            "dime", "explica", "busca", "consulta", "saluda", "ayudame", "gracias",
        }:
            return IntentResolution(IntentConfidence.HIGH, "direct_request", entities=(tokens[1],))
        return IntentResolution(
            IntentConfidence.HIGH,
            executive.intent if executive is not None else "general",
        )

    @staticmethod
    def _resolve_home(text: str) -> IntentResolution | None:
        try:
            from automation.home_intent_resolver import HomeIntentResolver

            resolved = HomeIntentResolver().resolve(text)
        except (ImportError, RuntimeError, ValueError):
            return None
        if resolved is None:
            return None
        entities = tuple(str(value) for value in resolved.parameters.values())
        return IntentResolution(IntentConfidence.HIGH, str(resolved.intent_type), entities=entities)

    @staticmethod
    def _resolve_windows(text: str) -> IntentResolution | None:
        try:
            from automation.windows_intent_resolver import WindowsIntentResolver

            resolved = WindowsIntentResolver().resolve(text)
        except (ImportError, RuntimeError, ValueError):
            return None
        if resolved is None:
            return None
        level = IntentConfidence.HIGH if resolved.confidence >= 0.85 else IntentConfidence.MEDIUM
        return IntentResolution(level, resolved.action_id, entities=tuple(str(value) for value in resolved.parameters.values()))

    @staticmethod
    def _resolve_registered_command(text: str) -> IntentResolution | None:
        try:
            from console.command_manager import COMMANDS, resolve_command
            from utils.text_normalizer import normalize_text

            normalized = normalize_text(text, COMMANDS.keys())
            resolved = resolve_command(text)
        except (ImportError, RuntimeError, ValueError):
            return None
        if resolved is None:
            return None
        level = IntentConfidence.HIGH if normalized in COMMANDS else IntentConfidence.MEDIUM
        question = None if level is IntentConfidence.HIGH else "¿Quieres ejecutar ese comando?"
        return IntentResolution(level, f"command:{resolved}", question)

    @staticmethod
    def _resolve_executive(text: str) -> IntentResolution | None:
        try:
            from core.atlas_executive import AtlasExecutiveMixin

            intent, confidence, question = AtlasExecutiveMixin._infer_intent(text)
        except (ImportError, RuntimeError, ValueError):
            return None
        if question or confidence < 0.50:
            return IntentResolution(IntentConfidence.LOW, intent, question or "¿Qué necesitas exactamente?")
        level = IntentConfidence.HIGH if confidence >= 0.85 else IntentConfidence.MEDIUM
        return IntentResolution(level, intent, question)


class STTInputPolicy:
    """Combina las dos confianzas sin ejecutar ni persistir contenido."""

    def __init__(self, intent_resolver: IntentConfidenceResolver | None = None) -> None:
        self.intent_resolver = intent_resolver or AtlasIntentConfidenceResolver()

    def evaluate(self, result: STTResult, context: STTIntentContext | None = None) -> STTDecision:
        text = " ".join(result.text.split()).strip()
        intent = self.intent_resolver.resolve(text, context)
        sensitive = is_sensitive_stt_command(text)
        common = {
            "speech_confidence": result.confidence,
            "intent_confidence": intent.confidence,
            "intent": intent.intent,
            "sensitive": sensitive,
        }
        if not text or result.confidence is STTConfidence.LOW:
            return STTDecision(
                STTDecisionKind.REPEAT,
                text,
                "No estoy seguro de haber entendido lo que has dicho. ¿Puedes repetirlo un poco más despacio?",
                **common,
            )
        if result.confidence is STTConfidence.MEDIUM:
            prefix = "Es una orden sensible y no la ejecutaré todavía. " if sensitive else ""
            return STTDecision(
                STTDecisionKind.CONFIRM,
                text,
                f"{prefix}He entendido «{text}». Corrígeme si no era eso.",
                **common,
            )
        if intent.confidence is not IntentConfidence.HIGH:
            return STTDecision(
                STTDecisionKind.CLARIFY,
                text,
                intent.clarification_question or "¿Qué quieres hacer exactamente?",
                **common,
            )
        return STTDecision(STTDecisionKind.PROCESS, text, **common)


def process_stt_result(result: STTResult, process, *, context: STTIntentContext | None = None) -> str:
    """Entrada común para CLI/transportes; solo PROCESS llama al callback."""
    decision = STTInputPolicy().evaluate(result, context)
    if decision.kind is not STTDecisionKind.PROCESS:
        return decision.response or "No he podido confirmar la transcripción."
    return str(process(decision.text))
