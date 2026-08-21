"""Audita una E2E guiada sin modificar ni publicar su evidencia privada."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import wave


KNOWN_RETRY_CASES = (2, 5, 10, 12)
CAP_HIT_SAMPLES = 106_560


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wav_metrics(path: Path) -> dict[str, object]:
    with wave.open(str(path), "rb") as wav:
        frames = wav.readframes(wav.getnframes())
        channels, width, rate, count = (
            wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getnframes()
        )
    if width != 2:
        return {"samples": count, "rate": rate, "duration_ms": count * 1000 / rate}
    import array
    values = array.array("h")
    values.frombytes(frames)
    mono = values[::channels]
    threshold = 16
    active = [i for i, value in enumerate(mono) if abs(value) > threshold]
    first = active[0] if active else count
    last = active[-1] if active else -1
    return {
        "samples": count,
        "rate": rate,
        "duration_ms": round(count * 1000 / rate, 3),
        "leading_quiet_ms": round(first * 1000 / rate, 3),
        "trailing_quiet_ms": round(max(0, count - last - 1) * 1000 / rate, 3),
    }


def audit(source: Path, retries: tuple[int, ...]) -> dict[str, object]:
    payload = json.loads(source.read_text(encoding="utf-8"))
    rows = []
    for case in payload.get("cases", []):
        index = int(case["index"])
        preserved = Path(case["audio_path"])
        generated = [Path(item) for item in case.get("generated_wav_paths") or []]
        replayed = [Path(item) for item in case.get("playback_paths") or []]
        preserved_hash = sha256(preserved) if preserved.is_file() else None
        generated_hashes = [sha256(item) for item in generated if item.is_file()]
        replayed_hashes = [sha256(item) for item in replayed if item.is_file()]
        metrics = wav_metrics(preserved) if preserved.is_file() else {}
        rows.append({
            "index": index,
            "case_id": case.get("case_id"),
            "human_functional": case.get("human_functional"),
            "notes": case.get("notes", ""),
            "stt_recovered_after_retry": index in retries,
            "playback_completed": case.get("playback_completed"),
            "preserved_equals_generated": bool(generated_hashes) and preserved_hash in generated_hashes,
            "generated_equals_replayed": generated_hashes == replayed_hashes,
            "wav": metrics,
            "fixed_110_token_cap_signature": metrics.get("samples") == CAP_HIT_SAMPLES,
            "intent": case.get("intent"),
            "side_effect": case.get("side_effect"),
            "confirmation_before": case.get("confirmation_before"),
            "confirmation_after": case.get("confirmation_after"),
        })
    partial = [row["index"] for row in rows if row["human_functional"] == "parcial"]
    cap_hits = [row["index"] for row in rows if row["fixed_110_token_cap_signature"]]
    return {
        "schema_version": 1,
        "source": str(source),
        "source_sha256": sha256(source),
        "original_evidence_modified": False,
        "completed": payload.get("completed"),
        "scope_completed": payload.get("scope_completed"),
        "rated_cases": sum(bool(case.get("rated")) for case in payload.get("cases", [])),
        "case_count": len(rows),
        "human_functional_counts": {
            "si": sum(row["human_functional"] == "s" for row in rows),
            "parcial": len(partial),
        },
        "partial_cases": partial,
        "known_stt_retry_cases": list(retries),
        "fixed_cap_signature_cases": cap_hits,
        "all_playbacks_completed": all(row["playback_completed"] is True for row in rows),
        "all_preserved_wavs_match_generated": all(row["preserved_equals_generated"] for row in rows),
        "all_generated_wavs_match_replayed": all(row["generated_equals_replayed"] for row in rows),
        "findings": {
            "tts_end_boundary": "El techo fijo de 110 tokens truncó habla real antes de añadir 80 ms de silencio.",
            "tts_start_boundary": "No había pre-roll protegido; el fundido de 5 ms podía atenuar el inicio real.",
            "playback": "No introdujo los cortes: generado, reproducido y preservado coinciden por SHA-256.",
            "reminder_case_8": "No persistió recordatorio; side_effect es nulo.",
            "social_case_5": "La coincidencia difusa de saludar absorbió Saluda a Lidia.",
            "telegram_cases_9_10": "No existía confirmación pendiente real; cancelar no tenía estado que limpiar.",
            "docker_case_11": "Falta el ejecutable local; el rechazo fue correcto.",
            "home_assistant_cases_6_7": "ON reprodujo desincronización física/Tuya frente a UI/API; OFF quedó coherente.",
        },
        "phase_status": "OPEN_PENDING_TARGETED_HUMAN_TTS_VALIDATION",
        "cases": rows,
    }


def markdown(report: dict[str, object]) -> str:
    lines = [
        "# Auditoría final E2E de voz",
        "",
        f"- Ejecución: {report['case_count']}/13 casos; {report['rated_cases']} valorados.",
        f"- Funcional humano: {report['human_functional_counts']}.",
        f"- Casos parciales: {report['partial_cases']}.",
        f"- Reintentos STT conocidos: {report['known_stt_retry_cases']} (el JSON conserva solo el intento aceptado).",
        f"- Firma del techo fijo de 110 tokens: {report['fixed_cap_signature_cases']}.",
        f"- Playback completo: {report['all_playbacks_completed']}.",
        f"- WAV preservado=generado: {report['all_preserved_wavs_match_generated']}.",
        f"- WAV generado=reproducido: {report['all_generated_wavs_match_replayed']}.",
        "",
        "## Conclusión",
        "",
        "Los cortes finales proceden del presupuesto fijo de generación, no de la reproducción. "
        "El silencio final se añadió después de perder el fonema. En el inicio faltaba pre-roll protegido. "
        "La Fase 6 permanece abierta hasta validar humanamente el mini-laboratorio TTS.",
        "",
        "## Estado funcional",
        "",
        "El recordatorio del caso 8 no se guardó. El saludo a Lidia se desvió al comando genérico. "
        "La confirmación de Telegram nunca quedó pendiente, por lo que cancelar no limpió un estado real. "
        "Docker falló de forma segura por ausencia del ejecutable. Home Assistant reprodujo en ON la "
        "desincronización física/Tuya frente a UI/API; OFF fue coherente.",
        "",
    ]
    lab = report.get("targeted_tts_lab")
    if isinstance(lab, dict):
        lines.extend((
            "## Mini-laboratorio TTS",
            "",
            f"Se generaron {lab['clips']} clips ciegos para {lab['cases']} casos y {lab['variants']} variantes. "
            f"El control fijo alcanzó el límite en {lab['fixed_limit_hits']}/{lab['cases']} casos; "
            f"el candidato dinámico en {lab['candidate_limit_hits']}/{lab['cases']}.",
            "La selección final no se automatiza: queda pendiente completar la revisión humana ciega.",
            "",
        ))
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--lab-manifest", type=Path)
    parser.add_argument("--known-retry-cases", default=",".join(map(str, KNOWN_RETRY_CASES)))
    args = parser.parse_args()
    retries = tuple(int(item) for item in args.known_retry_cases.split(",") if item.strip())
    report = audit(args.input.resolve(), retries)
    if args.lab_manifest:
        manifest = json.loads(args.lab_manifest.read_text(encoding="utf-8"))
        fixed = [row for row in manifest if row.get("variant") == "A_current_80_0_fixed110"]
        candidate = [row for row in manifest if row.get("variant") == "E_candidate"]
        report["targeted_tts_lab"] = {
            "manifest": str(args.lab_manifest.resolve()),
            "manifest_sha256": sha256(args.lab_manifest),
            "clips": len(manifest),
            "cases": len({row.get("case") for row in manifest}),
            "variants": len({row.get("variant") for row in manifest}),
            "fixed_limit_hits": sum(bool(row.get("reached_generation_limit")) for row in fixed),
            "candidate_limit_hits": sum(bool(row.get("reached_generation_limit")) for row in candidate),
            "candidate_policy": {
                "generation_tokens": "dynamic 120-260 per unit",
                "segmentation_max_chars": 120,
                "pre_roll_ms": 40,
                "end_padding_ms": 200,
            },
            "human_status": "PENDING_BLIND_REVIEW",
        }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_md.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"output_json": str(args.output_json), "output_md": str(args.output_md), "status": report["phase_status"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
