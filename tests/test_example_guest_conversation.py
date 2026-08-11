from contextlib import redirect_stdout
from datetime import datetime, timedelta
from io import StringIO

import core.atlas_daily_brief as daily_brief
from core.atlas_daily_brief import (
    _requested_location,
    _seasonal_month_answer,
    _weather_answer,
)
from core.atlas_social import AtlasSocialMixin
from telegram_interface.core_adapter import AtlasCoreAdapter


def test_weather_without_location_uses_home_location(monkeypatch):
    monkeypatch.setenv("ATLAS_HOME_LOCATION", "VillaEjemplo")
    assert _requested_location("Me puedes decir si en agosto será igual en mi localidad?") == "VillaEjemplo"


def test_august_request_does_not_fake_current_forecast():
    answer = _seasonal_month_answer(
        "qué tiempo hará en agosto",
        "VillaEjemplo, Provincia Ejemplo",
        now=datetime(2026, 7, 31, 12, 0),
    )
    assert answer is not None
    assert "no existe una previsión diaria fiable" in answer


def test_weather_with_explicit_location_uses_that_location():
    assert _requested_location("qué tiempo hace en Madrid mañana") == "madrid"
    assert _requested_location("qué tiempo hará en agosto en Valencia") == "valencia"


def _fake_forecast(now: datetime) -> dict:
    dates = [(now.date() + timedelta(days=index)).isoformat() for index in range(16)]
    return {
        "current": {
            "temperature_2m": 24.5,
            "apparent_temperature": 25,
            "relative_humidity_2m": 50,
            "weather_code": 0,
            "wind_speed_10m": 8,
            "wind_gusts_10m": 12,
        },
        "daily": {
            "time": dates,
            "weather_code": [0] * 16,
            "temperature_2m_min": [18] * 16,
            "temperature_2m_max": [30] * 16,
            "precipitation_probability_max": [5] * 16,
            "precipitation_sum": [0] * 16,
            "wind_speed_10m_max": [10] * 16,
            "wind_gusts_10m_max": [15] * 16,
            "sunrise": [f"{day}T07:00" for day in dates],
            "sunset": [f"{day}T21:00" for day in dates],
        },
        "air_quality": {"european_aqi": 20},
    }


def test_today_tomorrow_and_date_inside_forecast_use_simulated_data(monkeypatch):
    now = datetime(2026, 7, 31, 12, 0)
    monkeypatch.setattr(
        daily_brief,
        "_forecast",
        lambda location: (_fake_forecast(now), "VillaEjemplo, Provincia Ejemplo"),
    )

    today = _weather_answer("qué tiempo hace hoy", "VillaEjemplo", now=now)
    tomorrow = _weather_answer("qué tiempo hará mañana", "VillaEjemplo", now=now)
    dated = _weather_answer("qué tiempo hará el 5 de agosto", "VillaEjemplo", now=now)

    assert "Ahora mismo en VillaEjemplo" in today
    assert "Mañana en VillaEjemplo" in tomorrow
    assert "El 05/08/2026 en VillaEjemplo" in dated


def test_future_date_outside_forecast_does_not_call_network(monkeypatch):
    monkeypatch.setattr(
        daily_brief,
        "_forecast",
        lambda _location: (_ for _ in ()).throw(AssertionError("network path")),
    )
    answer = _weather_answer(
        "qué tiempo hará el 20 de agosto",
        "VillaEjemplo",
        now=datetime(2026, 7, 31, 12, 0),
    )
    assert "no existe una previsión diaria fiable" in answer


def test_climatology_is_not_presented_as_a_current_forecast():
    answer = _seasonal_month_answer(
        "cómo es el clima habitual en agosto",
        "VillaEjemplo",
        now=datetime(2026, 1, 15, 12, 0),
    )
    assert "tendencia climática habitual" in answer
    assert "no una previsión exacta" in answer


def test_non_weather_month_mention_is_not_weather_intent(monkeypatch):
    monkeypatch.setattr(
        daily_brief,
        "_forecast",
        lambda _location: (_ for _ in ()).throw(AssertionError("network path")),
    )
    assert _weather_answer(
        "el cumpleaños de Carla es en agosto",
        "VillaEjemplo",
        now=datetime(2026, 7, 31, 12, 0),
    ) is None


def test_quick_greeting_has_variation():
    values = {AtlasCoreAdapter.quick_response("Hola") for _ in range(20)}
    assert len(values) >= 2


class _Repo:
    def __init__(self):
        self.people = {}
    def _read(self):
        return {
            "people": {
                "norberto": {
                    "display_name": "Norberto",
                    "facts": [{"fact_type": "location", "value": "Buenos Aires"}],
                }
            },
            "relations": {
                "alex::norberto": {
                    "target_person_id": "norberto",
                    "level": 2,
                    "active": True,
                }
            },
        }
    def find_person(self, name):
        class P:
            person_id = "alex"
        return P() if name.casefold() == "alex" else None


class _Atlas(AtlasSocialMixin):
    friends_repository = _Repo()
    def _get_current_conversation_user(self):
        return "Alex"
    def get_user(self):
        return "Alex"


def test_friend_name_followup_is_understood():
    atlas = _Atlas()
    output = StringIO()
    with redirect_stdout(output):
        assert atlas._handle_friend_fact_conversation("Cómo se llama mi amigo argentino?") is True
    assert "Norberto" in output.getvalue()
