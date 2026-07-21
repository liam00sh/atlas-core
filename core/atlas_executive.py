"""Cerebro ejecutivo conversacional de Atlas.

Realiza una comprobación previa ligera antes de los manejadores funcionales:
identidad, intención, ambigüedad, seguimiento, temporalidad, privacidad y estilo.
No sustituye al modelo de IA ni ejecuta herramientas por sí mismo.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import re
import threading
from typing import Any
import unicodedata


def _plain(text: str) -> str:
    value = unicodedata.normalize("NFD", str(text).casefold())
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9ñ\s]", " ", value).split())


@dataclass(slots=True)
class ExecutiveDecision:
    speaker: str
    intent: str
    confidence: float
    enough_information: bool
    clarification_question: str | None
    memory_scope: str
    sensitive: bool
    follow_up_due: bool
    suggested_action: str | None
    style: str
    internal_summary: str


class ExecutiveStorage:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def _load(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return {"version": 1, "users": {}, "sessions": {}}
        if not isinstance(payload, dict):
            return {"version": 1, "users": {}, "sessions": {}}
        payload.setdefault("version", 1)
        payload.setdefault("users", {})
        payload.setdefault("sessions", {})
        return payload

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._load())

    def update(self, mutator):
        with self._lock:
            payload = self._load()
            result = mutator(payload)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            with temporary.open("w", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            return result


class AtlasExecutiveMixin:
    """Planificación conversacional ligera y segura."""

    _STYLE_GUIDED_MARKERS = (
        "hablame mas sencillo", "explicamelo sencillo", "respuestas mas cortas",
        "paso a paso", "sin palabras tecnicas", "modo sencillo", "modo madre",
    )
    _STYLE_NORMAL_MARKERS = (
        "modo normal", "respuestas normales", "puedes explicarlo normal",
        "desactiva modo sencillo",
    )

    def _executive_bootstrap(self) -> None:
        if getattr(self, "_executive_ready", False):
            return
        root = Path(__file__).resolve().parents[1]
        self.executive_storage = ExecutiveStorage(
            root / "data" / "conversation" / "executive_state.json"
        )
        self.last_executive_decision: dict[str, Any] | None = None
        self._executive_ready = True

    def _executive_user(self) -> str:
        getter = getattr(self, "_get_current_conversation_user", None)
        return str(getter()) if callable(getter) else str(self.get_user())

    def _executive_session(self) -> str:
        return str(getattr(self, "session_id", None) or f"cli:{self._executive_user().casefold()}")

    @staticmethod
    def _eprint(text: str) -> None:
        print()
        print(text)

    def _profile_style(self, owner: str) -> str:
        self._executive_bootstrap()
        user = self.executive_storage.snapshot().get("users", {}).get(owner.casefold(), {})
        return str(user.get("conversation_style", "normal"))

    def _set_profile_style(self, owner: str, style: str) -> None:
        def mutate(payload: dict[str, Any]) -> None:
            user = payload.setdefault("users", {}).setdefault(owner.casefold(), {"display_name": owner})
            user["conversation_style"] = style
            user["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.executive_storage.update(mutate)

    def _handle_conversation_style_request(self, text: str) -> bool:
        plain = _plain(text)
        owner = self._executive_user()
        if any(marker in plain for marker in self._STYLE_GUIDED_MARKERS):
            self._set_profile_style(owner, "guided")
            self._eprint(
                "De acuerdo. A partir de ahora usaré frases más cortas, menos tecnicismos "
                "y pasos claros. Si algo no está claro, te preguntaré una sola cosa cada vez."
            )
            return True
        if any(marker in plain for marker in self._STYLE_NORMAL_MARKERS):
            self._set_profile_style(owner, "normal")
            self._eprint("De acuerdo. Vuelvo al estilo normal de conversación.")
            return True
        return False

    @staticmethod
    def _summarize_long_message(text: str) -> str:
        compact = " ".join(str(text).split())
        if len(compact.split()) < 45:
            return compact
        sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+|\n+", compact) if item.strip()]
        markers = (
            "quiero", "necesito", "puedes", "ayuda", "problema", "no puedo",
            "me pasa", "recuerd", "dile", "busca", "explica", "pregunta",
        )
        selected = [sentence for sentence in sentences if any(m in _plain(sentence) for m in markers)]
        if not selected:
            selected = sentences[:3]
        summary = " ".join(selected[:4])
        return summary[:700]

    @staticmethod
    def _infer_intent(text: str) -> tuple[str, float, str | None]:
        plain = _plain(text)
        rules = (
            ("reminder", ("recuerdame", "avisame", "recordatorio"), 0.96),
            ("message", ("dile a", "manda a", "escribe a", "pregunta a"), 0.94),
            ("memory", ("recuerda que", "guarda que", "que sabes de", "olvida"), 0.92),
            ("internet", ("busca en internet", "consulta en internet", "busca online"), 0.98),
            ("help_problem", ("no funciona", "no puedo", "va fatal", "sale un error"), 0.82),
            ("explanation", ("explicame", "que significa", "ponme un ejemplo"), 0.91),
            ("conversation", ("estoy aburr", "cuentame", "como estas"), 0.86),
        )
        for intent, markers, confidence in rules:
            if any(marker in plain for marker in markers):
                return intent, confidence, None
        vague = {
            "esto no funciona": "¿Qué intentabas hacer justo antes de que fallara?",
            "no puedo hacerlo": "¿Qué estás intentando hacer exactamente?",
            "ayudame": "Claro. ¿Con qué necesitas ayuda?",
            "tengo un problema": "Cuéntame qué estabas intentando hacer y qué ocurrió.",
        }
        if plain in vague:
            return "ambiguous", 0.35, vague[plain]
        return "general", 0.62, None

    @staticmethod
    def _memory_scope(text: str) -> tuple[str, bool]:
        plain = _plain(text)
        sensitive = any(marker in plain for marker in (
            "medic", "dolor", "enfermed", "diagnostic", "contraseña", "clave",
            "dni", "cuenta bancaria", "problema familiar", "discusion", "ansiedad",
        ))
        if sensitive:
            return "temporary_private", True
        if any(marker in plain for marker in ("hoy", "ahora", "esta tarde", "esta noche", "mañana")):
            return "temporary", False
        if any(marker in plain for marker in ("recuerda que", "guarda que", "siempre", "mi cumpleaños")):
            return "candidate_permanent", False
        return "conversation", False

    def _register_follow_up(self, owner: str, text: str) -> None:
        plain = _plain(text)
        candidates: list[tuple[str, str, timedelta]] = [
            ("medical_visit", "la visita al médico", timedelta(hours=4)),
            ("trip", "el viaje", timedelta(hours=8)),
            ("interview", "la entrevista", timedelta(hours=4)),
            ("exam", "el examen", timedelta(hours=5)),
            ("operation", "la operación", timedelta(hours=12)),
        ]
        selected = None
        if any(marker in plain for marker in ("tengo medico", "voy al medico", "cita medica")):
            selected = candidates[0]
        elif any(marker in plain for marker in ("voy de viaje", "me voy de viaje", "mañana viajo")):
            selected = candidates[1]
        elif "entrevista" in plain:
            selected = candidates[2]
        elif "examen" in plain:
            selected = candidates[3]
        elif "operacion" in plain:
            selected = candidates[4]
        if selected is None:
            return
        kind, label, delay = selected
        now = datetime.now()
        def mutate(payload: dict[str, Any]) -> None:
            user = payload.setdefault("users", {}).setdefault(owner.casefold(), {"display_name": owner})
            threads = user.setdefault("follow_ups", [])
            # No dupliques el mismo seguimiento abierto el mismo día.
            for item in threads:
                if item.get("kind") == kind and not item.get("closed"):
                    return
            threads.append({
                "kind": kind,
                "label": label,
                "source": text[:500],
                "created_at": now.isoformat(timespec="seconds"),
                "due_after": (now + delay).isoformat(timespec="seconds"),
                "asked": False,
                "closed": False,
                "expires_at": (now + timedelta(days=7)).isoformat(timespec="seconds"),
            })
            del threads[:-30]
        self.executive_storage.update(mutate)

    def _emit_due_executive_follow_up(self, current_text: str) -> bool:
        owner = self._executive_user()
        plain = _plain(current_text)
        if any(marker in plain for marker in ("medico", "viaje", "entrevista", "examen", "operacion")):
            return False
        snapshot = self.executive_storage.snapshot()
        threads = snapshot.get("users", {}).get(owner.casefold(), {}).get("follow_ups", [])
        now = datetime.now()
        selected_index = None
        selected = None
        for index, item in enumerate(threads):
            if item.get("asked") or item.get("closed"):
                continue
            try:
                due = datetime.fromisoformat(str(item.get("due_after")))
                expires = datetime.fromisoformat(str(item.get("expires_at")))
            except (TypeError, ValueError):
                continue
            if expires < now:
                continue
            if due <= now:
                selected_index, selected = index, item
                break
        if selected is None:
            return False
        def mutate(payload: dict[str, Any]) -> None:
            item = payload["users"][owner.casefold()]["follow_ups"][selected_index]
            item["asked"] = True
            item["asked_at"] = now.isoformat(timespec="seconds")
        self.executive_storage.update(mutate)
        self._eprint(f"Por cierto, ¿qué tal fue {selected.get('label', 'eso que tenías pendiente')}?")
        return True

    def _store_decision(self, decision: ExecutiveDecision) -> None:
        self.last_executive_decision = asdict(decision)
        session = self._executive_session()
        def mutate(payload: dict[str, Any]) -> None:
            payload.setdefault("sessions", {})[session] = {
                "decision": asdict(decision),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "expires_at": (datetime.now() + timedelta(hours=12)).isoformat(timespec="seconds"),
            }
        self.executive_storage.update(mutate)

    def _executive_preflight(self, text: str) -> bool:
        """Evalúa el mensaje. Devuelve True solo si responde con una aclaración."""
        self._executive_bootstrap()
        if self._handle_conversation_style_request(text):
            return True
        owner = self._executive_user()
        intent, confidence, question = self._infer_intent(text)
        scope, sensitive = self._memory_scope(text)
        summary = self._summarize_long_message(text)
        follow_up_due = self._emit_due_executive_follow_up(text)
        self._register_follow_up(owner, text)
        decision = ExecutiveDecision(
            speaker=owner,
            intent=intent,
            confidence=confidence,
            enough_information=question is None,
            clarification_question=question,
            memory_scope=scope,
            sensitive=sensitive,
            follow_up_due=follow_up_due,
            suggested_action=None,
            style=self._profile_style(owner),
            internal_summary=summary,
        )
        self._store_decision(decision)
        if question:
            self._eprint(question)
            return True
        return False

    def _executive_prompt_context(self, original_text: str) -> str:
        """Contexto privado para el prompt; no contiene datos de otros usuarios."""
        self._executive_bootstrap()
        decision = self.last_executive_decision or {}
        if not decision:
            intent, confidence, question = self._infer_intent(original_text)
            scope, sensitive = self._memory_scope(original_text)
            decision = {
                "speaker": self._executive_user(),
                "intent": intent,
                "confidence": confidence,
                "enough_information": question is None,
                "clarification_question": question,
                "memory_scope": scope,
                "sensitive": sensitive,
                "style": self._profile_style(self._executive_user()),
                "internal_summary": self._summarize_long_message(original_text),
            }
        return (
            "COMPROBACIÓN EJECUTIVA INTERNA\n"
            f"Interlocutor: {decision.get('speaker', self._executive_user())}\n"
            f"Intención probable: {decision.get('intent', 'general')} "
            f"(confianza {float(decision.get('confidence', 0.0)):.2f})\n"
            f"Resumen de la necesidad: {decision.get('internal_summary', original_text)}\n"
            f"Ámbito de memoria recomendado: {decision.get('memory_scope', 'conversation')}\n"
            f"Información sensible: {'sí' if decision.get('sensitive') else 'no'}\n"
            f"Estilo conversacional: {decision.get('style', 'normal')}\n"
            "Antes de responder, confirma que entiendes la necesidad real. Si falta un dato esencial, "
            "haz una sola pregunta breve. No guardes información sensible o temporal como memoria permanente "
            "sin consentimiento. No inventes relaciones, posesión ni parentescos."
        )

    def adapt_response_for_profile(self, response: str, user: str | None = None) -> str:
        """Adapta presentación sin alterar el significado ni truncar contenido."""
        owner = str(user or self._executive_user())
        if self._profile_style(owner) != "guided":
            return response
        raw = str(response).strip()
        # Conserva listas, código y saltos que ya ayudan a leer.
        if "\n" in raw or raw.startswith(("•", "-", "1.")):
            return raw
        text = " ".join(raw.split())
        # Frases cortas en párrafos separados; se conserva todo el contenido.
        sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+", text) if item.strip()]
        if len(sentences) <= 1:
            return text
        return "\n\n".join(sentences)
