"""Batería común y utilidades de benchmark para motores de voz locales."""

from __future__ import annotations

import csv
import json
import time
import wave
from pathlib import Path


BATTERY = (
    ("01_neutral", "Atlas está listo. Todo funciona con normalidad."),
    ("02_sonriente", "¡Hola, REDACTED_2c7b6821719d! Me alegra verte por aquí."),
    ("03_travieso", "Je, je... seguro que este botón no hace nada peligroso."),
    ("04_sorprendido", "¡¿Qué?! ¡Eso sí que no me lo esperaba!"),
    ("05_emocionado", "¡Vamos, Jak! ¡Esta aventura acaba de empezar!"),
    ("06_asustado", "Espera, espera... ¿has oído ese ruido detrás de nosotros?"),
    ("07_enfadado", "¡Eh! ¡Devuélveme eso ahora mismo!"),
    ("08_curioso", "Oye, Atlas, ¿cómo funciona exactamente ese cacharro?"),
    ("09_confiado", "Tranquilo, lo tengo todo bajo control."),
    ("10_determinado", "No nos rendiremos; encontraremos una salida."),
    ("11_jugueton", "A que no me pillas, Jak. ¡Vamos, inténtalo!"),
    ("12_numeros_nombres", "REDACTED_2c7b6821719d y REDACTED_bc04a68d9192 probarán Atlas el 9 de agosto de 2026, a las 18:45, con 1.300 muestras."),
    ("13_larga", "Atlas procesa la petición localmente, conserva los permisos del núcleo y, si la voz principal falla, utiliza una alternativa española sin repetir acciones ni ocultar el error."),
)


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / handle.getframerate()


def write_results(output_dir: Path, engine: str, rows: list[dict], metadata: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "benchmark.json").open("w", encoding="utf-8") as handle:
        json.dump({"engine": engine, "metadata": metadata, "runs": rows}, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    fields = ("case_id", "text", "output_file", "generation_seconds", "audio_seconds", "rtf", "peak_vram_mb", "error")
    with (output_dir / "benchmark.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


class Timer:
    def __enter__(self):
        self.started = time.perf_counter()
        return self

    def __exit__(self, *_):
        self.seconds = time.perf_counter() - self.started
