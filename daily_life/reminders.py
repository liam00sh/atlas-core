"""Análisis determinista de recordatorios personales."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
import re
import unicodedata
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


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
