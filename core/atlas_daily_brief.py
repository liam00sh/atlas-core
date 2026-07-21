"""Resumen conversacional de buenos días y buenas noches.

El tiempo usa Open-Meteo sin clave. La ubicación doméstica se obtiene de
ATLAS_HOME_LOCATION y, de forma provisional para este proyecto, usa Beneixama.
La arquitectura deja preparados ganchos para agenda, cumpleaños y turnos.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import json
import os
from urllib.parse import urlencode
from urllib.request import urlopen
import unicodedata


def _norm(text: str) -> str:
    value = unicodedata.normalize("NFD", text.casefold())
    return " ".join("".join(c for c in value if unicodedata.category(c) != "Mn").split())


def _json(url: str) -> dict:
    with urlopen(url, timeout=5) as response:  # nosec - servicio público fijo
        return json.loads(response.read().decode("utf-8"))


def _weather(location: str) -> str | None:
    try:
        geo = _json("https://geocoding-api.open-meteo.com/v1/search?" + urlencode({"name": location, "count": 1, "language": "es", "format": "json"}))
        result = (geo.get("results") or [])[0]
        latitude, longitude = result["latitude"], result["longitude"]
        forecast = _json("https://api.open-meteo.com/v1/forecast?" + urlencode({
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,apparent_temperature,precipitation,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto",
            "forecast_days": 2,
        }))
        current = forecast.get("current") or {}
        daily = forecast.get("daily") or {}
        maximum = (daily.get("temperature_2m_max") or [None])[0]
        minimum = (daily.get("temperature_2m_min") or [None])[0]
        rain = (daily.get("precipitation_probability_max") or [None])[0]
        pieces = [f"Ahora hay {current.get('temperature_2m', '—')} °C"]
        if maximum is not None and minimum is not None:
            pieces.append(f"hoy se esperan entre {minimum} y {maximum} °C")
        if rain is not None:
            pieces.append(f"con un {rain}% de probabilidad máxima de lluvia")
        return ", ".join(pieces) + "."
    except Exception:
        return None


class AtlasDailyBriefMixin:

    def _brief_reminders(self, owner: str, *, tomorrow: bool = False) -> list[str]:
        try:
            self._daily_bootstrap()
            timezone = self.personal_reminder_parser.timezone
            target = datetime.now(timezone).date() + (timedelta(days=1) if tomorrow else timedelta())
            rows = []
            for item in self._queue().list_pending(owner):
                if str(item.get("target_user_id", "")).casefold() != owner.casefold():
                    continue
                raw_due = item.get("due_at_utc") or item.get("due_at")
                due = datetime.fromisoformat(str(raw_due)).astimezone(timezone)
                if due.date() == target:
                    rows.append((due, str(item.get("message", "Recordatorio"))))
            rows.sort(key=lambda row: row[0])
            return [f"{due:%H:%M} — {message}" for due, message in rows]
        except Exception:
            return []

    def _optional_brief_items(self, hook_name: str, owner: str, target_date) -> list[str]:
        hook = getattr(self, hook_name, None)
        if not callable(hook):
            return []
        try:
            result = hook(owner, target_date)
        except Exception:
            return []
        return [str(item) for item in (result or []) if str(item).strip()]

    def _handle_daily_brief(self, text: str) -> bool:
        normalized = _norm(text).strip(" .!¡?¿")
        morning = normalized in {"buenos dias", "muy buenos dias", "buen dia"}
        night = normalized in {"buenas noches", "hasta manana", "me voy a dormir"}
        if not morning and not night:
            return False

        location = os.environ.get("ATLAS_HOME_LOCATION", "Beneixama, Alicante, España").strip()
        user = getattr(self, "get_user", lambda: "")()
        name = str(user or "").strip()
        if morning:
            print(f"¡Buenos días{', ' + name if name else ''}! ☀️")
            weather = _weather(location)
            if weather:
                print(f"Tiempo en {location}: {weather}")
            else:
                print("No he podido consultar el tiempo ahora mismo. El resto de Atlas sigue disponible.")
            reminders = self._brief_reminders(name, tomorrow=False) if name else []
            extra = []
            today = datetime.now().date()
            extra += self._optional_brief_items("_atlas_brief_calendar_events", name, today)
            extra += self._optional_brief_items("_atlas_brief_birthdays", name, today)
            if reminders:
                print("Pendiente para hoy:")
                print("\n".join(f"• {item}" for item in reminders))
            elif not extra:
                print("No veo recordatorios registrados para hoy.")
            if extra:
                print("También debes tener en cuenta:")
                print("\n".join(f"• {item}" for item in extra))
            return True

        print(f"Buenas noches{', ' + name if name else ''} 🌙")
        tomorrow = datetime.now().date() + timedelta(days=1)
        reminders = self._brief_reminders(name, tomorrow=True) if name else []
        shifts = self._optional_brief_items("_atlas_brief_work_shift", name, tomorrow)
        events = self._optional_brief_items("_atlas_brief_calendar_events", name, tomorrow)
        if reminders or shifts or events:
            print("Para mañana:")
            print("\n".join(f"• {item}" for item in (shifts + events + reminders)))
        else:
            print("No veo turnos, citas ni recordatorios registrados para mañana.")
        print("Las alarmas se integrarán más adelante; por ahora puedo dejarte un recordatorio.")
        return True
