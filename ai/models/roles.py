"""Configuración central de los roles de modelos de Atlas.

Los consumidores usan roles estables. Los nombres físicos solo viven aquí o
en variables de entorno; nunca forman parte del contrato de voz, Telegram o CLI.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import os


class ModelRole(StrEnum):
    FAST = "fast"
    REASONING = "reasoning"
    DEEP = "deep"
    EXTERNAL = "external"


@dataclass(frozen=True, slots=True)
class RoleModelDefinition:
    role: ModelRole
    provider: str
    model: str | None
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.role is ModelRole.EXTERNAL and self.enabled:
            raise ValueError("El rol external debe permanecer deshabilitado en esta fase.")
        if self.enabled and (not self.provider.strip() or not str(self.model or "").strip()):
            raise ValueError(f"El rol {self.role.value} necesita proveedor y modelo.")


class ModelRoleRegistry:
    """Registro definitivo fast/reasoning/deep con external deshabilitado."""

    DEFAULT_MODELS = {
        ModelRole.FAST: "qwen2.5:7b",
        ModelRole.REASONING: "qwen2.5:14b",
        ModelRole.DEEP: "qwen3:30b",
    }

    ENV_KEYS = {
        ModelRole.FAST: "ATLAS_AI_FAST_MODEL",
        ModelRole.REASONING: "ATLAS_AI_REASONING_MODEL",
        ModelRole.DEEP: "ATLAS_AI_DEEP_MODEL",
    }

    def __init__(self, definitions: list[RoleModelDefinition] | None = None) -> None:
        if definitions is None:
            definitions = [
                RoleModelDefinition(
                    role=role,
                    provider="ollama",
                    model=os.getenv(self.ENV_KEYS[role], default).strip() or default,
                )
                for role, default in self.DEFAULT_MODELS.items()
            ]
            definitions.append(
                RoleModelDefinition(ModelRole.EXTERNAL, "disabled", None, enabled=False)
            )
        self._definitions = {item.role: item for item in definitions}
        missing = set(ModelRole) - set(self._definitions)
        if missing:
            raise ValueError(f"Faltan roles de modelo: {sorted(item.value for item in missing)}")

    def resolve(self, role: ModelRole | str) -> RoleModelDefinition:
        return self._definitions[ModelRole(str(role))]

    def enabled_local_roles(self) -> tuple[ModelRole, ...]:
        return tuple(
            role for role in (ModelRole.FAST, ModelRole.REASONING, ModelRole.DEEP)
            if self._definitions[role].enabled
        )

    def as_dict(self) -> dict[str, dict[str, object]]:
        return {
            role.value: {
                "provider": item.provider,
                "model": item.model,
                "enabled": item.enabled,
            }
            for role, item in self._definitions.items()
        }

