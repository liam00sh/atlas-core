"""Resumen diario y consultas meteorológicas compartidas por CLI y Telegram.

El tiempo se consulta automáticamente mediante Open-Meteo, sin pedir permiso de
búsqueda web. La ubicación usa ATLAS_HOME_LOCATION y, mientras no haya ubicación
actual del dispositivo, Beneixama (Alicante) como residencia predeterminada.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import json
import os
import re
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from core.log_manager import error, info


def _norm(text: str) -> str:
    value = unicodedata.normalize("NFD", text.casefold())
    return " ".join("".join(c for c in value if unicodedata.category(c) != "Mn").split())


def _json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "Atlas/0.3 weather-service"})
    with urlopen(request, timeout=12) as response:  # nosec - endpoints públicos fijos
        return json.loads(response.read().decode("utf-8"))


def _home_location() -> str:
    return os.environ.get("ATLAS_HOME_LOCATION", "Beneixama").strip() or "Beneixama"




def _requested_location(text: str) -> str:
    """Extrae una ubicación explícita; si no existe, usa el domicilio configurado."""
    normalized = _norm(text).strip(" .!¡?¿")
    patterns = (
        r"\ben\s+([a-z0-9áéíóúüñ][a-z0-9áéíóúüñ .,'’-]{1,80})$",
        r"\bpara\s+([a-z0-9áéíóúüñ][a-z0-9áéíóúüñ .,'’-]{1,80})$",
        r"\bde\s+([a-z0-9áéíóúüñ][a-z0-9áéíóúüñ .,'’-]{1,80})$",
    )
    stop_words = {
        "hoy", "mañana", "manana", "esta tarde", "esta noche",
        "la semana que viene", "la proxima semana", "próxima semana",
        "luego", "ahora", "ahora mismo",
    }
    for pattern in patterns:
        match = re.search(pattern, normalized, re.IGNORECASE)
        if not match:
            continue
        candidate = " ".join(match.group(1).strip(" .,!¡?¿").split())
        candidate_norm = _norm(candidate)
        if candidate_norm in stop_words:
            continue
        candidate = re.sub(
            r"\s+(?:hoy|mañana|manana|esta tarde|esta noche|luego|ahora(?: mismo)?|la semana que viene|la proxima semana)$",
            "", candidate, flags=re.IGNORECASE,
        ).strip()
        if candidate:
            return candidate
    return _home_location()

def _weather_code(code: int | None) -> str:
    labels = {
        0: "cielo despejado", 1: "cielo principalmente despejado",
        2: "intervalos nubosos", 3: "cielo cubierto",
        45: "niebla", 48: "niebla con escarcha",
        51: "llovizna débil", 53: "llovizna moderada", 55: "llovizna intensa",
        61: "lluvia débil", 63: "lluvia moderada", 65: "lluvia intensa",
        71: "nieve débil", 73: "nieve moderada", 75: "nieve intensa",
        80: "chubascos débiles", 81: "chubascos moderados", 82: "chubascos fuertes",
        95: "tormentas", 96: "tormentas con granizo", 99: "tormentas fuertes con granizo",
    }
    return labels.get(code, "condiciones variables")


def _coordinates(location: str) -> tuple[float, float, str]:
    geo = _json("https://geocoding-api.open-meteo.com/v1/search?" + urlencode({
        "name": location,
        "count": 5,
        "language": "es",
        "format": "json",
        "countryCode": "ES",
    }))
    results = geo.get("results") or []
    if not results:
        raise ValueError(f"ubicación no encontrada: {location}")
    result = results[0]
    label = result.get("name") or location
    admin = result.get("admin1")
    if admin and admin.casefold() not in label.casefold():
        label = f"{label}, {admin}"
    return float(result["latitude"]), float(result["longitude"]), label


def _forecast(location: str) -> tuple[dict, str]:
    latitude, longitude, label = _coordinates(location)
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": ",".join([
            "temperature_2m", "apparent_temperature", "relative_humidity_2m",
            "precipitation", "weather_code", "wind_speed_10m", "wind_gusts_10m",
        ]),
        "hourly": ",".join([
            "temperature_2m", "apparent_temperature", "relative_humidity_2m",
            "precipitation_probability", "precipitation", "weather_code",
            "wind_speed_10m", "wind_gusts_10m",
        ]),
        "daily": ",".join([
            "weather_code", "temperature_2m_max", "temperature_2m_min",
            "apparent_temperature_max", "apparent_temperature_min",
            "sunrise", "sunset", "precipitation_sum",
            "precipitation_probability_max", "wind_speed_10m_max",
            "wind_gusts_10m_max",
        ]),
        "timezone": "Europe/Madrid",
        "forecast_days": 16,
    }
    forecast = _json("https://api.open-meteo.com/v1/forecast?" + urlencode(params))
    try:
        air = _json("https://air-quality-api.open-meteo.com/v1/air-quality?" + urlencode({
            "latitude": latitude,
            "longitude": longitude,
            "current": "european_aqi,pm10,pm2_5",
            "timezone": "Europe/Madrid",
        }))
        forecast["air_quality"] = air.get("current") or {}
    except Exception as exc:
        info(f"Tiempo: calidad del aire no disponible: {exc}")
    return forecast, label


def _daily_value(daily: dict, key: str, index: int):
    values = daily.get(key) or []
    return values[index] if index < len(values) else None


def _day_index(daily: dict, target_date) -> int:
    dates = daily.get("time") or []
    iso = target_date.isoformat()
    if iso not in dates:
        raise ValueError(f"fecha fuera del pronóstico: {iso}")
    return dates.index(iso)


def _fmt(value, unit: str = "", digits: int = 0) -> str:
    if value is None:
        return "—"
    number = round(float(value), digits)
    if digits == 0:
        number = int(number)
    return f"{number}{unit}"


def _aqi_label(value) -> str:
    if value is None:
        return "no disponible"
    value = float(value)
    if value <= 20: return "muy buena"
    if value <= 40: return "buena"
    if value <= 60: return "moderada"
    if value <= 80: return "mala"
    if value <= 100: return "muy mala"
    return "extremadamente mala"


def _describe_day(forecast: dict, label: str, target_date, prefix: str) -> str:
    daily = forecast.get("daily") or {}
    index = _day_index(daily, target_date)
    code = _daily_value(daily, "weather_code", index)
    tmax = _daily_value(daily, "temperature_2m_max", index)
    tmin = _daily_value(daily, "temperature_2m_min", index)
    rain = _daily_value(daily, "precipitation_probability_max", index)
    rainfall = _daily_value(daily, "precipitation_sum", index)
    wind = _daily_value(daily, "wind_speed_10m_max", index)
    gust = _daily_value(daily, "wind_gusts_10m_max", index)
    sunrise = _daily_value(daily, "sunrise", index)
    sunset = _daily_value(daily, "sunset", index)
    sunrise_text = sunrise[-5:] if isinstance(sunrise, str) else "—"
    sunset_text = sunset[-5:] if isinstance(sunset, str) else "—"
    return (
        f"{prefix} en {label}: {_weather_code(code)}, entre {_fmt(tmin, ' °C')} y "
        f"{_fmt(tmax, ' °C')}. Probabilidad máxima de lluvia: {_fmt(rain, '%')}; "
        f"precipitación prevista: {_fmt(rainfall, ' mm', 1)}. Viento máximo: "
        f"{_fmt(wind, ' km/h')} y rachas de hasta {_fmt(gust, ' km/h')}. "
        f"Amanecer a las {sunrise_text} y atardecer a las {sunset_text}."
    )


def _describe_period(forecast: dict, label: str, target_date, start_hour: int, end_hour: int, prefix: str) -> str:
    hourly = forecast.get("hourly") or {}
    times = hourly.get("time") or []
    indexes = []
    for index, raw in enumerate(times):
        try:
            dt = datetime.fromisoformat(raw)
        except (TypeError, ValueError):
            continue
        if dt.date() == target_date and start_hour <= dt.hour < end_hour:
            indexes.append(index)
    if not indexes:
        raise ValueError("franja horaria fuera del pronóstico")
    def values(key):
        source = hourly.get(key) or []
        return [source[i] for i in indexes if i < len(source) and source[i] is not None]
    temps = values("temperature_2m")
    rain = values("precipitation_probability")
    wind = values("wind_speed_10m")
    gust = values("wind_gusts_10m")
    codes = values("weather_code")
    code = max(set(codes), key=codes.count) if codes else None
    return (
        f"{prefix} en {label}: {_weather_code(code)}, temperaturas entre "
        f"{_fmt(min(temps) if temps else None, ' °C')} y {_fmt(max(temps) if temps else None, ' °C')}, "
        f"hasta {_fmt(max(rain) if rain else None, '%')} de probabilidad de lluvia, "
        f"viento de hasta {_fmt(max(wind) if wind else None, ' km/h')} y rachas de "
        f"{_fmt(max(gust) if gust else None, ' km/h')}."
    )


def _weather_answer(text: str, location: str) -> str | None:
    normalized = _norm(text).strip(" .!¡?¿")
    weather_terms = (
        "tiempo", "temperatura", "llover", "lluvia", "viento", "aire", "humedad",
        "amanecer", "atardecer", "calidad del aire", "pronostico", "prevision",
    )
    if not any(term in normalized for term in weather_terms):
        return None
    forecast, label = _forecast(location)
    now = datetime.now()
    today = now.date()
    tomorrow = today + timedelta(days=1)
    daily = forecast.get("daily") or {}

    if "calidad del aire" in normalized:
        air = forecast.get("air_quality") or {}
        aqi = air.get("european_aqi")
        return (
            f"La calidad del aire en {label} es {_aqi_label(aqi)} "
            f"(índice europeo {_fmt(aqi)}, PM2.5 {_fmt(air.get('pm2_5'), ' µg/m³', 1)} "
            f"y PM10 {_fmt(air.get('pm10'), ' µg/m³', 1)})."
        )

    if "semana que viene" in normalized or "proxima semana" in normalized:
        dates = daily.get("time") or []
        start = min(7, max(0, len(dates) - 1))
        end = min(start + 7, len(dates))
        rows = []
        for index in range(start, end):
            date = datetime.fromisoformat(dates[index]).date()
            rows.append(
                f"{date:%a %d}: {_weather_code(_daily_value(daily, 'weather_code', index))}, "
                f"{_fmt(_daily_value(daily, 'temperature_2m_min', index), ' °C')}/"
                f"{_fmt(_daily_value(daily, 'temperature_2m_max', index), ' °C')}, "
                f"lluvia {_fmt(_daily_value(daily, 'precipitation_probability_max', index), '%')}."
            )
        return f"Previsión para la próxima semana en {label}:\n" + "\n".join(rows)

    if "manana" in normalized:
        if "tarde" in normalized:
            return _describe_period(forecast, label, tomorrow, 15, 21, "Mañana por la tarde")
        if "noche" in normalized:
            return _describe_period(forecast, label, tomorrow, 21, 24, "Mañana por la noche")
        return _describe_day(forecast, label, tomorrow, "Mañana")

    if "esta tarde" in normalized or normalized.endswith(" tarde"):
        return _describe_period(forecast, label, today, 15, 21, "Esta tarde")
    if "esta noche" in normalized or normalized.endswith(" noche"):
        return _describe_period(forecast, label, today, 21, 24, "Esta noche")
    if "luego" in normalized:
        start = min(now.hour + 1, 22)
        return _describe_period(forecast, label, today, start, min(start + 4, 24), "Durante las próximas horas")

    current = forecast.get("current") or {}
    index = _day_index(daily, today)
    air = forecast.get("air_quality") or {}
    return (
        f"Ahora mismo en {label} hay {_fmt(current.get('temperature_2m'), ' °C', 1)}, "
        f"sensación de {_fmt(current.get('apparent_temperature'), ' °C', 1)} y "
        f"{_weather_code(current.get('weather_code'))}. Humedad: "
        f"{_fmt(current.get('relative_humidity_2m'), '%')}. Viento: "
        f"{_fmt(current.get('wind_speed_10m'), ' km/h')} con rachas de "
        f"{_fmt(current.get('wind_gusts_10m'), ' km/h')}. Hoy se esperan entre "
        f"{_fmt(_daily_value(daily, 'temperature_2m_min', index), ' °C')} y "
        f"{_fmt(_daily_value(daily, 'temperature_2m_max', index), ' °C')}, con hasta "
        f"{_fmt(_daily_value(daily, 'precipitation_probability_max', index), '%')} de lluvia. "
        f"Calidad del aire: {_aqi_label(air.get('european_aqi'))}."
    )


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

    def _handle_weather(self, text: str) -> bool:
        try:
            location = _requested_location(text)
            answer = _weather_answer(text, location)
        except (HTTPError, URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as exc:
            error(f"Tiempo: consulta fallida: {type(exc).__name__}: {exc}")
            print("No he podido consultar el tiempo ahora mismo. Prueba de nuevo en unos minutos.")
            return True
        except Exception as exc:
            error(f"Tiempo: error inesperado: {type(exc).__name__}: {exc}")
            print("No he podido consultar el tiempo ahora mismo. Prueba de nuevo en unos minutos.")
            return True
        if answer is None:
            return False
        info(f"Tiempo consultado automáticamente para {location}")
        print(answer)
        return True

    def _handle_daily_brief(self, text: str) -> bool:
        normalized = _norm(text).strip(" .!¡?¿")
        morning = normalized in {"buenos dias", "muy buenos dias", "buen dia"}
        night = normalized in {"buenas noches", "hasta manana", "me voy a dormir"}
        if not morning and not night:
            return False

        location = _home_location()
        user = getattr(self, "get_user", lambda: "")()
        name = str(user or "").strip()
        if morning:
            print(f"¡Buenos días{', ' + name if name else ''}! ☀️")
            try:
                weather = _weather_answer("qué tiempo hace hoy", location)
                if weather:
                    print(weather)
            except Exception as exc:
                error(f"Tiempo en resumen diario: {type(exc).__name__}: {exc}")
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
