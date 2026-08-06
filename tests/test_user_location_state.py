from __future__ import annotations

from datetime import datetime, timedelta

from core.atlas_daily import AtlasDailyMixin, DailyLifeStorage
from core.atlas_daily_brief import AtlasDailyBriefMixin
from core import atlas_daily_brief


class _Users:
    def __init__(self, profiles):
        self.profiles = profiles

    def get_profile(self, user):
        return dict(self.profiles.get(user, {}))


class _LocationAtlas(AtlasDailyMixin, AtlasDailyBriefMixin):
    def __init__(self, path, profiles):
        self.current_user = "Nora"
        self.users = _Users(profiles)
        self.daily_storage = DailyLifeStorage(path)
        self._daily_session_state = {}
        self._daily_ready = True

    def get_user(self):
        return self.current_user


def test_temporary_locations_are_isolated_and_replaceable(tmp_path):
    atlas = _LocationAtlas(
        tmp_path / "state.json",
        {"Nora": {"location": "Villa Norte"}, "Teo": {"location": "Villa Sur"}},
    )

    assert atlas._handle_user_location("Estoy en Puerto Azul unos días")
    assert atlas._resolve_user_location("Nora") == ("Puerto Azul", "ubicación temporal")
    assert atlas._resolve_user_location("Teo") == ("Villa Sur", "domicilio habitual")

    atlas.current_user = "Teo"
    assert atlas._handle_user_location("Ahora estoy en Monte Claro")
    assert atlas._resolve_user_location("Teo") == ("Monte Claro", "ubicación temporal")
    assert atlas._resolve_user_location("Nora")[0] == "Puerto Azul"


def test_clear_and_expired_temporary_location_fall_back_to_habitual(tmp_path):
    atlas = _LocationAtlas(tmp_path / "state.json", {"Nora": {"location": "Villa Norte"}})
    atlas._set_temporary_location("Nora", "Puerto Azul")
    assert atlas._handle_user_location("borra mi ubicación temporal")
    assert atlas._resolve_user_location("Nora") == ("Villa Norte", "domicilio habitual")

    def expire(data):
        user = data.setdefault("users", {}).setdefault("nora", {"display_name": "Nora"})
        user["temporary_location"] = {
            "place": "Monte Claro",
            "updated_at": datetime.now().astimezone().isoformat(),
            "expires_at": (datetime.now().astimezone() - timedelta(seconds=1)).isoformat(),
        }

    atlas.daily_storage.update(expire)
    assert atlas._resolve_user_location("Nora") == ("Villa Norte", "domicilio habitual")


def test_ambiguous_house_reference_is_not_persisted(tmp_path, capsys):
    atlas = _LocationAtlas(tmp_path / "state.json", {"Nora": {"location": "Villa Norte"}})
    assert atlas._handle_user_location("He venido a casa de Teo unos días")
    assert "¿En qué localidad" in capsys.readouterr().out
    assert atlas._temporary_location_record("Nora") is None

    assert atlas._handle_user_location("Puerto Azul")
    assert atlas._resolve_user_location("Nora") == ("Puerto Azul", "ubicación temporal")


def test_weather_priority_and_origin_explanation_do_not_repeat_tool_call(tmp_path, monkeypatch, capsys):
    atlas = _LocationAtlas(tmp_path / "state.json", {"Nora": {"location": "Villa Norte"}})
    atlas._set_temporary_location("Nora", "Puerto Azul")
    calls = []

    def fake_weather(text, location):
        calls.append(location)
        return f"Tiempo en {location}"

    monkeypatch.setattr("core.atlas_daily_brief._weather_answer", fake_weather)
    assert atlas._handle_weather("Dime el tiempo")
    assert calls == ["Puerto Azul"]
    assert atlas._handle_weather("¿Por qué me das el tiempo de Puerto Azul?")
    assert "ubicación temporal" in capsys.readouterr().out
    assert calls == ["Puerto Azul"]
    assert atlas._handle_weather("¿Qué tiempo hace en Monte Claro?")
    assert calls == ["Puerto Azul", "monte claro"]
    assert atlas._handle_weather("¿Por qué me das el tiempo de Puerto Azul?")
    output = capsys.readouterr().out
    assert "petición explícita" in output
    assert "No fue puerto azul" in output
    assert calls == ["Puerto Azul", "monte claro"]


def test_casual_message_does_not_change_location(tmp_path):
    atlas = _LocationAtlas(tmp_path / "state.json", {"Nora": {"location": "Villa Norte"}})
    assert not atlas._handle_user_location("Me gusta pasear cuando estoy de vacaciones")
    assert not atlas._handle_user_location("Estoy en desacuerdo con esa idea")
    assert atlas._temporary_location_record("Nora") is None


def test_weather_result_is_reused_without_duplicate_calls(monkeypatch):
    atlas_daily_brief._clear_weather_cache()
    calls = []
    monkeypatch.setattr(
        atlas_daily_brief,
        "_coordinates",
        lambda location: (1.0, 2.0, location.title()),
    )

    def fake_json(url):
        calls.append(url)
        return {"current": {}}

    monkeypatch.setattr(atlas_daily_brief, "_json", fake_json)
    first = atlas_daily_brief._forecast("Puerto Azul")
    second = atlas_daily_brief._forecast("puerto azul")
    assert first == second
    assert len(calls) == 2  # previsión y aire, una sola vez cada una
