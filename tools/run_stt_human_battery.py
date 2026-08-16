"""Batería STT humana reanudable; inspecciona rutas sin ejecutar acciones."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unicodedata
import wave


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.evaluate_stt_conversation_battery import write_reports
from voice.microphone import ManualMicrophoneRecorder
from voice.stt import AudioConverter, FasterWhisperSTTProvider, STTConfig, STTError, STTResult, STTService
from voice.text_normalizer import ContextualTranscriptNormalizer


@dataclass(frozen=True)
class RouterObservation:
    intent: str
    entity: str = ""
    command: bool = False
    safe_action: bool = False
    confirmation_required: bool = False


def choose_microphone(recorder: ManualMicrophoneRecorder, *, input_func=input) -> str:
    """Selecciona un dispositivo sin cargar Atlas ni sus ejecutores."""
    if recorder.device_name:
        return recorder.device_name
    devices = recorder.list_devices()
    if not devices:
        return recorder.selected_device()
    if len(devices) == 1:
        recorder.device_name = devices[0]
        return devices[0]
    print("Micrófonos detectados:")
    for index, device in enumerate(devices, 1):
        print(f"  {index}. {device}")
    while True:
        selected = input_func("Elige el número del micrófono: ").strip()
        if selected.isdigit() and 1 <= int(selected) <= len(devices):
            recorder.device_name = devices[int(selected) - 1]
            return recorder.device_name
        print("Selección no válida.")


def plain(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in value if not unicodedata.combining(char)).strip()


def inspect_router_only(text: str) -> RouterObservation:
    """Contrato diagnóstico puro: no importa Atlas, adaptadores ni ejecutores."""
    value = plain(text)
    suffix = re.sub(r"\s+(?:por favor|ahora)$", "", value)
    if "luz del acuario pequeno" in value:
        if value.startswith(("enciende", "encender")):
            return RouterObservation("home.turn_on", "luz del acuario pequeño", True, True)
        if value.startswith(("apaga", "apagar")):
            return RouterObservation("home.turn_off", "luz del acuario pequeño", True, True)
        return RouterObservation("home.state", "luz del acuario pequeño")
    if "home assistant" in value:
        return RouterObservation("infrastructure.status", "Home Assistant")
    if "docker" in value or "telegram esta" in value or "ollama" in value:
        entity = "Docker" if "docker" in value else ("Telegram" if "telegram" in value else "Ollama")
        return RouterObservation("infrastructure.status", entity)
    if value.startswith("reinicia telegram"):
        return RouterObservation("telegram.restart", "Telegram", True, True, True)
    if value.startswith("abre la calculadora"):
        return RouterObservation("windows.open", "calculadora", True, True)
    if value.startswith("cierra la calculadora"):
        return RouterObservation("windows.close", "calculadora", True, True)
    if value.startswith(("cancela la operacion",)):
        return RouterObservation("cancel", "operación", True, True)
    if value.startswith(("acuerdame", "recuerdame")):
        entity = "comprar pan" if "comprar pan" in value else "Atlas"
        return RouterObservation("reminder.create", entity, True, True)
    if "recordatorios tengo" in value:
        return RouterObservation("reminder.list")
    if value.startswith("cancela el recordatorio"):
        return RouterObservation("reminder.cancel", "Atlas", True, True)
    people = (("persona conocida uno", "persona_conocida_1"), ("persona conocida dos", "persona_conocida_2"))
    for phrase, entity in people:
        if phrase in value:
            intent = "people.greet" if value.startswith("saluda") else "people.introduce" if value.startswith("presenta") else "people.farewell" if value.startswith("despidete") else "people.presence"
            return RouterObservation(intent, entity)
    if "estado de atlas" in value:
        return RouterObservation("system.status", "Atlas")
    if value.startswith(("si, es correcto", "confirma la accion")):
        return RouterObservation("confirmation.accept")
    if value.startswith(("no, no era eso", "cancela y dejalo")):
        return RouterObservation("confirmation.reject")
    if value.startswith("repite tu respuesta"):
        return RouterObservation("repeat.response")
    if value.startswith("repite lo que he dicho"):
        return RouterObservation("repeat.user")
    if value.startswith("que has entendido"):
        return RouterObservation("repeat.transcript")
    if value.startswith("explicamelo"):
        return RouterObservation("continuity.followup")
    if value.startswith("dime algo divertido"):
        return RouterObservation("humor")
    if "tiempo hace" in value:
        return RouterObservation("weather")
    return RouterObservation("conversation")


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=path.stem + ".", suffix=".tmp", dir=path.parent)
    try:
        with open(fd, "w", encoding="utf-8-sig", newline="", closefd=True) as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        Path(temporary_name).replace(path)
    finally:
        Path(temporary_name).unlink(missing_ok=True)


STATE_FIELDS = (
    "status", "stt_confidence", "stt_confidence_score", "corrections",
    "error_code", "error_message", "confirmation_required_observed",
)
FINAL_STATES = {"evaluated", "skipped"}


def build_stt_config(args, base: STTConfig | None = None) -> STTConfig:
    current = base or STTConfig.from_env()
    return replace(
        current,
        model=args.stt_model or current.model,
        model_path=Path(args.stt_model_path).resolve() if args.stt_model_path else current.model_path,
        device=args.device or current.device,
        compute_type=args.compute_type or current.compute_type,
        allow_model_download=False,
    )


def migrate_rows(rows: list[dict], fields: list[str], audio_dir: Path) -> None:
    for field in STATE_FIELDS:
        if field not in fields:
            fields.append(field)
    for row in rows:
        for field in STATE_FIELDS:
            row.setdefault(field, "")
        expected_audio = audio_dir / f"stt_{int(row['id']):03d}.wav"
        if str(row.get("raw_transcript", "")).strip():
            row["status"] = "evaluated"
        elif expected_audio.is_file():
            row["audio_file"] = str(expected_audio)
            if row.get("status") not in {"recorded", "pending_transcription", "error"}:
                row["status"] = "recorded"
        elif row.get("status") not in {"skipped", "error"}:
            row["status"] = "not_recorded"


def _synthetic_probe(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16_000)
        handle.writeframes(b"\0\0" * 8_000)


def preflight_stt(stt: STTService, provider: FasterWhisperSTTProvider, config: STTConfig, probe: Path | None) -> STTResult | None:
    required = ("config.json", "model.bin", "tokenizer.json")
    if config.model_path is not None:
        missing = [name for name in required if not (config.model_path / name).is_file()]
        if missing:
            raise STTError("stt_model_incomplete", "Faltan en el modelo local: " + ", ".join(missing))
    health = provider.health()
    if not health["available"]:
        raise STTError("stt_unavailable", "No están disponibles el paquete faster-whisper y un modelo local completo.")
    temporary = None
    if probe is None:
        temporary = stt.work_dir / "preflight_probe.wav"
        _synthetic_probe(temporary)
        probe = temporary
    cached = None
    try:
        try:
            cached, _ = stt.transcribe(probe, language_hint="es", context_hint="general")
        except STTError as exc:
            # Silence can legitimately produce no transcript; reaching this error proves
            # the package, model, backend, converter and transcribe call all loaded.
            if exc.code != "audio_empty" or temporary is None:
                raise
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(
        "STT READY | "
        f"model={config.model} | path={config.model_path or 'caché local'} | "
        f"device={health['device']} | compute_type={health['compute_type']}"
    )
    if health.get("fallback_reason"):
        print(f"Fallback local: {health['fallback_reason']}")
    return cached


def _recording_path(row: dict, audio_dir: Path) -> Path:
    return audio_dir / f"stt_{int(row['id']):03d}.wav"


def _preserve_take(path: Path) -> None:
    if not path.exists():
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path.replace(path.with_name(f"{path.stem}.previous-{stamp}{path.suffix}"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Graba y evalúa 160 casos sin ejecutar ninguna acción real.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--audio-dir", type=Path)
    parser.add_argument("--microphone", help="Nombre del micrófono; no es el dispositivo de cómputo STT.")
    parser.add_argument("--stt-model")
    parser.add_argument("--stt-model-path", type=Path)
    parser.add_argument("--device", choices=("auto", "cpu", "cuda", "gpu"), help="Dispositivo de cómputo STT.")
    parser.add_argument("--compute-type")
    parser.add_argument("--max-items", type=int)
    parser.add_argument("--smoke-test", action="store_true", help="Limita esta sesión a tres casos.")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--list-devices", action="store_true")
    args = parser.parse_args()
    output = args.output or args.input.with_name("STT_CONVERSATION_BATTERY_160_RESULTS.csv")
    audio_dir = args.audio_dir or args.input.parent / "stt_human_audio"
    if not args.input.is_file():
        parser.error("No existe el CSV original.")
    if not output.exists():
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.input, output)
    with output.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows, fields = list(reader), list(reader.fieldnames or [])
    migrate_rows(rows, fields, audio_dir)
    _write_csv(output, rows, fields)
    recorder = ManualMicrophoneRecorder(device_name=args.microphone)
    if args.list_devices:
        print("\n".join(recorder.list_devices()))
        return 0
    config = build_stt_config(args)
    provider = FasterWhisperSTTProvider(config)
    stt = STTService(provider, AudioConverter(timeout_seconds=min(30, config.timeout_seconds)), config=config, work_dir=audio_dir / ".converted")
    existing_probe = next((_recording_path(row, audio_dir) for row in rows if _recording_path(row, audio_dir).is_file()), None)
    try:
        cached_probe = preflight_stt(stt, provider, config, existing_probe)
    except STTError as exc:
        print(f"STT NOT READY [{exc.code}]: {exc}")
        print("No se ha abierto el micrófono. Indica --stt-model-path a un modelo faster-whisper local completo.")
        return 2
    if args.preflight_only:
        return 0
    selected = choose_microphone(recorder)
    pending = [index for index, row in enumerate(rows) if row.get("status") not in FINAL_STATES]
    session_limit = 3 if args.smoke_test else args.max_items
    if session_limit is not None and session_limit <= 0:
        parser.error("--max-items debe ser mayor que cero.")
    print(f"Micrófono: {selected}. Cobertura actual: {len(rows) - len(pending)}/{len(rows)}.")
    print("Modo router-only/dry-run: jamás se ejecutan comandos, Home Assistant ni acciones sensibles.")
    try:
        cursor = 0
        completed_this_session = 0
        while cursor < len(pending) and (session_limit is None or completed_this_session < session_limit):
            index = pending[cursor]
            row = rows[index]
            print(f"\nCaso {index + 1}/{len(rows)}\nDi exactamente:\n\"{row['expected_text']}\"")
            target = _recording_path(row, audio_dir)
            has_recording = target.is_file()
            if not has_recording:
                action = input("Enter=grabar, S=saltar, Q=salir: ").strip().casefold()
                if action == "q":
                    break
                if action == "s":
                    row["status"] = "skipped"
                    _write_csv(output, rows, fields)
                    cursor += 1
                    continue
                recorder.start(target)
                try:
                    input("Grabando. Pulsa Enter para detener…")
                finally:
                    recorder.stop()
                row.update({"audio_file": str(target), "status": "recorded", "error_code": "", "error_message": ""})
                _write_csv(output, rows, fields)
            try:
                if target == existing_probe and cached_probe is not None:
                    result = cached_probe
                    cached_probe = None
                else:
                    result, _timings = stt.transcribe(target, language_hint="es", context_hint=row.get("category", "general"))
            except STTError as exc:
                row.update({"status": "pending_transcription", "error_code": exc.code, "error_message": str(exc)})
                _write_csv(output, rows, fields)
                print(f"Audio conservado: {target}\nSTT pendiente [{exc.code}]: {exc}")
                action = input("Enter=reintentar el mismo WAV, S=saltar por ahora, Q=salir: ").strip().casefold()
                if action == "q":
                    break
                if action == "s":
                    cursor += 1
                continue
            normalized = ContextualTranscriptNormalizer.normalize(result)
            observed = inspect_router_only(normalized.text)
            print(f"Raw: {result.text}\nNormalizado: {normalized.text}\nIntent: {observed.intent}; entidad: {observed.entity or '-'}")
            row.update({
                "audio_file": str(target), "raw_transcript": result.text,
                "normalized_transcript": normalized.text, "status": "transcribed",
                "stt_confidence": str(result.confidence),
                "stt_confidence_score": "" if result.confidence_score is None else str(result.confidence_score),
                "corrections": json.dumps(
                    [] if result.text == normalized.text else [{"raw": result.text, "normalized": normalized.text}],
                    ensure_ascii=False,
                ),
                "error_code": "", "error_message": "",
            })
            _write_csv(output, rows, fields)
            decision = input("Enter=guardar, R=retranscribir, N=nueva toma conservando esta, Q=guardar y salir: ").strip().casefold()
            if decision == "r":
                continue
            if decision == "n":
                _preserve_take(target)
                row.update({"audio_file": "", "raw_transcript": "", "normalized_transcript": "", "status": "not_recorded"})
                _write_csv(output, rows, fields)
                continue
            row.update({
                "observed_intent": observed.intent,
                "observed_entity": observed.entity, "command_observed": str(observed.command),
                "safe_action_observed": str(observed.safe_action),
                "confirmation_required_observed": str(observed.confirmation_required),
                "status": "evaluated",
            })
            _write_csv(output, rows, fields)
            write_reports(rows, output.parent)
            cursor += 1
            completed_this_session += 1
            if decision == "q":
                break
    except KeyboardInterrupt:
        _write_csv(output, rows, fields)
        print("\nInterrumpido de forma segura; el progreso queda guardado.")
    finally:
        recorder.close()
    measured = sum(row.get("status") == "evaluated" for row in rows)
    print(f"Guardado: {output}\nCobertura: {measured}/{len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
