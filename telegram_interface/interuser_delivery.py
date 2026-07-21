"""Mensajes y recordatorios entre usuarios vinculados a Telegram.

La cola es persistente y genérica: no conoce nombres concretos. Resuelve el
usuario de destino mediante las asociaciones Telegram <-> Atlas ya existentes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
import re
import secrets
import threading
from typing import Any
import unicodedata
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from telegram_interface.client import TelegramClientError, TelegramClientProtocol
from telegram_interface.storage import TelegramStorage, utc_now_text


@dataclass(frozen=True, slots=True)
class InteruserRequest:
    target_user_id: str
    message: str
    due_at_utc: datetime
    scheduled: bool


class InteruserRequestParser:
    """Analiza frases en español sin depender del modelo de IA."""

    IMMEDIATE_PREFIXES = (
        "dile a",
        "avisa a",
        "avisale a",
        "manda a",
        "mandale a",
        "envia a",
        "enviale a",
        "recuerda a",
        "recuerdale a",
        "pregunta a",
    )

    def __init__(self, timezone_name: str = "Europe/Madrid") -> None:
        self.timezone_name = timezone_name
        try:
            self.timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            # En Windows, zoneinfo depende del paquete tzdata cuando el sistema
            # no proporciona la base IANA. Usamos UTC como último recurso para
            # que Atlas siga arrancando, aunque los recordatorios locales no
            # tendrán cambio horario hasta instalar tzdata.
            self.timezone = timezone.utc
            self.timezone_name = "UTC"

    @staticmethod
    def _plain(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text.casefold())
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))

    def parse(
        self,
        text: str,
        *,
        linked_user_ids: list[str],
        now: datetime | None = None,
    ) -> InteruserRequest | None:
        original = " ".join(text.strip().split())
        if not original:
            return None
        plain = self._plain(original)
        prefix = next((item for item in self.IMMEDIATE_PREFIXES if plain.startswith(item + " ")), None)
        if prefix is None:
            return None

        remainder_original = original[len(prefix):].strip()
        remainder_plain = plain[len(prefix):].strip()
        target = self._resolve_target(remainder_plain, linked_user_ids)
        if target is None:
            return None
        target_plain = self._plain(target)
        if not remainder_plain.startswith(target_plain):
            return None

        tail_original = remainder_original[len(target):].strip(" ,:")
        tail_plain = self._plain(tail_original)
        current = now or datetime.now(self.timezone)
        if current.tzinfo is None:
            current = current.replace(tzinfo=self.timezone)
        else:
            current = current.astimezone(self.timezone)

        schedule = self._extract_schedule(tail_original, tail_plain, current)
        if schedule is not None:
            due_local, body = schedule
            if not body:
                return None
            return InteruserRequest(
                target_user_id=target,
                message=body,
                due_at_utc=due_local.astimezone(UTC),
                scheduled=True,
            )

        body = self._extract_body(tail_original)
        if not body:
            return None
        return InteruserRequest(
            target_user_id=target,
            message=body,
            due_at_utc=datetime.now(UTC),
            scheduled=False,
        )

    def _resolve_target(self, remainder_plain: str, linked_user_ids: list[str]) -> str | None:
        candidates = sorted(linked_user_ids, key=lambda item: len(self._plain(item)), reverse=True)
        for candidate in candidates:
            plain_candidate = self._plain(candidate)
            if remainder_plain == plain_candidate or remainder_plain.startswith(plain_candidate + " "):
                return candidate
        return None

    @staticmethod
    def _extract_body(tail: str) -> str:
        body = re.sub(r"^(?:que|:|,)+\s*", "", tail, flags=re.IGNORECASE).strip()
        return body[:1500]

    def _extract_schedule(
        self,
        tail_original: str,
        tail_plain: str,
        now: datetime,
    ) -> tuple[datetime, str] | None:
        # Admite: "a las 17 que...", "hoy a las 17:30 que..." y
        # "mañana a las 8 que...".
        pattern = re.compile(
            r"^(?:(hoy|manana)\s+)?a\s+las\s+([0-2]?\d)(?::([0-5]\d))?\s*(?:h|horas?)?\s*(?:que|:|,)?\s*(.+)$",
            re.IGNORECASE,
        )
        match = pattern.match(tail_plain)
        if not match:
            return None
        day_word, hour_text, minute_text, body_plain = match.groups()
        hour = int(hour_text)
        minute = int(minute_text or 0)
        if hour > 23:
            return None

        # Los índices del texto normalizado se conservan para letras acentuadas
        # comunes en español; así recuperamos el cuerpo con su ortografía original.
        body = tail_original[match.start(4):].strip()
        body = re.sub(r"^(?:que|:|,)+\s*", "", body, flags=re.IGNORECASE).strip()[:1500]

        due_date = now.date()
        if day_word == "manana":
            due_date += timedelta(days=1)
        due = datetime.combine(due_date, datetime.min.time(), tzinfo=self.timezone).replace(
            hour=hour,
            minute=minute,
        )
        if day_word != "hoy" and due <= now:
            due += timedelta(days=1)
        if day_word == "hoy" and due <= now:
            return None
        return due, body


class NaturalInteruserMessageFormatter:
    """Convierte mensajes indirectos en avisos naturales para el destinatario.

    No utiliza IA ni altera el significado libremente. Aplica transformaciones
    pequeñas y previsibles sobre pronombres y verbos frecuentes; cuando no
    reconoce una estructura, conserva el mensaje original tras una introducción
    neutra.
    """

    _AFFECTION_RE = re.compile(
        r"^(?:(?:que\s+)?(?:la|lo|le|te)\s+)?quiero(?P<rest>\s+.*)?$",
        re.IGNORECASE,
    )

    _SECOND_PERSON_REPLACEMENTS = (
        (re.compile(r"^se\s+tiene\s+que\s+", re.IGNORECASE), "te tienes que "),
        (re.compile(r"^tiene\s+que\s+", re.IGNORECASE), "tienes que "),
        (re.compile(r"^que\s+se\s+", re.IGNORECASE), "que te "),
        (re.compile(r"^se\s+", re.IGNORECASE), "te "),
    )

    _VERB_REPLACEMENTS = {
        "ponga": "pongas",
        "vaya": "vayas",
        "compre": "compres",
        "haga": "hagas",
        "saque": "saques",
        "lleve": "lleves",
        "cierre": "cierres",
        "abra": "abras",
        "llame": "llames",
        "recuerde": "recuerdes",
        "apague": "apagues",
        "encienda": "enciendas",
        "termine": "termines",
        "salga": "salgas",
        "llegue": "llegues",
    }

    _REMINDER_STARTS = (
        "ponga ", "vaya ", "compre ", "haga ", "saque ",
        "lleve ", "cierre ", "abra ", "llame ", "recuerde ",
        "apague ", "encienda ", "termine ", "salga ", "llegue ",
        "se tiene que ", "tiene que ", "no se olvide ",
    )

    @classmethod
    def _second_person(cls, body: str) -> str:
        result = body.strip()
        for pattern, replacement in cls._SECOND_PERSON_REPLACEMENTS:
            result = pattern.sub(replacement, result, count=1)

        parts = result.split(maxsplit=1)
        if parts:
            replacement = cls._VERB_REPLACEMENTS.get(parts[0].casefold())
            if replacement:
                if parts[0][:1].isupper():
                    replacement = replacement.capitalize()
                result = replacement + ((" " + parts[1]) if len(parts) > 1 else "")

        # Los infinitivos reflexivos del mensaje original se dirigen ahora al
        # destinatario: «vaya a cortarse» -> «vayas a cortarte».
        # También cubre «irse» -> «irte», «vestirse» -> «vestirte», etc.
        result = re.sub(
            r"\b([a-záéíóúüñ]+)rse\b",
            r"\1rte",
            result,
            flags=re.IGNORECASE,
        )
        return result

    @staticmethod
    def _finish(text: str) -> str:
        clean = " ".join(text.strip().split())
        if not clean:
            return clean
        return clean if clean[-1] in ".!?" else clean + "."

    @classmethod
    def format(cls, *, sender: str, body: str, scheduled: bool) -> str:
        clean_sender = sender.strip() or "Alguien"
        clean_sender = clean_sender[:1].upper() + clean_sender[1:]
        clean_body = " ".join(body.strip().split())
        plain = InteruserRequestParser._plain(clean_body)

        affection = cls._AFFECTION_RE.match(plain)
        if affection:
            rest = (affection.group("rest") or "").strip()
            # El emisor habla en primera persona ("le echo de menos"), pero el
            # destinatario debe recibir una frase natural en tercera persona.
            rest = re.sub(r"\b(?:le|te)\s+echo\b", "te echa", rest, flags=re.IGNORECASE)
            rest = re.sub(r"\b(?:le|te)\s+extrano\b", "te extraña", rest, flags=re.IGNORECASE)
            suffix = f" {rest}" if rest else ""
            return cls._finish(
                f"{clean_sender} quiere decirte que te quiere{suffix}"
            )

        is_reminder = scheduled or any(plain.startswith(item) for item in cls._REMINDER_STARTS)
        if is_reminder:
            converted = cls._second_person(clean_body)
            converted = re.sub(
                r"^no\s+se\s+olvide\s+de\s+",
                "no te olvides de ",
                converted,
                flags=re.IGNORECASE,
            )
            return cls._finish(f"{clean_sender} te recuerda que {converted}")

        if plain.startswith("si ") or clean_body.endswith("?"):
            question = clean_body if clean_body.endswith("?") else clean_body + "?"
            return cls._finish(f"{clean_sender} te pregunta {question}")

        # Para información en primera persona, mantenemos el texto literal y
        # utilizamos una introducción natural que no cambia quién realiza la acción.
        first_person = re.match(
            r"^(?:yo\s+)?(?:he|voy|estoy|tengo|puedo|quiero|necesito|llego|salgo|vuelvo)\b",
            plain,
        )
        if first_person:
            return cls._finish(f"{clean_sender} quiere decirte que {clean_body}")

        return cls._finish(f"{clean_sender} quiere decirte: {clean_body}")


class TelegramDeliveryQueue:
    """Cola persistente de entregas interusuario."""

    def __init__(self, storage: TelegramStorage) -> None:
        self.storage = storage

    def linked_users(self) -> list[str]:
        users: list[str] = []
        for account in self.storage.section("accounts").values():
            if not isinstance(account, dict) or account.get("state") != "linked":
                continue
            user_id = str(account.get("atlas_user_id", "")).strip()
            if user_id and user_id.casefold() not in {item.casefold() for item in users}:
                users.append(user_id)
        return users

    def _target_account(self, atlas_user_id: str) -> tuple[str, dict[str, Any]] | None:
        for telegram_user_id, account in self.storage.section("accounts").items():
            if not isinstance(account, dict) or account.get("state") != "linked":
                continue
            if str(account.get("atlas_user_id", "")).casefold() == atlas_user_id.casefold():
                if str(account.get("chat_id", "")).strip():
                    return str(telegram_user_id), account
        return None

    def enqueue(self, sender_user_id: str, request: InteruserRequest) -> dict[str, Any]:
        target = self._target_account(request.target_user_id)
        if target is None:
            return {"ok": False, "error": "target_not_linked"}
        telegram_user_id, account = target
        delivery_id = secrets.token_hex(5)
        record = {
            "id": delivery_id,
            "sender_user_id": sender_user_id.strip(),
            "target_user_id": str(account.get("atlas_user_id", request.target_user_id)).strip(),
            "target_telegram_user_id": telegram_user_id,
            "target_chat_id": str(account.get("chat_id")),
            "message": request.message.strip()[:1500],
            "due_at": request.due_at_utc.astimezone(UTC).isoformat(),
            "scheduled": bool(request.scheduled),
            "status": "pending",
            "attempts": 0,
            "created_at": utc_now_text(),
            "updated_at": utc_now_text(),
        }

        def mutate(data: dict[str, Any]) -> None:
            data.setdefault("deliveries", {})[delivery_id] = record

        self.storage.update(mutate)
        return {"ok": True, **record}

    def list_pending(self, sender_user_id: str) -> list[dict[str, Any]]:
        records = []
        for item in self.storage.section("deliveries").values():
            if not isinstance(item, dict):
                continue
            if item.get("status") != "pending":
                continue
            if str(item.get("sender_user_id", "")).casefold() != sender_user_id.casefold():
                continue
            records.append(item)
        return sorted(records, key=lambda item: str(item.get("due_at", "")))

    def cancel(self, sender_user_id: str, delivery_id: str) -> bool:
        clean_id = delivery_id.strip().casefold()

        def mutate(data: dict[str, Any]) -> bool:
            for key, item in data.setdefault("deliveries", {}).items():
                if key.casefold() != clean_id or not isinstance(item, dict):
                    continue
                if item.get("status") != "pending":
                    return False
                if str(item.get("sender_user_id", "")).casefold() != sender_user_id.casefold():
                    return False
                item.update({"status": "cancelled", "updated_at": utc_now_text()})
                return True
            return False

        return bool(self.storage.update(mutate))

    def update_delivery(
        self,
        sender_user_id: str,
        delivery_id: str,
        *,
        due_at_utc: datetime | None = None,
        message: str | None = None,
    ) -> bool:
        """Actualiza un recordatorio pendiente del propio emisor."""
        def mutate(data: dict[str, Any]) -> bool:
            item = data.setdefault("deliveries", {}).get(delivery_id)
            if not isinstance(item, dict) or item.get("status") != "pending":
                return False
            if str(item.get("sender_user_id", "")).casefold() != sender_user_id.casefold():
                return False
            if due_at_utc is not None:
                item["due_at"] = due_at_utc.astimezone(UTC).isoformat()
            if message is not None and message.strip():
                item["message"] = message.strip()[:1500]
            item["updated_at"] = utc_now_text()
            return True
        return bool(self.storage.update(mutate))

    def record_incoming_question(self, *, target_user_id: str, sender_user_id: str, delivery_id: str) -> None:
        def mutate(data: dict[str, Any]) -> None:
            data.setdefault("reply_context", {})[target_user_id.casefold()] = {
                "sender_user_id": sender_user_id,
                "delivery_id": delivery_id,
                "updated_at": utc_now_text(),
            }
        self.storage.update(mutate)

    def last_incoming_question(self, target_user_id: str) -> dict[str, Any] | None:
        item = self.storage.section("reply_context").get(target_user_id.casefold())
        return dict(item) if isinstance(item, dict) else None

    def claim_due(self, *, limit: int = 20) -> list[dict[str, Any]]:
        now = datetime.now(UTC)

        def mutate(data: dict[str, Any]) -> list[dict[str, Any]]:
            claimed: list[dict[str, Any]] = []
            deliveries = data.setdefault("deliveries", {})
            for item in sorted(deliveries.values(), key=lambda value: str(value.get("due_at", ""))):
                if len(claimed) >= limit or not isinstance(item, dict):
                    continue
                if item.get("status") == "sending":
                    try:
                        updated = datetime.fromisoformat(str(item.get("updated_at")))
                    except (TypeError, ValueError):
                        updated = now - timedelta(minutes=10)
                    if updated <= now - timedelta(minutes=5):
                        item["status"] = "pending"
                if item.get("status") != "pending":
                    continue
                try:
                    due = datetime.fromisoformat(str(item.get("due_at")))
                except (TypeError, ValueError):
                    item["status"] = "invalid"
                    continue
                if due.tzinfo is None:
                    due = due.replace(tzinfo=UTC)
                if due > now:
                    continue
                item.update({"status": "sending", "updated_at": utc_now_text()})
                claimed.append(dict(item))
            return claimed

        return self.storage.update(mutate)

    def mark_delivered(self, delivery_id: str) -> None:
        def mutate(data: dict[str, Any]) -> None:
            item = data.setdefault("deliveries", {}).get(delivery_id)
            if isinstance(item, dict):
                item.update({"status": "delivered", "delivered_at": utc_now_text(), "updated_at": utc_now_text()})
        self.storage.update(mutate)

    def mark_failed(self, delivery_id: str, *, retryable: bool) -> None:
        def mutate(data: dict[str, Any]) -> None:
            item = data.setdefault("deliveries", {}).get(delivery_id)
            if not isinstance(item, dict):
                return
            attempts = int(item.get("attempts", 0)) + 1
            status = "pending" if retryable and attempts < 5 else "failed"
            item.update({"status": status, "attempts": attempts, "updated_at": utc_now_text()})
            if status == "pending":
                item["due_at"] = (datetime.now(UTC) + timedelta(seconds=min(300, 15 * attempts))).isoformat()
        self.storage.update(mutate)


class TelegramDeliveryDispatcher:
    """Entrega en segundo plano los elementos vencidos de la cola."""

    def __init__(self, queue: TelegramDeliveryQueue, client: TelegramClientProtocol) -> None:
        self.queue = queue
        self.client = client
        self._lock = threading.Lock()

    def deliver_due(self) -> int:
        delivered = 0
        with self._lock:
            for item in self.queue.claim_due():
                scheduled = bool(item.get("scheduled"))
                sender = str(item.get("sender_user_id", "Alguien"))
                body = str(item.get("message", "")).strip()
                text = NaturalInteruserMessageFormatter.format(
                    sender=sender,
                    body=body,
                    scheduled=scheduled,
                )
                try:
                    self.client.send_message(
                        chat_id=str(item.get("target_chat_id")),
                        text=text,
                        parse_mode=None,
                    )
                except TelegramClientError as exc:
                    self.queue.mark_failed(str(item.get("id")), retryable=exc.retryable)
                except Exception:
                    self.queue.mark_failed(str(item.get("id")), retryable=True)
                else:
                    self.queue.mark_delivered(str(item.get("id")))
                    plain_body = InteruserRequestParser._plain(body)
                    if plain_body.startswith("si ") or body.rstrip().endswith("?"):
                        self.queue.record_incoming_question(
                            target_user_id=str(item.get("target_user_id", "")),
                            sender_user_id=str(item.get("sender_user_id", "")),
                            delivery_id=str(item.get("id", "")),
                        )
                    delivered += 1
        return delivered
