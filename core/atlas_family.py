"""Preparación de Atlas para una beta familiar segura y comprensible.

No sustituye la autenticación, la memoria ni las herramientas existentes. Añade
una capa conversacional temprana para incorporación, cancelación universal,
confirmación de acciones sensibles, privacidad, incidencias y diagnóstico local.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import threading
import unicodedata
from typing import Any, Callable


def _plain(value: str) -> str:
    value = unicodedata.normalize("NFD", value.casefold())
    return " ".join(
        "".join(ch for ch in value if unicodedata.category(ch) != "Mn" and (ch.isalnum() or ch.isspace()))
        .split()
    )


class FamilyReadinessStorage:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            if not self.path.exists():
                return {"version": 1, "users": {}}
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                return {"version": 1, "users": {}}
            return data if isinstance(data, dict) else {"version": 1, "users": {}}

    def update(self, mutator: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        with self._lock:
            payload = self.snapshot()
            payload.setdefault("version", 1)
            payload.setdefault("users", {})
            mutator(payload)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.path)
            return deepcopy(payload)


class AtlasFamilyMixin:
    """Capa de seguridad y usabilidad previa al resto del enrutamiento."""

    _CANCEL_ALL = {
        "cancelar", "para", "parate", "detente", "dejalo", "déjalo",
        "olvida lo anterior", "olvidalo", "olvídalo", "empezar de nuevo",
        "empieza de nuevo", "reinicia la conversacion", "reinicia la conversación",
        "salir del juego", "sal del juego",
    }
    _YES = {"si", "sí", "vale", "confirmo", "confirmar", "adelante", "hazlo", "envialo", "envíalo"}
    _NO = {"no", "cancelar", "dejalo", "déjalo", "mejor no"}

    def _family_bootstrap(self) -> None:
        if getattr(self, "_family_ready", False):
            return
        root = Path(__file__).resolve().parents[1]
        self.family_readiness_storage = FamilyReadinessStorage(
            root / "data" / "family" / "readiness.json"
        )
        self.family_incident_path = root / "data" / "family" / "incidents.jsonl"
        self.family_incident_path.parent.mkdir(parents=True, exist_ok=True)
        self._family_guard_bypass: set[str] = set()
        self._family_ready = True

    def _family_user(self) -> str:
        getter = getattr(self, "_get_current_conversation_user", None)
        return str(getter()) if callable(getter) else str(self.get_user())

    def _family_record(self, payload: dict[str, Any], user: str) -> dict[str, Any]:
        return payload.setdefault("users", {}).setdefault(
            user.casefold(), {"display_name": user, "created_at": datetime.now().isoformat(timespec="seconds")}
        )

    @staticmethod
    def _family_print(message: str) -> None:
        print(); print(message)

    def _clear_everything_pending(self, user: str) -> None:
        confirmations = getattr(self, "confirmations", None)
        if confirmations is not None and hasattr(confirmations, "clear_confirmation"):
            confirmations.clear_confirmation()

        # Estados por usuario de funciones cotidianas.
        states = getattr(self, "_daily_session_state", None)
        if isinstance(states, dict):
            state = states.get(user.casefold())
            if isinstance(state, dict):
                for key in list(state):
                    if key.startswith("pending") or key.startswith("last_draft"):
                        state.pop(key, None)

        # Aclaración tecnológica o contextual.
        clearer = getattr(self, "_clear_pending", None)
        if callable(clearer):
            try:
                clearer(user)
            except Exception:
                pass

        # Juegos y actividades sociales.
        social_clear = getattr(self, "_clear_social_game", None)
        if callable(social_clear):
            social_clear()
        for key in ("_language_session", "_translator_session", "_pending_internet_lookup"):
            if hasattr(self, key):
                try:
                    setattr(self, key, None)
                except Exception:
                    pass

        def mutate(payload: dict[str, Any]) -> None:
            record = self._family_record(payload, user)
            record.pop("pending_action", None)
            record.pop("pending_onboarding", None)
            record.pop("pending_incident_correction", None)
        self.family_readiness_storage.update(mutate)

    def _pending_family_action(self, user: str) -> dict[str, Any] | None:
        record = self.family_readiness_storage.snapshot().get("users", {}).get(user.casefold(), {})
        action = record.get("pending_action")
        if not isinstance(action, dict):
            return None
        try:
            created = datetime.fromisoformat(str(action.get("created_at")))
        except (TypeError, ValueError):
            return None
        if datetime.now() - created > timedelta(minutes=5):
            def mutate(payload: dict[str, Any]) -> None:
                self._family_record(payload, user).pop("pending_action", None)
            self.family_readiness_storage.update(mutate)
            return None
        return action

    def _set_pending_action(self, user: str, action_type: str, original: str, preview: str) -> None:
        def mutate(payload: dict[str, Any]) -> None:
            self._family_record(payload, user)["pending_action"] = {
                "type": action_type,
                "original": original,
                "preview": preview,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        self.family_readiness_storage.update(mutate)

    def _execute_confirmed_action(self, user: str, action: dict[str, Any]) -> bool:
        original = str(action.get("original", "")).strip()
        kind = str(action.get("type", ""))
        self._family_guard_bypass.add(user.casefold())
        try:
            if kind == "interuser":
                handler = getattr(self, "_handle_interuser_request", None)
                return bool(handler and handler(original))
            if kind in {"share_list", "change_reminder"}:
                handler = getattr(self, "_handle_daily_life", None)
                return bool(handler and handler(original))
        finally:
            self._family_guard_bypass.discard(user.casefold())
        return False

    def _handle_pending_family_action(self, text: str, plain: str, user: str) -> bool:
        action = self._pending_family_action(user)
        if action is None:
            return False
        if plain in self._YES:
            def mutate(payload: dict[str, Any]) -> None:
                self._family_record(payload, user).pop("pending_action", None)
            self.family_readiness_storage.update(mutate)
            if not self._execute_confirmed_action(user, action):
                self._family_print("No he podido completar la acción. No se ha enviado ni cambiado nada.")
            return True
        if plain in self._NO:
            def mutate(payload: dict[str, Any]) -> None:
                self._family_record(payload, user).pop("pending_action", None)
            self.family_readiness_storage.update(mutate)
            self._family_print("De acuerdo. No he hecho ningún cambio.")
            return True
        self._family_print(
            f"Tengo pendiente esta acción: {action.get('preview', 'acción sensible')}. "
            "Responde «sí» para confirmarla o «no» para cancelarla."
        )
        return True

    def _handle_onboarding(self, text: str, plain: str, user: str) -> bool:
        snapshot = self.family_readiness_storage.snapshot()
        record = snapshot.get("users", {}).get(user.casefold(), {})
        pending = record.get("pending_onboarding")
        if isinstance(pending, dict):
            preferred = text.strip().strip(".!?")
            if plain in self._CANCEL_ALL:
                self._clear_everything_pending(user)
                self._family_print("De acuerdo. Podemos continuar cuando quieras.")
                return True
            if not preferred or len(preferred.split()) > 5:
                self._family_print("¿Cómo prefieres que te llame? Puede ser tu nombre o un apodo corto.")
                return True
            def mutate(payload: dict[str, Any]) -> None:
                target = self._family_record(payload, user)
                target["preferred_name"] = preferred
                target["onboarded_at"] = datetime.now().isoformat(timespec="seconds")
                target.pop("pending_onboarding", None)
            self.family_readiness_storage.update(mutate)
            self._family_print(
                f"Perfecto, {preferred} 😊 Soy {getattr(self, 'name', 'Daxter')}.\n\n"
                "Puedo ayudarte con recordatorios, listas, preguntas, mensajes familiares, "
                "traducciones y búsquedas cuando me lo pidas.\n\n"
                "Puedes probar con:\n"
                "• Recuérdame mañana que llame al médico.\n"
                "• Añade leche a la lista de la compra.\n"
                "• Dile a Liam que he llegado bien.\n"
                "• ¿Qué tiempo hará mañana?\n\n"
                "Puedo guardar recuerdos en tu perfil, pero te pediré confirmación cuando sea "
                "algo sensible o compartido. Cuando no entienda algo, te preguntaré antes de asumirlo."
            )
            return True

        match = re.search(r"\b(?:hola[, ]+)?soy\s+(.+?)(?:[.!?]|$)", text, re.IGNORECASE)
        if not match:
            return False
        claimed = match.group(1).strip()
        current = user.strip()
        claimed_tokens = set(_plain(claimed).split())
        current_tokens = set(_plain(current).split())
        if current_tokens and claimed_tokens and not (claimed_tokens & current_tokens):
            self._family_print(
                f"Esta cuenta está vinculada a {current}. Decir «soy {claimed}» no cambia la identidad ni los permisos. "
                "¿Está usando otra persona esta cuenta?"
            )
            return True
        def mutate(payload: dict[str, Any]) -> None:
            target = self._family_record(payload, user)
            target["claimed_name"] = claimed
            target["pending_onboarding"] = {"created_at": datetime.now().isoformat(timespec="seconds")}
        self.family_readiness_storage.update(mutate)
        self._family_print(
            f"¡Hola, {claimed}! He comprobado que esta conversación está vinculada al perfil de {current}. "
            f"¿Prefieres que te llame {claimed} o de otra forma?"
        )
        return True

    def _guard_sensitive_action(self, text: str, plain: str, user: str) -> bool:
        if user.casefold() in self._family_guard_bypass:
            return False
        action_type = None
        preview = None
        if re.match(r"^(?:dile|recuerdale|recuérdale|pregunta)\s+a\s+", plain):
            action_type = "interuser"
            preview = f"enviar este mensaje a otra persona: «{text}»"
        elif plain.startswith("comparte la lista"):
            action_type = "share_list"
            preview = f"compartir una lista: «{text}»"
        elif plain.startswith("cambia el recordatorio"):
            action_type = "change_reminder"
            preview = f"cambiar un recordatorio: «{text}»"
        if action_type is None:
            return False
        self._set_pending_action(user, action_type, text, preview)
        self._family_print(f"Voy a {preview}. ¿Lo confirmas?")
        return True

    def _describe_understanding(self, user: str) -> None:
        original = str(getattr(self, "last_original_text", "") or "")
        interpreted = str(getattr(self, "last_interpreted_text", original) or original)
        pending = self._pending_family_action(user)
        if pending:
            self._family_print(
                f"He entendido que quieres {pending.get('preview')}. Estoy esperando tu confirmación antes de hacerlo."
            )
            return
        understanding = getattr(self, "understanding_storage", None)
        if understanding is not None:
            try:
                item = understanding.snapshot().get("users", {}).get(user.casefold(), {}).get("pending_clarification")
            except Exception:
                item = None
            if isinstance(item, dict):
                self._family_print(
                    f"He entendido que necesitas ayuda con: «{item.get('original', original)}». "
                    f"Me falta aclarar esto: {item.get('question', 'necesito un dato más.')}"
                )
                return
        if original and original != interpreted:
            self._family_print(f"Escribiste: «{original}». Lo he interpretado como: «{interpreted}».")
        elif original:
            self._family_print(f"He entendido literalmente: «{original}». Todavía no hay ninguna acción pendiente.")
        else:
            self._family_print("Todavía no tengo un mensaje anterior que pueda explicarte.")

    def _append_incident(self, payload: dict[str, Any]) -> None:
        with self.family_incident_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _handle_incident(self, text: str, plain: str, user: str) -> bool:
        snapshot = self.family_readiness_storage.snapshot()
        pending = snapshot.get("users", {}).get(user.casefold(), {}).get("pending_incident_correction")
        if isinstance(pending, dict):
            incident_id = str(pending.get("incident_id"))
            self._append_incident({
                "incident_id": incident_id,
                "event": "user_correction",
                "user": user,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "correction": text,
            })
            def mutate(payload: dict[str, Any]) -> None:
                self._family_record(payload, user).pop("pending_incident_correction", None)
            self.family_readiness_storage.update(mutate)
            self._family_print("Gracias. He guardado lo que querías decir para poder revisarlo, pero no cambiaré reglas ni recuerdos automáticamente.")
            return True

        markers = ("eso esta mal", "eso está mal", "no era eso", "has entendido mal", "reportar respuesta")
        if not any(marker in plain for marker in map(_plain, markers)):
            return False
        incident_id = datetime.now().strftime("INC-%Y%m%d-%H%M%S-%f")
        self._append_incident({
            "incident_id": incident_id,
            "event": "reported",
            "user": user,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "message_original": getattr(self, "last_original_text", None),
            "message_interpreted": getattr(self, "last_interpreted_text", None),
            "response": None,
            "context": "respuesta reportada desde conversación",
            "type": plain,
        })
        def mutate(payload: dict[str, Any]) -> None:
            self._family_record(payload, user)["pending_incident_correction"] = {
                "incident_id": incident_id,
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        self.family_readiness_storage.update(mutate)
        self._family_print("Gracias. He marcado esta respuesta para revisarla. ¿Qué querías decir realmente?")
        return True

    def _handle_privacy_explanation(self, plain: str, user: str) -> bool:
        if plain.startswith("que datos mios compartes") or plain.startswith("quien puede ver mis datos"):
            self._family_print(
                "Tus datos privados pertenecen a tu perfil. Otros familiares no los ven automáticamente. "
                "Solo se comparte lo que tú autorizas o lo que esté marcado expresamente como familiar. "
                "Los invitados no heredan tus permisos."
            )
            return True
        if re.match(r"^que puede ver\s+", plain):
            person = plain.split("que puede ver", 1)[1].strip() or "esa persona"
            self._family_print(
                f"{person.title()} no puede ver automáticamente tus recuerdos privados. Puede acceder únicamente "
                "a información que hayas compartido con esa persona o con la familia. Para un recuerdo concreto, "
                "pregúntame «¿quién puede ver este recuerdo?»."
            )
            return True
        if plain == "olvida lo que te he dicho hoy":
            self._family_print(
                "No borraré en bloque todo lo de hoy sin enseñártelo antes. Dime qué dato concreto quieres olvidar "
                "o pide «¿qué recuerdas de lo que te he dicho hoy?» para revisarlo."
            )
            return True
        return False

    def _count_errors_today(self) -> int:
        root = Path(__file__).resolve().parents[1]
        today = datetime.now().strftime("%Y-%m-%d")
        total = 0
        for path in (root / "logs").rglob("*.log") if (root / "logs").exists() else ():
            try:
                for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if today in line and any(marker in line.casefold() for marker in ("error", "traceback", "exception", "fallo")):
                        total += 1
            except OSError:
                continue
        return total

    def _telegram_status(self) -> str:
        root = Path(__file__).resolve().parents[1]
        status_path = root / "data" / "integrations" / "telegram" / "supervisor_status.json"
        if not status_path.exists():
            return "sin latido reciente"
        try:
            payload = json.loads(status_path.read_text(encoding="utf-8"))
            heartbeat = datetime.fromisoformat(str(payload.get("heartbeat")))
            age = (datetime.now() - heartbeat).total_seconds()
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return "estado ilegible"
        return "operativo" if age <= 30 and payload.get("state") == "running" else f"sin actividad reciente ({int(age)} s)"

    def _handle_admin_health(self, plain: str, user: str) -> bool:
        markers = (
            "estado de atlas", "funciona ollama", "esta conectado telegram", "está conectado telegram",
            "hay recordatorios pendientes", "ha habido errores hoy",
        )
        if not any(_plain(marker) in plain for marker in markers):
            return False
        if user.casefold() != "liam":
            self._family_print("Ese diagnóstico contiene información técnica y está reservado al propietario de Atlas.")
            return True
        provider = getattr(self, "ai_provider", None)
        try:
            ollama = "disponible" if provider is not None and provider.is_available() else "no disponible"
        except Exception:
            ollama = "error al comprobar"
        telegram = self._telegram_status()
        try:
            pending = len(getattr(self, "_queue")().list_pending(user))
        except Exception:
            pending = 0
        errors = self._count_errors_today()
        self._family_print(
            "Estado de Atlas\n\n"
            f"Telegram: {telegram}\n"
            f"Ollama: {ollama}\n"
            "Internet: no comprobado; Atlas no hace búsquedas automáticas\n"
            f"Errores registrados hoy: {errors}\n"
            f"Recordatorios pendientes de Liam: {pending}\n\n"
            "Si Ollama no está disponible, recordatorios, listas, mensajes y otras funciones deterministas pueden seguir funcionando."
        )
        return True

    def _handle_family_readiness(self, text: str) -> bool:
        self._family_bootstrap()
        text = " ".join(text.strip().split())
        plain = _plain(text)
        user = self._family_user()

        # Cancelación universal antes de cualquier confirmación del núcleo.
        if plain in {_plain(item) for item in self._CANCEL_ALL}:
            self._clear_everything_pending(user)
            self._family_print("De acuerdo. He cancelado lo que estábamos haciendo. ¿En qué te ayudo ahora?")
            return True

        if self._handle_pending_family_action(text, plain, user):
            return True
        if self._handle_onboarding(text, plain, user):
            return True
        if plain in {"que has entendido", "que entendiste", "dime que has entendido"}:
            self._describe_understanding(user)
            return True
        if self._handle_incident(text, plain, user):
            return True
        if self._handle_privacy_explanation(plain, user):
            return True
        if self._handle_admin_health(plain, user):
            return True
        if self._guard_sensitive_action(text, plain, user):
            return True
        return False
