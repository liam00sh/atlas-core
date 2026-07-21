"""Funciones cotidianas y gestión conversacional segura de Atlas.

Incluye normalización tolerante, recordatorios personales, listas, cálculos,
redacción, ayuda cotidiana y gestión conversacional de memoria.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from difflib import SequenceMatcher
import ast
import json
import operator
import os
from pathlib import Path
import re
import threading
from typing import Any, Callable
import unicodedata
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram_interface.interuser_delivery import InteruserRequest, TelegramDeliveryQueue


@dataclass(frozen=True, slots=True)
class Interpretation:
    original: str
    interpreted: str
    corrections: tuple[tuple[str, str, float], ...]


FUNCTION_WORDS = {
    "a", "al", "algo", "anade", "añade", "archiva", "avisa", "avisame",
    "avísame", "busca", "cambia", "cancela", "como", "cómo", "con", "corrige",
    "cuando", "cuándo", "cuanto", "cuánto", "cuantos", "cuántos", "de", "del",
    "dile", "dime", "donde", "dónde", "el", "ella", "en", "es", "esta", "está",
    "estas", "estás", "esto", "haz", "hoy", "la", "las", "le", "lo", "los",
    "manana", "mañana", "me", "mi", "mis", "no", "olvida", "para", "por",
    "pregunta", "puede", "puedes", "que", "qué", "quien", "quién", "quienes",
    "recuerda", "recuerdame", "recuérdame", "recupera", "responde", "responder",
    "si", "sí", "sobre", "te", "tengo", "tiene", "todo", "un", "una", "vive",
    "viven", "y", "yo",
}

COMMON = {
    "com": "con",
    "qe": "que",
    "q": "que",
    "k": "que",
    "dnde": "donde",
    "dnd": "donde",
    "kien": "quien",
    "kienes": "quienes",
    "recuerdame": "recuérdame",
    "avisame": "avísame",
    "manana": "mañana",
    "ppsible": "posible",
    "posble": "posible",
    "tngo": "tengo",
    "tienees": "tienes",
}

TOKEN_RE = re.compile(r"\w+|[^\w\s]+|\s+", re.UNICODE)


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold())
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _score(left: str, right: str) -> float:
    return SequenceMatcher(None, _fold(left), _fold(right)).ratio()


def interpret_text(text: str) -> Interpretation:
    tokens = TOKEN_RE.findall(text)
    corrections: list[tuple[str, str, float]] = []
    word_positions = [i for i, token in enumerate(tokens) if token.isalpha()]

    for index in word_positions:
        token = tokens[index]
        folded = _fold(token)
        # Los nombres propios no se tocan, salvo la primera palabra cuando hay
        # un error común inequívoco como "Com quien...".
        is_capitalized = token[:1].isupper()
        first_word = index == word_positions[0]
        replacement = COMMON.get(folded)

        # Corrección contextual de "pam" -> "pan" solo alrededor de comprar.
        if folded == "pam":
            nearby = " ".join(_fold(tokens[pos]) for pos in word_positions if abs(pos - index) <= 4)
            if any(item in nearby for item in ("compr", "anade", "lista")):
                replacement = "pan"

        if replacement is None and (not is_capitalized or first_word):
            candidates = sorted(
                ((candidate, _score(folded, candidate)) for candidate in FUNCTION_WORDS),
                key=lambda item: item[1],
                reverse=True,
            )
            if candidates and candidates[0][1] >= 0.90:
                replacement = candidates[0][0]

        if replacement and _fold(replacement) != folded:
            if token[:1].isupper():
                replacement = replacement[:1].upper() + replacement[1:]
            confidence = max(_score(token, replacement), 0.95 if folded in COMMON else 0.0)
            tokens[index] = replacement
            corrections.append((token, replacement, confidence))

    return Interpretation(text, "".join(tokens), tuple(corrections))


class DailyLifeStorage:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self._data = self._load()

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {"version": 1, "users": {}}

    def _load(self) -> dict[str, Any]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            return self._empty()
        return raw if isinstance(raw, dict) and isinstance(raw.get("users"), dict) else self._empty()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            self._data = self._load()
            return deepcopy(self._data)

    def update(self, mutator: Callable[[dict[str, Any]], Any]) -> Any:
        with self._lock:
            self._data = self._load()
            result = mutator(self._data)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(self.path.suffix + ".tmp")
            with temporary.open("w", encoding="utf-8", newline="\n") as stream:
                json.dump(self._data, stream, ensure_ascii=False, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            return result


class PersonalListService:
    def __init__(self, storage: DailyLifeStorage) -> None:
        self.storage = storage

    @staticmethod
    def normalize_name(name: str) -> str:
        clean = " ".join(name.strip().casefold().split())
        clean = re.sub(r"^(?:la|el)\s+", "", clean)
        return clean or "compra"

    def create(self, owner: str, name: str) -> bool:
        list_name = self.normalize_name(name)
        def mutate(data: dict[str, Any]) -> bool:
            user = data.setdefault("users", {}).setdefault(owner.casefold(), {"display_name": owner, "lists": {}})
            lists = user.setdefault("lists", {})
            if list_name in lists:
                return False
            lists[list_name] = {"name": list_name, "items": [], "updated_at": datetime.now().isoformat(timespec="seconds")}
            return True
        return bool(self.storage.update(mutate))

    def add(self, owner: str, list_name: str, items: list[str]) -> list[str]:
        name = self.normalize_name(list_name)
        clean_items = [" ".join(item.strip().split()) for item in items if item.strip()]
        def mutate(data: dict[str, Any]) -> list[str]:
            user = data.setdefault("users", {}).setdefault(owner.casefold(), {"display_name": owner, "lists": {}})
            record = user.setdefault("lists", {}).setdefault(name, {"name": name, "items": [], "updated_at": None})
            current = record.setdefault("items", [])
            added = []
            existing = {str(item.get("text", "")).casefold() for item in current if isinstance(item, dict)}
            for item in clean_items:
                if item.casefold() in existing:
                    continue
                current.append({"text": item, "done": False})
                existing.add(item.casefold())
                added.append(item)
            record["updated_at"] = datetime.now().isoformat(timespec="seconds")
            return added
        return list(self.storage.update(mutate))

    def remove(self, owner: str, list_name: str, item_text: str) -> bool:
        name = self.normalize_name(list_name)
        expected = item_text.strip().casefold()
        def mutate(data: dict[str, Any]) -> bool:
            record = data.get("users", {}).get(owner.casefold(), {}).get("lists", {}).get(name)
            if not isinstance(record, dict):
                return False
            items = record.get("items", [])
            before = len(items)
            record["items"] = [item for item in items if str(item.get("text", "")).casefold() != expected]
            record["updated_at"] = datetime.now().isoformat(timespec="seconds")
            return len(record["items"]) != before
        return bool(self.storage.update(mutate))

    def get(self, owner: str, list_name: str) -> dict[str, Any] | None:
        name = self.normalize_name(list_name)
        return self.storage.snapshot().get("users", {}).get(owner.casefold(), {}).get("lists", {}).get(name)

    def names(self, owner: str) -> list[str]:
        lists = self.storage.snapshot().get("users", {}).get(owner.casefold(), {}).get("lists", {})
        return sorted(str(name) for name in lists)


@dataclass(frozen=True, slots=True)
class PersonalReminder:
    message: str
    due_at_utc: datetime


class PersonalReminderParser:
    def __init__(self, timezone_name: str = "Europe/Madrid") -> None:
        try:
            self.timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            self.timezone = timezone.utc

    @staticmethod
    def plain(text: str) -> str:
        normalized = unicodedata.normalize("NFD", text.casefold())
        return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")

    def parse(self, text: str, now: datetime | None = None) -> PersonalReminder | None:
        original = " ".join(text.strip().split())
        plain = self.plain(original)
        if not re.match(r"^(?:recuerdame|avisame)\b", plain):
            return None
        tail_original = re.sub(r"^(?:recuérdame|recuerdame|avísame|avisame)\s+", "", original, flags=re.I)
        tail_plain = self.plain(tail_original)
        current = now or datetime.now(self.timezone)
        if current.tzinfo is None:
            current = current.replace(tzinfo=self.timezone)
        else:
            current = current.astimezone(self.timezone)

        relative = re.match(r"^dentro\s+de\s+(\d+)\s+(minutos?|horas?|dias?)\s+(?:de\s+)?(?:que\s+)?(.+)$", tail_plain)
        if relative:
            amount = int(relative.group(1))
            unit = relative.group(2)
            body = tail_original[relative.start(3):].strip()
            delta = timedelta(minutes=amount) if unit.startswith("minuto") else timedelta(hours=amount) if unit.startswith("hora") else timedelta(days=amount)
            return PersonalReminder(body[:1500], (current + delta).astimezone(UTC))

        absolute = re.match(
            r"^(?:(hoy|manana)\s+)?(?:a\s+)?(?:las\s+)?([0-2]?\d)(?::([0-5]\d))?\s*(?:h|horas?)?\s+(?:de\s+)?(?:que\s+)?(.+)$",
            tail_plain,
        )
        if not absolute:
            return None
        day_word, hour_text, minute_text, _ = absolute.groups()
        hour = int(hour_text)
        if hour > 23:
            return None
        minute = int(minute_text or 0)
        body = tail_original[absolute.start(4):].strip()
        due_date = current.date() + (timedelta(days=1) if day_word == "manana" else timedelta())
        due = datetime.combine(due_date, datetime.min.time(), tzinfo=self.timezone).replace(hour=hour, minute=minute)
        if day_word != "hoy" and due <= current:
            due += timedelta(days=1)
        if day_word == "hoy" and due <= current:
            return None
        return PersonalReminder(body[:1500], due.astimezone(UTC))


OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _eval(node):
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        return OPS[type(node.op)](_eval(node.left), _eval(node.right))
    raise ValueError("Expresión no permitida")


def calculate_from_text(text: str) -> str | None:
    plain = " ".join(text.casefold().replace(",", ".").split())
    discount = re.search(r"(?:cuesta|vale)\s+(\d+(?:\.\d+)?)\s*(?:€|euros?)?.*?(\d+(?:\.\d+)?)\s*%\s+de\s+descuento", plain)
    if discount:
        price, percent = map(float, discount.groups())
        result = price * (1 - percent / 100)
        return f"Con un {percent:g} % de descuento, se queda en {result:.2f} €.".replace(".", ",")

    glasses = re.search(r"cu[aá]ntos?\s+mililitros\s+son\s+(\d+(?:\.\d+)?)\s+vasos?", plain)
    if glasses:
        count = float(glasses.group(1))
        ml = count * 250
        return f"Tomando un vaso estándar de 250 ml, son aproximadamente {ml:g} ml."

    expression = plain
    number_words = {
        "cero": "0", "uno": "1", "una": "1", "dos": "2", "tres": "3",
        "cuatro": "4", "cinco": "5", "seis": "6", "siete": "7",
        "ocho": "8", "nueve": "9", "diez": "10",
    }
    for word, digit in number_words.items():
        expression = re.sub(rf"\b{word}\b", digit, expression)
    replacements = {
        "cuanto son": "", "cuánto son": "", "cuanto es": "", "cuánto es": "",
        "euros": "", "euro": "", "entre": "/", "por": "*", "mas": "+", "más": "+", "menos": "-",
    }
    for source, target in replacements.items():
        expression = expression.replace(source, target)
    expression = re.sub(r"[^0-9.+\-*/() ]", "", expression).strip()
    if not expression or not any(op in expression for op in "+-*/"):
        return None
    try:
        value = _eval(ast.parse(expression, mode="eval"))
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError):
        return None
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return f"El resultado es {value}."


class AtlasDailyMixin:
    """Añade recordatorios, listas, ayuda cotidiana y memoria conversacional."""

    def _daily_bootstrap(self) -> None:
        if getattr(self, "_daily_ready", False):
            return
        root = Path(__file__).resolve().parents[1]
        self.daily_storage = DailyLifeStorage(root / "data" / "daily_life" / "state.json")
        self.personal_lists = PersonalListService(self.daily_storage)
        self.personal_reminder_parser = PersonalReminderParser("Europe/Madrid")
        self._daily_session_state: dict[str, dict] = {}
        self._daily_ready = True

    def _conversation_user(self) -> str:
        getter = getattr(self, "_get_current_conversation_user", None)
        if callable(getter):
            return str(getter())
        return str(self.get_user())

    def _daily_state_for(self, owner: str | None = None) -> dict:
        self._daily_bootstrap()
        key = (owner or self._conversation_user()).casefold()
        return self._daily_session_state.setdefault(key, {})

    def _interpret_user_text(self, text: str) -> str:
        """Corrige solo errores de alta confianza y conserva el original."""
        self._daily_bootstrap()
        interpretation = interpret_text(text)
        self.last_original_text = interpretation.original
        self.last_interpreted_text = interpretation.interpreted
        self.last_typing_corrections = interpretation.corrections
        return interpretation.interpreted

    @staticmethod
    def _plain(text: str) -> str:
        normalized = unicodedata.normalize("NFD", text.casefold())
        return " ".join(
            "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn" and (ch.isalnum() or ch.isspace()))
            .split()
        )

    def _print(self, text: str) -> None:
        print()
        print(text)

    def _handle_daily_life(self, original_text: str) -> bool:
        self._daily_bootstrap()
        text = " ".join(original_text.strip().split())
        plain = self._plain(text)
        owner = self._conversation_user()
        state = self._daily_state_for(owner)

        if self._handle_daily_pending(text, plain, owner, state):
            return True
        if self._handle_agenda_summary(text, plain, owner):
            return True
        if self._handle_personal_reminders(text, plain, owner, state):
            return True
        if self._handle_object_locations(text, plain, owner):
            return True
        if self._handle_routines(text, plain, owner):
            return True
        if self._handle_lists(text, plain, owner, state):
            return True
        if self._handle_linked_reply(text, plain, owner):
            return True
        if self._handle_memory_conversation(text, plain, owner, state):
            return True
        if self._handle_message_help(text, plain, owner, state):
            return True
        result = calculate_from_text(text)
        if result is not None:
            self._print(result)
            return True
        if self._handle_cooking_and_explanations(text, plain):
            return True
        if self._handle_everyday_help(text, plain):
            return True
        return False


    # ------------------------------------------------------------------
    # Agenda resumida
    # ------------------------------------------------------------------
    def _handle_agenda_summary(self, text: str, plain: str, owner: str) -> bool:
        markers = (
            "que tengo pendiente", "que me queda por hacer hoy",
            "tengo algo programado esta tarde", "que recordatorios vencen hoy",
            "resumeme el dia", "resumen de hoy",
        )
        if not any(marker in plain for marker in markers):
            return False
        queue = self._queue()
        now = datetime.now(self.personal_reminder_parser.timezone)
        pending = []
        for item in queue.list_pending(owner):
            if str(item.get("target_user_id", "")).casefold() != owner.casefold():
                continue
            try:
                due = datetime.fromisoformat(str(item.get("due_at_utc", ""))).astimezone(self.personal_reminder_parser.timezone)
            except (ValueError, TypeError):
                continue
            if due.date() == now.date():
                if "esta tarde" in plain and not (14 <= due.hour < 21):
                    continue
                pending.append((due, str(item.get("message", "Recordatorio"))))
        if not pending:
            self._print("No tienes nada pendiente para ese periodo.")
            return True
        pending.sort(key=lambda row: row[0])
        lines = ["Para hoy tienes esto pendiente:"]
        lines.extend(f"{due:%H:%M} — {message}" for due, message in pending)
        self._print("\n\n".join(lines))
        return True

    # ------------------------------------------------------------------
    # Lugares donde se dejan objetos
    # ------------------------------------------------------------------
    def _handle_object_locations(self, text: str, plain: str, owner: str) -> bool:
        save = re.match(
            r"^(?:guarda|recuerda|apunta)(?:\s+que)?\s+(?:he\s+)?dejado\s+(?:el|la|los|las)?\s*(.+?)\s+en\s+(.+)$",
            plain,
        )
        if save:
            obj, place = save.group(1).strip(), save.group(2).strip()
            def mutate(data: dict[str, Any]) -> None:
                user = data.setdefault("users", {}).setdefault(owner.casefold(), {"display_name": owner})
                locations = user.setdefault("object_locations", {})
                locations[obj] = {
                    "object": obj,
                    "place": place,
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                }
            self.daily_storage.update(mutate)
            self._print(f"Lo guardo. Has dejado {obj} en {place}.")
            return True
        query = re.match(r"^(?:donde\s+(?:deje|guarde)|donde\s+esta)\s+(?:el|la|los|las)?\s*(.+)$", plain)
        if query:
            wanted = query.group(1).strip()
            locations = self.daily_storage.snapshot().get("users", {}).get(owner.casefold(), {}).get("object_locations", {})
            best = None
            best_score = 0.0
            for key, record in locations.items():
                score = _score(wanted, key)
                if score > best_score:
                    best, best_score = record, score
            if not best or best_score < 0.62:
                self._print(f"No recuerdo todavía dónde dejaste {wanted}.")
            else:
                self._print(f"Me dijiste que dejaste {best['object']} en {best['place']}.")
            return True
        return False

    # ------------------------------------------------------------------
    # Rutinas sencillas
    # ------------------------------------------------------------------
    def _handle_routines(self, text: str, plain: str, owner: str) -> bool:
        create = re.match(r"^(?:crea|anade|añade)\s+(?:una\s+)?rutina\s+(?:diaria\s+)?(?:para|de)?\s*(.+)$", plain)
        if create:
            task = create.group(1).strip()
            def mutate(data: dict[str, Any]) -> None:
                user = data.setdefault("users", {}).setdefault(owner.casefold(), {"display_name": owner})
                routines = user.setdefault("routines", {})
                routines[task] = {"task": task, "frequency": "daily", "completed_dates": []}
            self.daily_storage.update(mutate)
            self._print(f"He añadido la rutina diaria de {task}.")
            return True
        done = re.match(r"^(?:ya\s+)?(?:he\s+)?(?:hecho|tomado|regado|sacado|marcado)\s+(.+)$", plain)
        if done:
            phrase = done.group(1).strip()
            data = self.daily_storage.snapshot()
            routines = data.get("users", {}).get(owner.casefold(), {}).get("routines", {})
            candidate = max(routines, key=lambda key: _score(phrase, key), default=None)
            if candidate and _score(phrase, candidate) >= 0.55:
                today = datetime.now().date().isoformat()
                def mutate(payload: dict[str, Any]) -> None:
                    routine = payload["users"][owner.casefold()]["routines"][candidate]
                    dates = routine.setdefault("completed_dates", [])
                    if today not in dates:
                        dates.append(today)
                self.daily_storage.update(mutate)
                self._print(f"Perfecto. He marcado {candidate} como hecho hoy.")
                return True
        if any(marker in plain for marker in ("que rutinas tengo", "que me falta de la rutina", "he hecho la medicacion hoy", "he tomado la medicacion hoy")):
            routines = self.daily_storage.snapshot().get("users", {}).get(owner.casefold(), {}).get("routines", {})
            if not routines:
                self._print("Todavía no tienes rutinas guardadas.")
                return True
            today = datetime.now().date().isoformat()
            lines = []
            for record in routines.values():
                completed = today in record.get("completed_dates", [])
                lines.append(("✅ " if completed else "⬜ ") + record.get("task", "Rutina"))
            self._print("Rutinas de hoy:\n\n" + "\n\n".join(lines))
            return True
        return False

    # ------------------------------------------------------------------
    # Cocina y explicaciones sencillas
    # ------------------------------------------------------------------
    def _handle_cooking_and_explanations(self, text: str, plain: str) -> bool:
        cooking = re.match(r"^(?:que\s+puedo\s+cocinar\s+con|tengo)\s+(.+)$", plain)
        if cooking and any(word in plain for word in ("cocinar", "huevos", "pollo", "arroz", "queso", "jamon", "patatas")):
            ingredients = cooking.group(1).strip()
            prompt = (
                "Propón una receta sencilla y segura con estos ingredientes. "
                "No inventes que tiene ingredientes no mencionados sin marcarlos como opcionales. "
                "Da pasos breves y pregunta al final si quiere otra idea. Ingredientes: " + ingredients
            )
            self._print(self._generate_text(prompt, fallback="Puedo ayudarte, pero dime también si buscas algo rápido, al horno o de sartén."))
            return True
        if plain in {"dame una receta rapida", "quiero una receta rapida"}:
            self._print("¿Qué ingredientes tienes y prefieres sartén, horno o algo sin cocinar?")
            return True
        explain = re.match(r"^(?:que\s+significa|explicame)\s+(.+)$", plain)
        if explain:
            subject = explain.group(1).strip()
            prompt = f"Explica de forma sencilla, breve y con un ejemplo qué significa: {subject}. Si falta contexto, haz una sola pregunta aclaratoria."
            self._print(self._generate_text(prompt, fallback=f"¿Dónde has visto «{subject}»? Con ese contexto te lo explico mejor."))
            return True
        if plain in {"explicamelo como si no supiera nada", "ponme un ejemplo"}:
            self._print("Claro. ¿Sobre qué explicación anterior quieres que lo haga?")
            return True
        return False

    # ------------------------------------------------------------------
    # Recordatorios personales
    # ------------------------------------------------------------------
    def _queue(self) -> TelegramDeliveryQueue:
        return TelegramDeliveryQueue(self.telegram_storage)

    def _handle_personal_reminders(self, text: str, plain: str, owner: str, state: dict) -> bool:
        queue = self._queue()
        parsed = self.personal_reminder_parser.parse(text)
        if parsed is not None:
            request = InteruserRequest(owner, parsed.message, parsed.due_at_utc, True)
            result = queue.enqueue(owner, request)
            if not result.get("ok"):
                self._print("No puedo programarlo todavía porque tu usuario no está vinculado a un chat de Telegram.")
                return True
            state["last_reminder_id"] = result["id"]
            local = parsed.due_at_utc.astimezone(self.personal_reminder_parser.timezone)
            day = "hoy" if local.date() == datetime.now(self.personal_reminder_parser.timezone).date() else local.strftime("el %d/%m/%Y")
            self._print(f"Hecho. Te lo recordaré {day} a las {local:%H:%M}.")
            return True

        if re.search(r"\b(?:que|cuales)\s+recordatorios\s+tengo\b|\bmis\s+recordatorios\b", plain):
            pending = [item for item in queue.list_pending(owner) if str(item.get("target_user_id", "")).casefold() == owner.casefold()]
            if not pending:
                self._print("No tienes recordatorios pendientes.")
                return True
            lines = ["Estos son tus recordatorios pendientes:"]
            for index, item in enumerate(pending, 1):
                due = datetime.fromisoformat(str(item["due_at"]))
                local = due.astimezone(self.personal_reminder_parser.timezone)
                lines.append(f"{index}. {item.get('message')} — {local:%d/%m/%Y a las %H:%M}")
            state["last_reminder_ids"] = [item["id"] for item in pending]
            self._print("\n\n".join(lines))
            return True

        cancel = re.match(r"^(?:cancela|borra|elimina)\s+(?:el\s+)?recordatorio(?:\s+de)?\s*(.*)$", plain)
        if cancel:
            query = cancel.group(1).strip()
            target = self._select_reminder(queue.list_pending(owner), query, state)
            if target is None:
                self._print("No he encontrado con seguridad qué recordatorio quieres cancelar. Dime una palabra del recordatorio.")
                return True
            state["pending_daily_action"] = {"type": "cancel_reminder", "id": target["id"], "message": target.get("message", "")}
            self._print(f"¿Seguro que quieres cancelar «{target.get('message')}»? Responde «sí» para confirmarlo.")
            return True

        change = re.match(r"^cambia\s+(?:el\s+)?recordatorio(?:\s+de\s+(.+?))?\s+(?:a|para)\s+(?:las\s+)?([0-2]?\d)(?::([0-5]\d))?$", plain)
        if change:
            query, hour_text, minute_text = change.groups()
            target = self._select_reminder(queue.list_pending(owner), (query or "").strip(), state)
            if target is None:
                self._print("No sé qué recordatorio quieres cambiar. Indícame una palabra de su contenido.")
                return True
            old_due = datetime.fromisoformat(str(target["due_at"]))
            local = old_due.astimezone(self.personal_reminder_parser.timezone).replace(hour=int(hour_text), minute=int(minute_text or 0))
            if local.astimezone(UTC) <= datetime.now(UTC):
                from datetime import timedelta
                local += timedelta(days=1)
            if queue.update_delivery(owner, target["id"], due_at_utc=local.astimezone(UTC)):
                state["last_reminder_id"] = target["id"]
                self._print(f"Listo. He cambiado el recordatorio a {local:%d/%m/%Y a las %H:%M}.")
            else:
                self._print("No he podido cambiar ese recordatorio.")
            return True
        return False

    @staticmethod
    def _select_reminder(records: list[dict], query: str, state: dict) -> dict | None:
        records = [item for item in records if item.get("status") == "pending"]
        if query:
            matches = [item for item in records if query.casefold() in str(item.get("message", "")).casefold()]
            return matches[0] if len(matches) == 1 else None
        last_id = state.get("last_reminder_id")
        for item in records:
            if item.get("id") == last_id:
                return item
        return records[0] if len(records) == 1 else None

    # ------------------------------------------------------------------
    # Listas
    # ------------------------------------------------------------------
    def _handle_lists(self, text: str, plain: str, owner: str, state: dict) -> bool:
        create = re.match(r"^crea\s+(?:una\s+)?lista\s+(?:para|de)\s+(.+)$", plain)
        if create:
            name = create.group(1)
            created = self.personal_lists.create(owner, name)
            self._print(f"He creado la lista de {name}." if created else f"La lista de {name} ya existía.")
            return True

        add = re.match(r"^anade\s+(.+?)\s+a\s+(?:la\s+)?lista(?:\s+de\s+(.+))?$", plain)
        if add:
            items_text, list_name = add.groups()
            items = [item.strip() for item in re.split(r",|\s+y\s+", items_text) if item.strip()]
            name = list_name or "compra"
            added = self.personal_lists.add(owner, name, items)
            if added:
                self._print(f"Añadido a la lista de {name}: {', '.join(added)}.")
            else:
                self._print("Esos elementos ya estaban en la lista.")
            return True

        remove = re.match(r"^(?:quita|borra|elimina)\s+(.+?)\s+de\s+(?:la\s+)?lista(?:\s+de\s+(.+))?$", plain)
        if remove:
            item, list_name = remove.groups()
            name = list_name or "compra"
            ok = self.personal_lists.remove(owner, name, item)
            self._print(f"He quitado {item} de la lista de {name}." if ok else f"No he encontrado {item} en la lista de {name}.")
            return True

        if re.search(r"\bque\s+(?:falta|hay)\s+(?:por\s+)?comprar\b", plain):
            return self._show_list(owner, "compra", state)

        show = re.match(r"^(?:muestra|ensena|que\s+hay\s+en)\s+(?:la\s+)?lista(?:\s+de\s+(.+))?$", plain)
        if show:
            return self._show_list(owner, show.group(1) or "compra", state)

        share = re.match(r"^comparte\s+(?:la\s+)?lista(?:\s+de\s+(.+?))?\s+con\s+(.+)$", plain)
        if share:
            list_name, target = share.groups()
            name = list_name or "compra"
            record = self.personal_lists.get(owner, name)
            if not record:
                self._print(f"No existe la lista de {name}.")
                return True
            items = [str(item.get("text")) for item in record.get("items", []) if not item.get("done")]
            if not items:
                self._print(f"La lista de {name} está vacía.")
                return True
            linked = self._queue().linked_users()
            resolved = next((item for item in linked if item.casefold() == target.casefold() or item.casefold().startswith(target.casefold())), None)
            if resolved is None:
                self._print(f"No encuentro un usuario de Telegram vinculado llamado {target}.")
                return True
            request = InteruserRequest(resolved, f"te comparte su lista de {name}: {', '.join(items)}", datetime.now(UTC), False)
            result = self._queue().enqueue(owner, request)
            self._print(f"He compartido la lista de {name} con {resolved}." if result.get("ok") else "No he podido compartir la lista.")
            return True
        return False

    def _show_list(self, owner: str, name: str, state: dict) -> bool:
        record = self.personal_lists.get(owner, name)
        if not record:
            self._print(f"No tienes una lista de {name}.")
            return True
        items = [str(item.get("text")) for item in record.get("items", []) if not item.get("done")]
        if not items:
            self._print(f"La lista de {name} está vacía.")
            return True
        state["last_list"] = name
        self._print(f"En la lista de {name} tienes:\n\n" + "\n\n".join(f"{i}. {item}" for i, item in enumerate(items, 1)))
        return True

    # ------------------------------------------------------------------
    # Preguntas familiares y respuesta vinculada
    # ------------------------------------------------------------------
    def _handle_linked_reply(self, text: str, plain: str, owner: str) -> bool:
        match = re.match(r"^(?:responder|responde)\s*:?\s*(.+)$", text, flags=re.I)
        if not match:
            return False
        context = self._queue().last_incoming_question(owner)
        if context is None:
            self._print("No tengo una pregunta familiar pendiente a la que responder.")
            return True
        target = str(context.get("sender_user_id", "")).strip()
        body = match.group(1).strip()
        result = self._queue().enqueue(owner, InteruserRequest(target, body, datetime.now(UTC), False))
        self._print(f"He enviado tu respuesta a {target}." if result.get("ok") else "No he podido enviar la respuesta.")
        return True

    # ------------------------------------------------------------------
    # Memoria conversacional
    # ------------------------------------------------------------------
    def _handle_memory_conversation(self, text: str, plain: str, owner: str, state: dict) -> bool:
        query = re.match(r"^(?:que\s+recuerdas|recupera\s+lo\s+que\s+te\s+dije)\s+(?:de|sobre)\s+(.+)$", plain)
        if query:
            topic = query.group(1).replace("mi ", "", 1).strip()
            include_inactive = plain.startswith("recupera")
            memories = self.memory.list_memories(owner=owner, include_inactive=include_inactive)
            terms = topic.split()
            matches = [m for m in memories if any(term in self._plain(str(m.get("content", ""))) for term in terms)]
            if not matches:
                self._print(f"No encuentro recuerdos sobre {topic}.")
                return True
            state["last_memory_ids"] = [m["id"] for m in matches[:10]]
            if include_inactive:
                archived = [m for m in matches if m.get("state") != "active"]
                if len(archived) == 1 and self.memory.restore_memory(memory_id=archived[0]["id"], owner=owner):
                    self._print(f"He recuperado este recuerdo: {archived[0]['content']}")
                    return True
            self.memory.record_access(owner=owner, memory_ids=state["last_memory_ids"])
            self._print("Esto es lo que recuerdo:\n\n" + "\n\n".join(f"{i}. {m['content']}" for i, m in enumerate(matches[:10], 1)))
            return True

        if plain in {"archiva este recuerdo", "archivalo pero no lo borres", "archivalo"}:
            memory = self._last_memory(owner, state)
            if memory is None:
                self._print("No sé qué recuerdo quieres archivar. Consulta primero el dato concreto.")
            elif self.memory.archive_memory(memory_id=memory["id"], owner=owner):
                self._print("He archivado el recuerdo sin borrarlo. Podrás recuperarlo más adelante.")
            return True

        if plain in {"eso ya no es cierto", "olvida ese dato", "borra ese recuerdo"}:
            memory = self._last_memory(owner, state)
            if memory is None:
                self._print("No sé con seguridad a qué dato te refieres. Dime primero qué recuerdo quieres revisar.")
            else:
                state["pending_daily_action"] = {"type": "delete_memory", "id": memory["id"], "content": memory["content"]}
                self._print(f"¿Seguro que quieres borrar «{memory['content']}»? Para no eliminar nada por error, responde «sí».")
            return True

        correction = re.match(r"^corrige\s+lo\s+que\s+sabes\s+(?:de|sobre)\s+(.+)$", plain)
        if correction:
            topic = correction.group(1).replace("mi ", "", 1).strip()
            matches = self.memory.find_memories(owner=owner, query=topic, limit=5)
            if len(matches) == 1:
                state["pending_daily_action"] = {"type": "update_memory", "id": matches[0]["id"], "old": matches[0]["content"]}
                self._print(f"Ahora recuerdo «{matches[0]['content']}». ¿Cuál es el dato correcto?")
            elif matches:
                state["last_memory_ids"] = [m["id"] for m in matches]
                self._print("He encontrado varios recuerdos. Dime el número que quieres corregir:\n\n" + "\n\n".join(f"{i}. {m['content']}" for i, m in enumerate(matches, 1)))
            else:
                self._print(f"No encuentro un recuerdo sobre {topic} para corregirlo.")
            return True

        if plain in {"por que sabes eso", "de donde sabes eso", "cual es la fuente de ese dato"}:
            memory = self._last_memory(owner, state)
            if memory is None:
                self._print("Necesito que consultes primero el recuerdo al que te refieres.")
            else:
                source = memory.get("source_document") or memory.get("source")
                confirmed_by = memory.get("confirmed_by") or memory.get("created_by") or memory.get("owner")
                created = str(memory.get("created_at", "fecha desconocida")).split("T")[0]
                if source:
                    self._print(f"Lo he obtenido de {source}. El recuerdo se registró el {created}.")
                else:
                    self._print(f"Lo sé porque quedó registrado para {memory.get('owner')} el {created}, confirmado por {confirmed_by}.")
            return True

        if plain in {"quien puede ver este recuerdo", "quien puede ver ese dato"}:
            memory = self._last_memory(owner, state)
            if memory is None:
                self._print("Consulta primero el recuerdo concreto para que pueda revisar sus permisos.")
            else:
                visibility = str(memory.get("visibility", "private"))
                mapping = {
                    "private": "Solo su propietario.",
                    "admin_managed": "Su propietario y Liam como administrador de Atlas.",
                    "partner": "Su propietario, su pareja autorizada y Liam.",
                    "family": "Su propietario, la familia autorizada y Liam.",
                    "known": "Las personas de confianza autorizadas y Liam.",
                    "public": "Cualquier usuario de Atlas.",
                }
                self._print(mapping.get(visibility, "No puedo explicar ese permiso con seguridad."))
            return True

        if plain in {"cuando consultaste esto por ultima vez", "cuando consultaste ese recuerdo por ultima vez"}:
            memory = self._last_memory(owner, state)
            if memory is None:
                self._print("Consulta primero el recuerdo concreto.")
            else:
                when = memory.get("last_accessed_at")
                count = int(memory.get("access_count", 0))
                self._print(f"Se ha consultado {count} veces. La última fue {when}." if when else "Todavía no constaba ninguna consulta anterior.")
            return True

        if re.match(r"^que\s+recuerdos\s+de\s+(.+)\s+son\s+compartidos\s+con\s+familia$", plain):
            target = re.match(r"^que\s+recuerdos\s+de\s+(.+)\s+son\s+compartidos\s+con\s+familia$", plain).group(1)
            resolved = self.users.resolve_user_name(target) or target
            memories = [m for m in self.memory.list_memories(owner=resolved) if m.get("visibility") == "family"]
            if not memories:
                self._print(f"No hay recuerdos de {resolved} compartidos con la familia.")
            else:
                self._print("Recuerdos compartidos con familia:\n\n" + "\n\n".join(f"{i}. {m['content']}" for i, m in enumerate(memories, 1)))
            return True

        if plain in {"revisa recuerdos duplicados", "busca recuerdos duplicados"}:
            candidates = self.long_term_memory.consolidation_candidates(user_id=owner)
            if not candidates:
                self._print("No he encontrado recuerdos suficientemente parecidos como para proponer una consolidación.")
            else:
                pair = candidates[0]
                memories = [self.memory.get_memory_by_id(mid, owner=owner) for mid in pair["memory_ids"]]
                memories = [m for m in memories if m]
                state["pending_merge"] = pair
                self._print("Parece que estos recuerdos podrían describir lo mismo, pero no los fusionaré sin permiso:\n\n" + "\n\n".join(f"{i}. {m['content']}" for i, m in enumerate(memories, 1)))
            return True
        return False

    def _last_memory(self, owner: str, state: dict) -> dict | None:
        ids = state.get("last_memory_ids") or []
        return self.memory.get_memory_by_id(ids[0], owner=owner) if ids else None

    def _handle_daily_pending(self, text: str, plain: str, owner: str, state: dict) -> bool:
        action = state.get("pending_daily_action")
        if not action:
            return False
        if action.get("type") == "update_memory":
            # La siguiente frase completa es el contenido correcto, salvo cancelación.
            if plain in {"cancela", "cancelar", "no"}:
                state.pop("pending_daily_action", None)
                self._print("De acuerdo, no he cambiado el recuerdo.")
                return True
            metadata = {"temporal_scope": self._infer_temporal_scope(text), "confirmed_by": owner}
            previous = self.memory.update_memory(memory_id=action["id"], owner=owner, content=text, metadata=metadata)
            state.pop("pending_daily_action", None)
            if previous:
                state["last_memory_ids"] = [action["id"]]
                self._print("He corregido el recuerdo y he conservado la versión anterior en su historial.")
            else:
                self._print("No he podido actualizar ese recuerdo.")
            return True
        if plain not in {"si", "sí", "confirmar", "confirmo", "adelante"}:
            if plain in {"no", "cancela", "cancelar"}:
                state.pop("pending_daily_action", None)
                self._print("Operación cancelada. No he cambiado nada.")
                return True
            return False
        state.pop("pending_daily_action", None)
        if action["type"] == "cancel_reminder":
            ok = self._queue().cancel(owner, action["id"])
            self._print("Recordatorio cancelado." if ok else "Ese recordatorio ya no estaba pendiente.")
            return True
        if action["type"] == "delete_memory":
            removed = self.memory.delete_memory(memory_id=action["id"], owner=owner)
            self._print("He borrado el recuerdo." if removed else "No he podido borrar ese recuerdo.")
            return True
        return False

    @staticmethod
    def _infer_temporal_scope(text: str) -> str:
        plain = AtlasDailyMixin._plain(text)
        if any(word in plain for word in ("ahora", "actualmente", "este verano", "temporalmente")):
            return "temporary_current"
        if any(word in plain for word in ("antes", "vivia", "trabajaba", "antiguamente")):
            return "historical"
        if any(word in plain for word in ("cada verano", "en verano", "normalmente")):
            return "seasonal_or_habitual"
        return "current"

    # ------------------------------------------------------------------
    # Escritura de mensajes
    # ------------------------------------------------------------------
    def _handle_message_help(self, text: str, plain: str, owner: str, state: dict) -> bool:
        request = re.match(r"^(?:escribeme|redacta)\s+(?:un\s+)?mensaje\s+(?:para\s+)?(.+)$", plain)
        correction = re.match(r"^corrige\s+este\s+mensaje\s*:?\s*(.+)$", text, flags=re.I)
        if request or correction:
            task = request.group(1) if request else correction.group(1)
            prompt = (
                "Redacta un único mensaje breve y natural en español. No inventes datos. "
                f"Petición: {task}. Devuelve solo el texto del mensaje."
            )
            draft = self._generate_text(prompt, fallback=f"Hola, quería escribirte para {task}.")
            state["last_draft"] = draft
            self._print(draft)
            return True
        if plain in {"hazlo mas carinoso", "hazlo mas cariñoso", "hazlo mas corto", "hazlo mas educado", "hazlo mas formal"}:
            draft = state.get("last_draft")
            if not draft:
                self._print("Primero necesito que redactemos un mensaje.")
                return True
            style = plain.replace("hazlo ", "")
            prompt = f"Reescribe este mensaje de forma {style}. Mantén el significado y devuelve solo el mensaje:\n{draft}"
            updated = self._generate_text(prompt, fallback=draft)
            state["last_draft"] = updated
            self._print(updated)
            return True
        return False

    def _generate_text(self, prompt: str, fallback: str) -> str:
        provider = getattr(self, "ai_provider", None)
        if provider is None:
            return fallback
        try:
            generated = str(provider.generate(prompt)).strip()
            return generated or fallback
        except Exception:
            return fallback

    # ------------------------------------------------------------------
    # Ayuda, curiosidades e historias
    # ------------------------------------------------------------------
    def _handle_everyday_help(self, text: str, plain: str) -> bool:
        if plain in {"que puedes hacer", "ayuda", "como puedes ayudarme", "no se como pedirte esto"}:
            self._print(
                "Puedo ayudarte con recordatorios, listas, mensajes familiares, búsquedas en Internet, "
                "traducciones, cálculos, juegos, memoria y dudas cotidianas. Por ejemplo: «Recuérdame a las 8 "
                "que tome la pastilla» o «Añade leche a la lista de la compra»."
            )
            return True
        if plain.startswith("cuentame una curiosidad"):
            curiosities = (
                "Los pulpos tienen tres corazones y su sangre es azul.",
                "La miel puede conservarse durante muchísimo tiempo si se mantiene bien cerrada.",
                "Un día en Venus dura más que un año en Venus.",
                "Los cuervos pueden reconocer rostros humanos y recordarlos durante años.",
            )
            index = int(datetime.now().timestamp()) % len(curiosities)
            self._print(curiosities[index])
            return True
        if plain.startswith("cuentame una historia corta"):
            self._print("Una tarde, una mujer encontró una llave antigua en el bolsillo de un abrigo que no usaba desde hacía años. No abría ninguna puerta de su casa, pero sí una pequeña caja que su madre había guardado para ella. Dentro solo había una nota: «Las cosas importantes siempre encuentran el momento de volver». 🔑")
            return True
        if "aumento el tamano de la letra" in plain or "aumentar el tamano de la letra" in plain:
            self._print("En Android suele estar en Ajustes → Pantalla → Tamaño de fuente o Tamaño y texto. En iPhone: Ajustes → Pantalla y brillo → Tamaño del texto. Si me dices el modelo del móvil, te guío con más precisión.")
            return True
        if "mando una ubicacion por whatsapp" in plain or "enviar ubicacion por whatsapp" in plain:
            self._print("Abre el chat de WhatsApp, toca el clip o el botón +, elige «Ubicación» y selecciona «Enviar mi ubicación actual». Revisa siempre a quién se la envías antes de confirmar.")
            return True
        if plain.startswith("que significa este mensaje de error"):
            self._print("Cópialo aquí o envíame una captura. Si mandas una imagen, podré reconocer que la has enviado; el análisis visual completo todavía debe estar conectado.")
            return True
        return False
