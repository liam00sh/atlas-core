"""Carga local compartida del modelo Chatterbox Spanish (Spain)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys


REQUIRED_MODEL_FILES = (
    "ve.pt",
    "conds.pt",
    "grapheme_mtl_merged_expanded_v1.json",
    "s3gen_v3.pt",
    "t3_es_es.safetensors",
)


@dataclass(frozen=True, slots=True)
class ModelRoute:
    requested: Path
    effective: Path
    missing_requested: tuple[str, ...]
    missing_effective: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return not self.missing_effective


def missing_model_files(path: Path) -> tuple[str, ...]:
    return tuple(name for name in REQUIRED_MODEL_FILES if not (path / name).is_file())


def resolve_es_es_model_dir(model_dir: Path) -> ModelRoute:
    """Resuelve el checkout de pesos a la carpeta runtime ya ensamblada.

    La descarga regional contiene los pesos es-ES, pero el cargador oficial
    necesita además los artefactos base. La comparativa humana los reunió en
    ``models/runtime/chatterbox-es-es``; esta función reutiliza esa misma ruta.
    """
    requested = Path(model_dir).resolve()
    missing_requested = missing_model_files(requested)
    effective = requested
    if missing_requested:
        models_root = next(
            (path for path in (requested, *requested.parents) if path.name.casefold() == "models"),
            None,
        )
        candidates = (() if models_root is None else (models_root / "runtime" / "chatterbox-es-es",))
        effective = next(
            (candidate for candidate in candidates if candidate.is_dir() and not missing_model_files(candidate)),
            requested,
        )
    return ModelRoute(
        requested=requested,
        effective=effective,
        missing_requested=missing_requested,
        missing_effective=missing_model_files(effective),
    )


def cap_generation(model) -> None:
    """Aplica el mismo techo terminable usado en la comparativa validada."""
    original = model.t3.inference

    def bounded(*args, **kwargs):
        limit = int(getattr(model, "_atlas_max_new_tokens", 300))
        kwargs["max_new_tokens"] = min(int(kwargs.get("max_new_tokens", limit)), limit)
        return original(*args, **kwargs)

    model.t3.inference = bounded


def load_es_es_model(*, source: Path, model_dir: Path, device):
    source_path = Path(source).resolve() / "chatterbox" / "src"
    if not source_path.is_dir():
        raise FileNotFoundError(f"No existe el paquete Chatterbox es-ES: {source_path}")
    route = resolve_es_es_model_dir(model_dir)
    if not route.ready:
        missing = ", ".join(route.missing_effective)
        raise FileNotFoundError(
            f"Modelo es-ES incompleto en {route.effective}; faltan: {missing}. "
            f"Ruta solicitada: {route.requested}"
        )
    sys.path.insert(0, str(source_path))
    from chatterbox.tts import ChatterboxTTS

    model = ChatterboxTTS.from_local(
        route.effective,
        device,
        t3_filename="t3_es_es.safetensors",
        s3gen_filename="s3gen_v3.pt",
    )
    cap_generation(model)
    return model, route
