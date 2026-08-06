"""Diagnóstico local de STT sin descargar modelos ni exponer rutas privadas."""
from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
from time import perf_counter

from voice.stt import (
    FasterWhisperSTTProvider,
    STTConfig,
    _windows_dll_available,
    find_local_faster_whisper_model,
    resolve_stt_backend,
)


@dataclass(frozen=True, slots=True)
class Diagnostic:
    status: str
    name: str
    detail: str


def _package(name: str) -> Diagnostic:
    if importlib.util.find_spec(name.replace("-", "_")) is None:
        return Diagnostic("ERROR", name, "no instalado")
    try:
        version = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        version = "versión no identificada"
    return Diagnostic("OK", name, version)


def collect_stt_diagnostics(config: STTConfig | None = None, *, load_model: bool = False) -> list[Diagnostic]:
    config = config or STTConfig.from_env()
    checks = [
        Diagnostic("OK", "Python", sys.version.split()[0]),
        Diagnostic("OK" if shutil.which("ffmpeg") else "ERROR", "FFmpeg", "disponible" if shutil.which("ffmpeg") else "no encontrado en PATH"),
        _package("faster-whisper"),
        _package("ctranslate2"),
    ]
    try:
        import ctranslate2  # type: ignore[import-not-found]

        devices = int(ctranslate2.get_cuda_device_count())
        checks.append(Diagnostic("OK" if devices else "WARNING", "GPU CUDA", f"{devices} dispositivo(s) detectado(s)"))
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        checks.append(Diagnostic("WARNING", "GPU CUDA", f"no disponible ({type(exc).__name__})"))
    for library in ("cublas64_12.dll", "cudnn64_9.dll"):
        available = _windows_dll_available(library)
        checks.append(Diagnostic("OK" if available else "WARNING", library, "disponible" if available else "no accesible desde PATH"))
    backend = resolve_stt_backend(config)
    detail = f"{backend.device}/{backend.compute_type}"
    if backend.fallback_reason:
        detail += f"; fallback: {backend.fallback_reason}"
    checks.append(Diagnostic("WARNING" if backend.fallback_reason else "OK", "Backend activo", detail))
    local_model = find_local_faster_whisper_model(config)
    checks.append(Diagnostic("OK" if local_model else "WARNING", "Modelo local", "encontrado" if local_model else "no encontrado; las descargas siguen desactivadas"))
    variables = (
        "ATLAS_STT_MODEL", "ATLAS_STT_DEVICE", "ATLAS_STT_COMPUTE_TYPE",
        "ATLAS_STT_TIMEOUT", "ATLAS_STT_MAX_AUDIO_SECONDS",
        "ATLAS_STT_LANGUAGE_HINT", "ATLAS_STT_ALLOW_MODEL_DOWNLOAD",
    )
    import os
    configured = sum(bool(os.environ.get(name, "").strip()) for name in variables)
    checks.append(Diagnostic("OK" if configured == len(variables) else "WARNING", "Configuración", f"{configured}/{len(variables)} variables definidas; se usan valores seguros para el resto"))
    free_gib = shutil.disk_usage(Path.cwd().anchor or Path.cwd()).free / (1024 ** 3)
    checks.append(Diagnostic("OK" if free_gib >= 5 else "WARNING", "Disco", f"{free_gib:.1f} GiB libres"))
    provider = FasterWhisperSTTProvider(config)
    checks.append(Diagnostic("OK" if provider.is_available() else "WARNING", "Proveedor", "activo" if provider.is_available() else "inactivo hasta disponer de un modelo local"))
    if load_model:
        if not provider.is_available():
            checks.append(Diagnostic("WARNING", "Carga del modelo", "omitida: modelo local no disponible"))
        else:
            started = perf_counter()
            try:
                provider._get_model()
            except (OSError, RuntimeError, ValueError) as exc:
                checks.append(Diagnostic("ERROR", "Carga del modelo", f"falló ({type(exc).__name__})"))
            else:
                checks.append(Diagnostic("OK", "Carga del modelo", f"{perf_counter() - started:.2f} s"))
    else:
        checks.append(Diagnostic("WARNING", "Carga del modelo", "no medida; usa --load-model para probar sin descargar"))
    return checks


def nvidia_summary() -> str | None:
    command = shutil.which("nvidia-smi")
    if not command:
        return None
    try:
        result = subprocess.run(
            [command, "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5, check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() or None
