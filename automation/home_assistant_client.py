"""Cliente seguro de Home Assistant con contrato sustituible."""

from __future__ import annotations

import json
import ssl
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable
from urllib import error, request

from automation.home_assistant_models import HomeEntityState


class HomeAssistantErrorCode(StrEnum):
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    SERVER = "server_error"
    TIMEOUT = "timeout"
    CONNECTION = "connection_error"
    INVALID_JSON = "invalid_json"
    INVALID_RESPONSE = "invalid_response"


class HomeAssistantClientError(RuntimeError):
    def __init__(self, code: HomeAssistantErrorCode | str, message: str) -> None:
        self.code = str(code)
        super().__init__(message)


class BaseHomeAssistantClient(ABC):
    """Contrato común para el simulador y el cliente HTTP real."""

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    def ping(self) -> bool:
        return self.is_available()

    @abstractmethod
    def get_state(self, entity_id: str) -> HomeEntityState:
        raise NotImplementedError

    @abstractmethod
    def call_service(
        self,
        domain: str,
        service: str,
        *,
        entity_id: str,
        data: dict[str, Any] | None = None,
    ) -> HomeEntityState:
        raise NotImplementedError


HomeAssistantTransport = BaseHomeAssistantClient


@dataclass(slots=True)
class HomeAssistantHttpClient(BaseHomeAssistantClient):
    base_url: str
    token: str
    timeout_seconds: float = 10.0
    verify_ssl: bool = False
    read_attempts: int = 2
    retry_delay_seconds: float = 0.5
    sleep: Callable[[float], None] = field(default=time.sleep, repr=False)

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        if not self.base_url:
            raise ValueError("base_url no puede estar vacío.")
        if not self.token:
            raise ValueError("token no puede estar vacío.")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds debe ser mayor que cero.")
        if self.read_attempts < 1 or self.read_attempts > 2:
            raise ValueError("read_attempts debe estar entre 1 y 2.")

    def _ssl_context(self):
        if not self.base_url.lower().startswith("https://"):
            return None
        if self.verify_ssl:
            return ssl.create_default_context()
        return ssl._create_unverified_context()

    def _translate_error(self, exc: BaseException) -> HomeAssistantClientError:
        if isinstance(exc, error.HTTPError):
            mapping = {
                401: HomeAssistantErrorCode.UNAUTHORIZED,
                403: HomeAssistantErrorCode.FORBIDDEN,
                404: HomeAssistantErrorCode.NOT_FOUND,
            }
            code = mapping.get(
                exc.code,
                HomeAssistantErrorCode.SERVER
                if 500 <= exc.code <= 599
                else HomeAssistantErrorCode.INVALID_RESPONSE,
            )
            return HomeAssistantClientError(code, f"Home Assistant devolvió HTTP {exc.code}.")

        reason = exc.reason if isinstance(exc, error.URLError) else exc
        if isinstance(reason, TimeoutError) or "timed out" in str(reason).casefold():
            return HomeAssistantClientError(
                HomeAssistantErrorCode.TIMEOUT,
                "La conexión con Home Assistant agotó el tiempo de espera.",
            )
        return HomeAssistantClientError(
            HomeAssistantErrorCode.CONNECTION,
            "No se pudo conectar con Home Assistant.",
        )

    def _request_once(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        body = None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")

        req = request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        kwargs: dict[str, Any] = {"timeout": self.timeout_seconds}
        context = self._ssl_context()
        if context is not None:
            kwargs["context"] = context

        try:
            with request.urlopen(req, **kwargs) as response:
                raw = response.read().decode("utf-8")
        except (error.HTTPError, error.URLError, TimeoutError, OSError) as exc:
            raise self._translate_error(exc) from exc

        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise HomeAssistantClientError(
                HomeAssistantErrorCode.INVALID_JSON,
                "Home Assistant devolvió JSON no válido.",
            ) from exc

    def _read_request(self, path: str) -> Any:
        last_error: HomeAssistantClientError | None = None
        for attempt in range(self.read_attempts):
            try:
                return self._request_once("GET", path)
            except HomeAssistantClientError as exc:
                last_error = exc
                retryable = exc.code in {
                    str(HomeAssistantErrorCode.TIMEOUT),
                    str(HomeAssistantErrorCode.CONNECTION),
                    str(HomeAssistantErrorCode.SERVER),
                }
                if not retryable or attempt + 1 >= self.read_attempts:
                    raise
                self.sleep(self.retry_delay_seconds)
        assert last_error is not None
        raise last_error

    def is_available(self) -> bool:
        response = self._read_request("/api/")
        return isinstance(response, dict) and bool(response.get("message"))

    def get_state(self, entity_id: str) -> HomeEntityState:
        data = self._read_request(f"/api/states/{entity_id}")
        if not isinstance(data, dict) or "entity_id" not in data or "state" not in data:
            raise HomeAssistantClientError(
                HomeAssistantErrorCode.INVALID_RESPONSE,
                "Home Assistant devolvió un estado incompleto.",
            )
        return HomeEntityState(
            entity_id=str(data["entity_id"]),
            state=str(data["state"]),
            attributes=dict(data.get("attributes", {})),
            last_changed=str(data.get("last_changed")) if data.get("last_changed") else None,
            last_updated=str(data.get("last_updated")) if data.get("last_updated") else None,
        )

    def list_states(self) -> list[HomeEntityState]:
        """Lista estados para diagnósticos de solo lectura, sin exponer el token."""
        data = self._read_request("/api/states")
        if not isinstance(data, list):
            raise HomeAssistantClientError(
                HomeAssistantErrorCode.INVALID_RESPONSE,
                "Home Assistant no devolvió una lista de estados.",
            )
        return [
            HomeEntityState(
                entity_id=str(item["entity_id"]), state=str(item["state"]),
                attributes=dict(item.get("attributes", {})),
                last_changed=str(item.get("last_changed")) if item.get("last_changed") else None,
                last_updated=str(item.get("last_updated")) if item.get("last_updated") else None,
            )
            for item in data
            if isinstance(item, dict) and "entity_id" in item and "state" in item
        ]

    def call_service(
        self,
        domain: str,
        service: str,
        *,
        entity_id: str,
        data: dict[str, Any] | None = None,
    ) -> HomeEntityState:
        payload = {"entity_id": entity_id, **dict(data or {})}
        response = self._request_once(
            "POST",
            f"/api/services/{domain}/{service}",
            payload,
        )
        if isinstance(response, list):
            for item in reversed(response):
                if isinstance(item, dict) and item.get("entity_id") == entity_id:
                    return HomeEntityState(
                        entity_id=entity_id,
                        state=str(item.get("state", "unknown")),
                        attributes=dict(item.get("attributes", {})),
                        last_changed=str(item.get("last_changed")) if item.get("last_changed") else None,
                        last_updated=str(item.get("last_updated")) if item.get("last_updated") else None,
                    )
        return self.get_state(entity_id)

    def create_or_update_time_automation(
        self,
        *,
        automation_id: str,
        alias: str,
        entity_id: str,
        start_time: str,
        end_time: str,
        enabled: bool = True,
    ) -> dict[str, Any]:
        payload = {
            "alias": alias,
            "description": "Creada y gestionada por Atlas.",
            "mode": "single",
            "trigger": [
                {"platform": "time", "at": start_time},
                {"platform": "time", "at": end_time},
            ],
            "condition": [],
            "action": [
                {
                    "choose": [
                        {
                            "conditions": [
                                {
                                    "condition": "template",
                                    "value_template": (
                                        "{{ trigger.now.strftime('%H:%M') == '"
                                        + start_time[:5]
                                        + "' }}"
                                    ),
                                }
                            ],
                            "sequence": [
                                {
                                    "service": "switch.turn_on",
                                    "target": {"entity_id": entity_id},
                                }
                            ],
                        }
                    ],
                    "default": [
                        {
                            "service": "switch.turn_off",
                            "target": {"entity_id": entity_id},
                        }
                    ],
                }
            ],
        }
        try:
            response = self._request_once(
                "POST",
                f"/api/config/automation/config/{automation_id}",
                payload,
            )
        except HomeAssistantClientError as exc:
            # Home Assistant puede guardar correctamente la automatización y,
            # aun así, responder 404 en este endpoint según la versión/configuración.
            # No tratamos ese 404 como fallo definitivo.
            if exc.code != str(HomeAssistantErrorCode.NOT_FOUND):
                raise
            response = {
                "accepted": True,
                "warning": "home_assistant_returned_404_after_save",
            }

        try:
            self.call_service(
                "automation",
                "turn_on" if enabled else "turn_off",
                entity_id=f"automation.{automation_id}",
            )
        except HomeAssistantClientError as exc:
            if exc.code != str(HomeAssistantErrorCode.NOT_FOUND):
                raise

        return response if isinstance(response, dict) else {"accepted": True}

    def set_automation_enabled(
        self,
        automation_id: str,
        enabled: bool,
    ) -> HomeEntityState:
        return self.call_service(
            "automation",
            "turn_on" if enabled else "turn_off",
            entity_id=f"automation.{automation_id}",
        )

    def create_one_shot_turn_off_automation(
        self,
        *,
        automation_id: str,
        alias: str,
        entity_id: str,
        delay_minutes: int,
    ) -> dict[str, Any]:
        payload = {
            "alias": alias,
            "description": "Temporizador de apagado creado por Atlas.",
            "mode": "restart",
            "trigger": [],
            "condition": [],
            "action": [
                {
                    "delay": {
                        "minutes": int(delay_minutes),
                    }
                },
                {
                    "service": "switch.turn_off",
                    "target": {"entity_id": entity_id},
                },
            ],
        }

        try:
            response = self._request_once(
                "POST",
                f"/api/config/automation/config/{automation_id}",
                payload,
            )
        except HomeAssistantClientError as exc:
            if exc.code != str(HomeAssistantErrorCode.NOT_FOUND):
                raise
            response = {
                "accepted": True,
                "warning": "home_assistant_returned_404_after_save",
            }

        try:
            self.call_service(
                "automation",
                "trigger",
                entity_id=f"automation.{automation_id}",
                data={"skip_condition": True},
            )
        except HomeAssistantClientError as exc:
            if exc.code != str(HomeAssistantErrorCode.NOT_FOUND):
                raise

        return response if isinstance(response, dict) else {"accepted": True}

