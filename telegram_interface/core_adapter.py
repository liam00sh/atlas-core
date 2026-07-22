"""Único puente permitido entre Telegram y el núcleo normal de Atlas."""

from __future__ import annotations

from contextlib import redirect_stdout
from difflib import SequenceMatcher
from io import StringIO
import re
import threading
import unicodedata
from typing import Protocol

from ai.context.context_manager import AIContextManager
from telegram_interface.models import TelegramRequestContext


class AtlasCoreProtocol(Protocol):
    def get_user(self) -> str: ...
    def change_user(self, user: str) -> bool: ...
    def process(self, text: str) -> bool: ...


class AtlasCoreAdapter:
    """Serializa el núcleo mutable y conserva el interlocutor de cada chat."""

    _IDENTITY_STOP_WORDS = {
        "que", "qué", "quien", "quién", "como", "cómo", "cuando", "cuándo",
        "donde", "dónde", "cual", "cuál", "cuanto", "cuánto", "sabes", "conoces",
        "dime", "cuentame", "cuéntame", "te", "me", "es", "el", "la", "los", "las",
        "puedes", "podrias", "podrías", "quiero", "necesito", "y", "pero",
    }
    _SAFE_WORDS = {
        "con", "quien", "quién", "vive", "viven", "casa", "donde", "dónde", "de",
        "soy", "estoy", "esta", "está", "estas", "estás", "saluda", "saludala", "salúdala", "saludalo",
        "salúdalo", "que", "qué", "sabes", "mi", "modo", "normal", "actual", "hablo",
        "hablando", "eres", "somos", "tengo", "tiene", "tienen", "cuantos", "cuántos",
        "cuantas", "cuántas", "primos", "primas", "edad", "años", "cumpleaños", "nacio",
        "nació", "fecha", "nacimiento", "recuerda", "dile", "avisa", "vaya", "cortarse",
        "posible", "puede", "puedo", "persona", "perfil", "volver", "vuelto", "nuevo",
    }
    _VISIBILITY_LABEL_RE = re.compile(
        r"\s*\[(?:cualquier persona|personas? de confianza|familia|pareja|privad[oa])\]\s*",
        re.IGNORECASE,
    )

    def __init__(self, atlas: AtlasCoreProtocol) -> None:
        self.atlas = atlas
        self._lock = threading.RLock()
        self._confirmation_states: dict[str, object] = {}
        self._legacy_memory_states: dict[str, object] = {}
        self._ai_context_states: dict[str, AIContextManager] = {}
        # La identidad conversacional no altera autenticación, permisos ni datos.
        self._temporary_speakers: dict[str, str] = {}

    @staticmethod
    def _plain(text: str) -> str:
        value = unicodedata.normalize("NFKD", str(text).casefold())
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        return re.sub(r"\s+", " ", value).strip()

    @classmethod
    def _correct_typing(cls, text: str) -> str:
        """Corrige erratas conservadoras sin tocar nombres ni contenido libre.

        Solo sustituye palabras funcionales cercanas a un vocabulario de intención.
        Evita convertir nombres, matrículas, códigos o palabras largas desconocidas.
        """
        tokens = re.findall(r"\w+|[^\w\s]+|\s+", text, re.UNICODE)
        corrected: list[str] = []
        for token in tokens:
            plain = cls._plain(token)
            if not plain or not token.isalpha() or len(plain) < 2:
                corrected.append(token)
                continue
            if plain in {cls._plain(word) for word in cls._SAFE_WORDS}:
                corrected.append(token)
                continue
            candidates: list[tuple[float, str]] = []
            for word in cls._SAFE_WORDS:
                candidate = cls._plain(word)
                if abs(len(candidate) - len(plain)) > 1:
                    continue
                score = SequenceMatcher(None, plain, candidate).ratio()
                if score >= (0.66 if len(plain) <= 3 else 0.80 if len(plain) <= 4 else 0.85):
                    candidates.append((score, word))
            if not candidates:
                corrected.append(token)
                continue
            candidates.sort(reverse=True)
            replacement = candidates[0][1]
            corrected.append(replacement)
        return "".join(corrected)

    @classmethod
    def _parse_identity_declaration(cls, text: str) -> tuple[str, str] | None:
        match = re.match(r"^\s*soy\s+(.+?)\s*$", text, re.IGNORECASE)
        if not match:
            return None
        tail = match.group(1).strip()
        # La coma y los signos separan inequívocamente nombre y consulta.
        punctuation = re.match(r"^([^,;.!?¿¡]+?)\s*[,;.!?¿¡]+\s*(.*)$", tail)
        if punctuation:
            return punctuation.group(1).strip(), punctuation.group(2).strip()
        words = tail.split()
        for index, word in enumerate(words[1:], start=1):
            if cls._plain(word) in {cls._plain(item) for item in cls._IDENTITY_STOP_WORDS}:
                return " ".join(words[:index]).strip(), " ".join(words[index:]).strip()
        return tail, ""

    def _find_person(self, name: str):
        manager = getattr(self.atlas, "people_manager", None)
        finder = getattr(manager, "find_person_by_name", None)
        return finder(name) if callable(finder) else None

    def _resolve_temporary_speaker(self, name: str) -> tuple[str, bool]:
        clean = " ".join(name.strip(" .,!¡!¿?").split())[:80]
        person = self._find_person(clean)
        if person is not None:
            display = getattr(person, "preferred_name", None) or getattr(person, "nickname", None)
            return str(display or person.name), True
        return clean.title(), False

    @staticmethod
    def _short_name(name: str) -> str:
        words = str(name).strip().split()
        if not words:
            return ""
        # Conserva nombres compuestos frecuentes; para el resto usa el nombre cotidiano.
        if len(words) >= 2 and words[0].casefold() in {"jose", "josé", "maria", "maría"}:
            return " ".join(words[:2])
        return words[0]

    def _meta_response(self, text: str, context: TelegramRequestContext) -> str | None:
        normalized = self._plain(text).strip(" ?!¡¿.")
        speaker = self._temporary_speakers.get(context.session_id)
        authenticated = context.atlas_user_id

        if normalized in {"quien soy", "quien soy yo", "como me llamo", "cual es mi nombre"}:
            if speaker:
                return f"Ahora mismo estoy hablando con {self._short_name(speaker)}. La cuenta de Telegram sigue siendo de {authenticated}."
            # Respuesta determinista equivalente al núcleo para evitar que el
            # adaptador devuelva un error vacío en Telegram.
            name = self._short_name(authenticated).title()
            return f"Eres {name}. El perfil encaja, la misión continúa y nadie ha perdido los pantalones."

        if normalized in {"con quien hablo", "con quien estoy hablando", "quien habla conmigo"}:
            identity = getattr(self.atlas, "identity_manager", None)
            getter = getattr(identity, "get_active_display_name", None)
            assistant = getter() if callable(getter) else "Atlas"
            return f"Estás hablando conmigo, {assistant}."

        if normalized in {"con quien estas hablando", "con quien hablas", "quien esta hablando"}:
            current = self._short_name(speaker or authenticated)
            return f"Estoy hablando con {current}."

        if normalized in {"en que modo estas", "que modo tienes", "cual es tu modo", "modo actual"}:
            identity = getattr(self.atlas, "identity_manager", None)
            getter = getattr(identity, "get_active_mode_label", None)
            if not callable(getter):
                getter = getattr(identity, "get_active_mode_name", None)
            mode = getter() if callable(getter) else "normal"
            return f"Ahora mismo estoy en modo {str(mode).casefold()}."

        return None

    def _presence_greeting(self, text: str) -> str | None:
        match = re.search(
            r"(?:estoy|estamos)\s+con\s+(?:mi\s+\w+\s+)?([A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ -]{0,60})\s*[,;]?\s*(?:saluda(?:la|lo)?|saludála|salúdala|salúdalo|saludale|salúdale|dile hola)",
            text,
            re.IGNORECASE,
        )
        if not match:
            return None
        raw_name = " ".join(match.group(1).split())
        first = self._short_name(raw_name)
        known = self._find_person(raw_name) or self._find_person(first)
        if known is not None:
            known_name = self._short_name(getattr(known, "name", raw_name))
            return (
                f"¡Hola, {first}! Encantado de saludarte 👋\n"
                f"¿Eres {known_name} de la familia o eres otra persona que también se llama {first}?"
            )
        return f"¡Hola, {first}! Encantado de saludarte 👋"

    @classmethod
    def _clean_response(cls, response: str) -> str:
        cleaned = cls._VISIBILITY_LABEL_RE.sub(" ", response)
        cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
        cleaned = re.sub(r" {2,}", " ", cleaned)
        return cleaned.strip()


    @classmethod
    def quick_response(cls, text: str, personality: str = "Daxter") -> str | None:
        """Respuestas deterministas que no necesitan bloquear Atlas Core."""
        normalized = cls._plain(text).strip(" ?!¡¿.,;:")
        name = str(personality or "Daxter")
        if normalized in {"hola", "buenas", "buenas tardes"}:
            return "¡Hola! 😊 ¿En qué te ayudo?"
        if normalized in {"como estas", "que tal"}:
            return "Estoy bien y operativo 🙂 ¿Cómo estás tú?"
        if normalized in {"gracias", "muchas gracias"}:
            return "De nada 😊"
        if normalized in {"vale", "ok", "de acuerdo", "perfecto"}:
            return "Perfecto 👍"
        if normalized in {"adios", "hasta luego"}:
            return "¡Hasta luego! 👋"
        return None

    def process(self, text: str, context: TelegramRequestContext) -> str:
        if context.atlas_user_id is None or context.authentication_state != "linked":
            raise PermissionError("La cuenta Telegram no está vinculada.")

        quick = self.quick_response(text, context.active_personality or "Daxter")
        if quick is not None:
            return quick

        with self._lock:
            corrected_text = self._correct_typing(text)
            plain_text = self._plain(corrected_text)

            # Saludos de disponibilidad habituales.
            if plain_text.strip(" ?!¡¿.") in {"estas", "sigues ahi", "andas por ahi"}:
                return "Sí, estoy aquí y operativo 🙂"

            presence = self._presence_greeting(corrected_text)
            if presence:
                return presence

            parsed_identity = self._parse_identity_declaration(corrected_text)
            identity_intro = ""
            if parsed_identity:
                declared_name, remainder = parsed_identity
                speaker, known = self._resolve_temporary_speaker(declared_name)
                if self._plain(speaker) == self._plain(context.atlas_user_id):
                    self._temporary_speakers.pop(context.session_id, None)
                    if not remainder:
                        return f"Perfecto, vuelvo a hablar contigo como {context.atlas_user_id}."
                else:
                    self._temporary_speakers[context.session_id] = speaker
                    short = self._short_name(speaker)
                    identity_intro = (
                        f"Perfecto, {short}. Mientras sigas hablando, te trataré como interlocutor de esta conversación. "
                        f"La cuenta y los permisos siguen siendo de {context.atlas_user_id}."
                    )
                    if not known and len(declared_name.split()) > 1 and not remainder:
                        return identity_intro + f" ¿Cómo prefieres que te llame, {short} u otro apodo?"
                    if not remainder:
                        return identity_intro
                corrected_text = remainder or corrected_text
                plain_text = self._plain(corrected_text)

            if plain_text in {
                "volver al usuario principal", "volver al perfil principal", "terminar invitado",
                "terminar conversacion temporal", "soy yo de nuevo", "estoy de vuelta",
                "he vuelto", "ya estoy yo",
            }:
                self._temporary_speakers.pop(context.session_id, None)
                return f"Perfecto, vuelvo a hablar contigo como {context.atlas_user_id}."

            meta = self._meta_response(corrected_text, context)
            if meta:
                return f"{identity_intro}\n{meta}".strip() if identity_intro else meta

            previous_user = self.atlas.get_user()
            previous_session = getattr(self.atlas, "session_id", None)
            previous_request_context = getattr(self.atlas, "channel_request_context", None)
            previous_temporary_speaker = getattr(self.atlas, "channel_temporary_speaker", None)
            confirmations = getattr(self.atlas, "confirmations", None)
            memory_service = getattr(self.atlas, "memory_service", None)
            previous_confirmation = getattr(confirmations, "pending_confirmation", None)
            previous_pending_memory = getattr(memory_service, "pending_memory", None)
            if confirmations is not None:
                confirmations.pending_confirmation = None
            if memory_service is not None:
                memory_service.pending_memory = None
            output = StringIO()
            target_ai_key = context.atlas_user_id.strip().casefold()
            previous_ai_context = None
            try:
                if previous_user.casefold() != context.atlas_user_id.casefold():
                    if not self.atlas.change_user(context.atlas_user_id):
                        raise PermissionError("No se pudo activar el usuario autenticado.")
                setattr(self.atlas, "session_id", context.session_id)
                setattr(self.atlas, "channel_request_context", context)
                temporary_speaker = self._temporary_speakers.get(context.session_id)
                if temporary_speaker:
                    setattr(self.atlas, "channel_temporary_speaker", temporary_speaker)
                elif hasattr(self.atlas, "channel_temporary_speaker"):
                    delattr(self.atlas, "channel_temporary_speaker")
                if confirmations is not None:
                    confirmations.pending_confirmation = self._confirmation_states.get(context.session_id)
                if memory_service is not None:
                    memory_service.pending_memory = self._legacy_memory_states.get(context.session_id)
                ai_contexts = getattr(self.atlas, "ai_contexts", None)
                if isinstance(ai_contexts, dict):
                    previous_ai_context = ai_contexts.get(target_ai_key)
                    ai_contexts[target_ai_key] = self._ai_context_states.setdefault(
                        context.session_id,
                        AIContextManager(max_messages=getattr(self.atlas, "ai_context_max_messages", 10)),
                    )
                with redirect_stdout(output):
                    self.atlas.process(corrected_text)
            finally:
                if confirmations is not None:
                    self._confirmation_states[context.session_id] = confirmations.pending_confirmation
                    confirmations.pending_confirmation = None
                if memory_service is not None:
                    self._legacy_memory_states[context.session_id] = memory_service.pending_memory
                    memory_service.pending_memory = None
                ai_contexts = getattr(self.atlas, "ai_contexts", None)
                if isinstance(ai_contexts, dict):
                    current = ai_contexts.get(target_ai_key)
                    if isinstance(current, AIContextManager):
                        self._ai_context_states[context.session_id] = current
                    if previous_ai_context is None:
                        ai_contexts.pop(target_ai_key, None)
                    else:
                        ai_contexts[target_ai_key] = previous_ai_context
                setattr(self.atlas, "session_id", previous_session)
                setattr(self.atlas, "channel_request_context", previous_request_context)
                if previous_temporary_speaker is None:
                    if hasattr(self.atlas, "channel_temporary_speaker"):
                        delattr(self.atlas, "channel_temporary_speaker")
                else:
                    setattr(self.atlas, "channel_temporary_speaker", previous_temporary_speaker)
                if self.atlas.get_user().casefold() != previous_user.casefold():
                    self.atlas.change_user(previous_user)
                if confirmations is not None:
                    confirmations.pending_confirmation = previous_confirmation
                if memory_service is not None:
                    memory_service.pending_memory = previous_pending_memory

            response = self._clean_response(output.getvalue().strip())
            adapter = getattr(self.atlas, "adapt_response_for_profile", None)
            if callable(adapter) and response:
                response = self._clean_response(adapter(response, context.atlas_user_id))
            if identity_intro:
                return self._clean_response(f"{identity_intro}\n{response}") if response else identity_intro
            return response or "Atlas no ha generado una respuesta."

    def active_personality(self, atlas_user_id: str) -> str:
        with self._lock:
            previous_user = self.atlas.get_user()
            try:
                if previous_user.casefold() != atlas_user_id.casefold():
                    self.atlas.change_user(atlas_user_id)
                return self.atlas.identity_manager.get_active_identity_name()
            finally:
                if self.atlas.get_user().casefold() != previous_user.casefold():
                    self.atlas.change_user(previous_user)

    def change_personality(self, atlas_user_id: str, personality: str) -> bool:
        with self._lock:
            previous_user = self.atlas.get_user()
            try:
                if previous_user.casefold() != atlas_user_id.casefold():
                    if not self.atlas.change_user(atlas_user_id):
                        return False
                return self.atlas.identity_manager.change_identity(personality, save_preference=True)
            finally:
                if self.atlas.get_user().casefold() != previous_user.casefold():
                    self.atlas.change_user(previous_user)


class CallableCoreAdapter:
    """Adaptador pequeño para pruebas y otros núcleos compatibles."""

    def __init__(self, handler, personality_getter=None, personality_setter=None) -> None:
        self.handler = handler
        self.personality_getter = personality_getter or (lambda _user: "daxter")
        self.personality_setter = personality_setter or (lambda _user, _value: True)

    def process(self, text: str, context: TelegramRequestContext) -> str:
        return self.handler(text, context)

    def active_personality(self, atlas_user_id: str) -> str:
        return self.personality_getter(atlas_user_id)

    def change_personality(self, atlas_user_id: str, personality: str) -> bool:
        return bool(self.personality_setter(atlas_user_id, personality))
