"""Registro pequeño y explícito de los modelos de IA conocidos por Atlas.

El registro conserva metadatos de selección; no consulta Ollama ni instala
modelos. La disponibilidad real sigue siendo responsabilidad del proveedor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import config


@dataclass(frozen=True, slots=True)
class ModelDefinition:
    """Modelo conocido y proveedor encargado de ejecutarlo."""

    name: str
    provider: str

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("El nombre del modelo no puede estar vacío.")
        if not self.provider.strip():
            raise ValueError("El proveedor del modelo no puede estar vacío.")


class ModelRegistry:
    """Resuelve modelos conocidos sin acoplar el núcleo a un proveedor."""

    DEFAULT_MODEL_NAME = "qwen2.5:7b"
    DEFAULT_PROVIDER_NAME = "ollama"

    def __init__(
        self,
        models: Iterable[ModelDefinition] | None = None,
        *,
        default_model_name: str | None = None,
    ) -> None:
        self._models: dict[str, ModelDefinition] = {}
        self.register(
            self.DEFAULT_MODEL_NAME,
            self.DEFAULT_PROVIDER_NAME,
        )

        for model in models or ():
            self.register(model.name, model.provider)

        configured_name = (
            default_model_name
            or config.AI_MODEL
            or self.DEFAULT_MODEL_NAME
        ).strip()
        configured_provider = (
            config.AI_PROVIDER or self.DEFAULT_PROVIDER_NAME
        ).strip()
        if configured_name not in self._models:
            self.register(configured_name, configured_provider)
        self._default_model_name = configured_name

    def register(
        self,
        model_name: str,
        provider: str,
        *,
        make_default: bool = False,
    ) -> ModelDefinition:
        """Registra un modelo; rechaza redefiniciones ambiguas."""

        definition = ModelDefinition(
            name=str(model_name).strip(),
            provider=str(provider).strip(),
        )
        if definition.name in self._models:
            raise ValueError(
                f"El modelo «{definition.name}» ya está registrado."
            )
        self._models[definition.name] = definition
        if make_default:
            self._default_model_name = definition.name
        return definition

    def resolve(self, model_name: str | None = None) -> ModelDefinition:
        """Devuelve el modelo solicitado o el predeterminado."""

        requested = (
            self._default_model_name
            if model_name is None
            else str(model_name).strip()
        )
        try:
            return self._models[requested]
        except KeyError as exc:
            raise KeyError(f"Modelo no registrado: {requested!r}") from exc

    def get_default_model_name(self) -> str:
        """Devuelve el identificador que deben pasar los consumidores."""

        return self.resolve().name

    def get_default_provider_name(self) -> str:
        """Devuelve el proveedor asociado al modelo predeterminado."""

        return self.resolve().provider

    def set_default(self, model_name: str) -> None:
        """Selecciona como predeterminado un modelo ya registrado."""

        definition = self.resolve(model_name)
        self._default_model_name = definition.name

    def list_models(
        self,
        *,
        provider: str | None = None,
    ) -> tuple[ModelDefinition, ...]:
        """Lista definiciones en orden de registro, con filtro opcional."""

        models = tuple(self._models.values())
        if provider is None:
            return models
        normalized_provider = str(provider).strip().casefold()
        return tuple(
            model
            for model in models
            if model.provider.casefold() == normalized_provider
        )
