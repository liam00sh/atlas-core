"""Genera una comparativa TTS A/B/C privada sin elegir ganador."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
from pathlib import Path
import random
import subprocess
import sys
import wave


ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools" / "chatterbox_comparison_worker.py"
CANDIDATES = ("v2", "v3", "es_es")
DISPLAY = {
    "v2": "Chatterbox Multilingual V2 (B1)",
    "v3": "Chatterbox Multilingual V3",
    "es_es": "Chatterbox Multilingual: Spanish (Spain)",
}
HUMAN_COLUMNS = (
    "blind_id", "frase", "parecido_daxter_1_5", "espanol_espana_1_5",
    "naturalidad_1_5", "ritmo_entonacion_1_5", "pronunciacion_1_5",
    "artefactos_cortes_1_5", "preferido_en_grupo", "notas",
)


def phrases(*, owner_name: str = "persona responsable", known_name: str = "persona conocida") -> list[str]:
    return [
        "La acción se ha completado correctamente.", "Esta función está disponible.",
        "La información está actualizada.", "La revisión ha terminado.",
        "La aplicación está funcionando.", "Esta explicación necesita más precisión.",
        "La pronunciación debería sonar natural.", "La emoción de la respuesta es correcta.",
        "El dispositivo está encendido.", "La opción está disponible.",
        "Hola, Daxter.", "Atlas está listo.", f"{known_name} está aquí.",
        f"{owner_name}, ya está terminado.", "Home Assistant está conectado.",
        "Docker está funcionando.", "Reinicia Telegram.", "GitHub está disponible.",
        "Google Drive está conectado.", "Wi-Fi está activado.",
        "Mañana a las 18:30 revisaré Atlas.", "Hoy es 13 de agosto de 2026.",
        "La temperatura es de 24 grados.",
        "Te explico brevemente cómo funciona y luego seguimos con lo demás.",
        "Cuando termine la comprobación, te avisaré para que puedas continuar.",
        "Si quieres, puedo revisar el estado y decirte exactamente qué está ocurriendo.",
        "¿La conversación funciona correctamente?", "¡Listo! La tercera opción cierra el resultado sin artefactos.",
    ]


def _write_player(path: Path, groups: list[dict]) -> None:
    cards = []
    for group in groups:
        buttons = "".join(
            f'<div class="choice"><strong>{label}</strong><audio controls preload="none" src="blind_audio/{group["files"][label]}"></audio></div>'
            for label in ("A", "B", "C")
        )
        cards.append(f'<section><h2>{html.escape(group["group_id"])}</h2><p>{html.escape(group["text"])}</p><div class="choices">{buttons}</div></section>')
    path.write_text("""<!doctype html><html lang="es"><meta charset="utf-8"><title>Comparación ciega de voz</title>
<style>body{font-family:system-ui;max-width:1100px;margin:auto;padding:24px;background:#f4f6f8;color:#17202a}section{background:white;padding:18px;margin:16px 0;border-radius:12px;box-shadow:0 2px 9px #0001}.choices{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.choice{display:grid;gap:8px}audio{width:100%}@media(max-width:750px){.choices{grid-template-columns:1fr}}</style>
<h1>Comparación ciega A/B/C</h1><p>Escucha las tres versiones de cada frase. Puntúa el CSV sin intentar identificar el motor. 5 es mejor; en artefactos, 5 significa completamente limpio.</p>""" + "".join(cards) + "</html>\n", encoding="utf-8")


def _run_worker(args, candidate: str, requests: list[dict]) -> dict:
    source = args.spain_source if candidate == "es_es" else args.general_source
    model_dir = args.spain_model_dir if candidate == "es_es" else args.general_model_dir
    result_path = args.output_dir / f".worker-{candidate}.json"
    result_path.unlink(missing_ok=True)
    completed = subprocess.run(
        [str(args.python), str(WORKER), "--candidate", candidate, "--source", str(source),
         "--model-dir", str(model_dir), "--reference", str(args.reference), "--result", str(result_path)],
        input=json.dumps(requests, ensure_ascii=False), text=True, encoding="utf-8",
        capture_output=True, timeout=args.timeout_seconds, check=False,
    )
    if completed.returncode not in (0, 2):
        raise RuntimeError(f"Worker {candidate} terminó con {completed.returncode}: {completed.stderr[-2000:]}")
    if not result_path.is_file():
        raise RuntimeError(f"Worker {candidate} no dejó métricas: {completed.stderr[-2000:]}")
    try:
        return json.loads(result_path.read_text(encoding="utf-8"))
    finally:
        result_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--general-source", type=Path, required=True)
    parser.add_argument("--spain-source", type=Path, required=True)
    parser.add_argument("--general-model-dir", type=Path, required=True)
    parser.add_argument("--spain-model-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260813)
    parser.add_argument("--timeout-seconds", type=float, default=7200)
    parser.add_argument("--owner-name", default="persona responsable")
    parser.add_argument("--known-name", default="persona conocida")
    args = parser.parse_args()
    for path in (args.python, args.reference, args.general_source, args.spain_source, args.general_model_dir, args.spain_model_dir):
        if not path.exists():
            parser.error(f"No existe: {path}")

    audio_dir = args.output_dir / "blind_audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    groups, key, requests_by_candidate = [], {}, {name: [] for name in CANDIDATES}
    for index, text in enumerate(phrases(owner_name=args.owner_name, known_name=args.known_name), 1):
        group_id = f"TTS{index:03d}"
        order = list(CANDIDATES)
        rng.shuffle(order)
        files = {}
        for label, candidate in zip(("A", "B", "C"), order):
            blind_id = f"{group_id}_{label}"
            filename = f"{blind_id}.wav"
            files[label] = filename
            key[blind_id] = {"candidate": candidate, "model": DISPLAY[candidate]}
            requests_by_candidate[candidate].append({
                "blind_id": blind_id, "text": text, "seed": args.seed + index,
                "output": str((audio_dir / filename).resolve()),
            })
        groups.append({"group_id": group_id, "text": text, "files": files})

    automatic = {"schema_version": 1, "winner": None, "metrics_are_decision": False, "candidates": {}}
    for candidate in CANDIDATES:
        automatic["candidates"][candidate] = _run_worker(args, candidate, requests_by_candidate[candidate])
    files_ok = all(row["success"] for data in automatic["candidates"].values() for row in data["results"])

    for group in groups:
        for label, filename in group["files"].items():
            path = audio_dir / filename
            if not path.is_file():
                continue
            with wave.open(str(path), "rb") as wav:
                duration = wav.getnframes() / wav.getframerate()
            key[f"{group['group_id']}_{label}"].update({
                "file": f"blind_audio/{filename}", "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "duration_seconds": round(duration, 4),
            })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_player(args.output_dir / "BLIND_TTS_PLAYER.html", groups)
    with (args.output_dir / "HUMAN_TTS_MODEL_COMPARISON.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HUMAN_COLUMNS)
        writer.writeheader()
        for group in groups:
            for label in ("A", "B", "C"):
                writer.writerow({"blind_id": f"{group['group_id']}_{label}", "frase": group["text"]})
    (args.output_dir / "BLIND_TTS_KEY.json").write_text(json.dumps({"schema_version": 1, "seed": args.seed, "mapping": key}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "schema_version": 1, "phase_6_closed": False, "human_winner": None,
        "reference_file": args.reference.name, "reference_sha256": hashlib.sha256(args.reference.read_bytes()).hexdigest(),
        "visible_normalization": "NFC y verbalización horaria común", "postprocess": "sin recorte inicial; recorte final conservador, 80 ms de margen y fade de 5 ms",
        "shared_controls": {"language_id": "es", "exaggeration": 0.45, "cfg_weight": 0.35, "temperature": 0.8},
        "generation_safety": "techo común por longitud: min(250, max(90, caracteres*2.0)); sustituye el límite upstream fijo en 1000 y marca salidas que rozan el techo",
        "control_difference": "V2/V3 general admiten repetition_penalty=2.0, min_p=0.05 y top_p=1.0; el cargador oficial es-ES no expone esos controles.",
        "groups": groups, "all_audio_generated": files_ok,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "automatic_metrics.json").write_text(json.dumps(automatic, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "COMPARATIVA.md").write_text("""# Comparativa ciega B1 / V3 / Spanish (Spain)\n\nLa Fase 6 sigue abierta. No hay ganador automático ni humano.\n\n## Evidencia humana B1 previa\n\nLas 24 muestras B1 ya fueron escuchadas y no se repiten. La identidad de Daxter se conserva razonablemente, pero el español peninsular es insuficiente. Se priorizan las terminaciones problemáticas, los términos ingleses y los cortes observados.\n\n## Candidatos\n\n- Chatterbox Multilingual V2 (B1): referencia reproducible.\n- Chatterbox Multilingual V3: checkpoint multilingüe general.\n- Chatterbox Multilingual: Spanish (Spain): ajuste monolingüe/regional del Single Language Pack; no se etiqueta como “V3 es-ES”.\n\nLos tres usan la misma referencia Daxter, textos, idioma, semillas y postproceso. El cargador oficial es-ES no expone todos los controles de muestreo del cargador multilingüe; la diferencia está declarada en `manifest.json`.\n\nLas métricas automáticas son diagnósticas y no deciden. La selección corresponde a la persona evaluadora tras escuchar A/B/C.\n""", encoding="utf-8")
    return 0 if files_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
