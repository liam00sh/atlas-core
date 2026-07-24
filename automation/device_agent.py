"""
Proyecto Atlas
Archivo: automation/device_agent.py

Contrato abstracto para agentes instalados en PCs, móviles y otros dispositivos.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class AgentExecutionRequest:
    device_id: str
    requester_user_id: str
    capability: str
    parameters: Mapping[str, object]
    correlation_id: str


@dataclass(frozen=True)
class AgentExecutionResult:
    ok: bool
    capability: str
    result: Mapping[str, object]
    error: str = ""


class BaseDeviceAgent(ABC):
    @abstractmethod
    def device_id(self) -> str:
        """Devuelve el identificador estable del dispositivo."""

    @abstractmethod
    def capabilities(self) -> frozenset[str]:
        """Devuelve las capacidades cerradas expuestas por el agente."""

    @abstractmethod
    def execute(self, request: AgentExecutionRequest) -> AgentExecutionResult:
        """Ejecuta una capacidad registrada y devuelve un resultado estructurado."""

    @abstractmethod
    def revoke(self) -> None:
        """Revoca inmediatamente el agente y rechaza nuevas operaciones."""
