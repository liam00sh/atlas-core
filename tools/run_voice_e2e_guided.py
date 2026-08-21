"""Prueba humana E2E real: micrófono -> STT -> Atlas -> estilo -> TTS -> altavoz."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import wave

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automation.home_assistant_factory import load_env_file
from voice.end_to_end import ManualVoiceSession
from voice.microphone import ManualMicrophoneRecorder
from voice.models import AssistantIdentity
from voice.providers.chatterbox_daxter_provider import ChatterboxDaxterProvider
from voice.service import VoiceService
from voice.stt import AudioConverter, FasterWhisperSTTProvider, STTConfig, STTService

PHRASE_TEMPLATES = (
    "Hola Daxter, ¿qué tal estás?", "¿Qué hora es?", "Repite.", "Dime algo divertido.",
    "Saluda a {known_name}.", "Enciende la luz del acuario pequeño.", "Apaga la luz del acuario pequeño.",
    "Recuérdame mañana a las 18:30 que revise Atlas.", "Reinicia Telegram.", "Cancelar.",
    "¿Docker está funcionando?", "Home Assistant está conectado.", "Hasta luego.",
)


def phrases(*, known_name: str = "persona conocida") -> tuple[str, ...]:
    return tuple(phrase.format(known_name=known_name) for phrase in PHRASE_TEMPLATES)


def save(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def load_or_initialize(path: Path, *, microphone: str) -> dict:
    if path.is_file():
        previous = json.loads(path.read_text(encoding="utf-8"))
        if previous.get("schema_version") == 2:
            previous["microphone"] = microphone
            return previous
        invalidated = path.with_name(path.stem + ".invalidated-schema1.json")
        if not invalidated.exists():
            shutil.copy2(path, invalidated)
    return {
        "schema_version": 2, "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(), "microphone": microphone,
        "completed": False, "phase_status": "OPEN", "cases": [],
        "validation_dimensions": [
            "naturalidad", "confirmaciones", "repeat", "contexto", "grounding",
            "recordatorios", "home_assistant", "cancelación", "stt", "tts",
        ],
    }


def combine_wavs(sources: tuple[Path, ...], target: Path) -> Path:
    if not sources:
        raise ValueError("No hay segmentos WAV reproducidos que conservar.")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp.wav")
    parameters = None
    chunks: list[bytes] = []
    for source in sources:
        with wave.open(str(source), "rb") as audio:
            current = (audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getcomptype())
            if parameters is None:
                parameters = current
            elif current != parameters:
                raise ValueError("Los segmentos TTS no comparten formato PCM.")
            chunks.append(audio.readframes(audio.getnframes()))
    assert parameters is not None
    with wave.open(str(temporary), "wb") as output:
        output.setnchannels(parameters[0]); output.setsampwidth(parameters[1])
        output.setframerate(parameters[2]); output.setcomptype(parameters[3], "NONE")
        for chunk in chunks:
            output.writeframes(chunk)
    temporary.replace(target)
    return target


class TurnAudioError(RuntimeError):
    """El turno no conserva un artefacto que corresponda al playback real."""


def played_audio_sources(result) -> tuple[Path, ...]:
    if not str(getattr(result, "spoken_response", "") or "").strip():
        raise TurnAudioError("El texto hablado está vacío; TTS no debía ejecutarse.")
    synthesis = getattr(result, "synthesis", None)
    if synthesis is None:
        raise TurnAudioError("El turno terminó sin resultado TTS.")
    if not synthesis.success:
        raise TurnAudioError(f"TTS falló: {synthesis.error or 'causa no informada'}")
    if synthesis.playback_completed is not True:
        raise TurnAudioError(
            f"Playback no completado: {synthesis.error or 'sin confirmación de reproducción'}"
        )
    sources = tuple(Path(path) for path in synthesis.segment_output_paths)
    if not sources:
        raise TurnAudioError(
            "TTS y playback terminaron correctamente, pero el resultado perdió segment_output_paths."
        )
    missing = tuple(path for path in sources if not path.is_file())
    if missing:
        raise TurnAudioError(
            "El WAV reproducido ya no existe: " + ", ".join(str(path) for path in missing)
        )
    return sources


def preserve_played_audio(sources: tuple[Path, ...], target: Path) -> Path:
    if not sources:
        raise TurnAudioError("No hay rutas de playback que conservar.")
    if len(sources) > 1:
        try:
            return combine_wavs(sources, target)
        except (OSError, EOFError, ValueError, wave.Error) as exc:
            raise TurnAudioError(f"No se pudieron conservar los segmentos reproducidos: {exc}") from exc
    source = sources[0]
    try:
        with wave.open(str(source), "rb") as audio:
            if audio.getnframes() <= 0:
                raise TurnAudioError(f"El WAV reproducido está vacío: {source}")
    except (OSError, EOFError, wave.Error) as exc:
        raise TurnAudioError(f"El WAV reproducido no es legible: {source}") from exc
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp.wav")
        shutil.copy2(source, temporary)
        temporary.replace(target)
    except OSError as exc:
        raise TurnAudioError(f"No se pudo conservar el WAV reproducido: {exc}") from exc
    return target


def limited_phrases(*, known_name: str, max_items: int | None) -> tuple[str, ...]:
    selected = phrases(known_name=known_name)
    return selected if max_items is None else selected[:max_items]


def print_voice_trace(stage: str, payload: dict[str, object]) -> None:
    if stage == "recording":
        print("Recording: " + str(payload.get("recording_path") or "[sin ruta]"))
    elif stage == "transcription":
        raw = str(payload.get("raw_transcript") or "")
        normalized = str(payload.get("normalized_transcript") or "")
        print("Tú dijiste: " + (raw or "[sin transcripción]"))
        if normalized != raw:
            print("Interpretado como: " + normalized)
    elif stage == "atlas":
        print("Atlas: " + str(payload.get("atlas_response") or "[sin respuesta]"))
    elif stage == "speech":
        print("Daxter: " + str(payload.get("styled_response") or "[sin respuesta]"))
        print("Texto hablado: " + str(payload.get("spoken_text") or "[vacío]"))
        print("Segmentos TTS esperados: " + str(payload.get("number_of_tts_segments_expected", 0)))
    elif stage == "tts":
        print("Segmentos TTS generados: " + str(payload.get("number_of_tts_segments_generated", 0)))
        print("WAV generados: " + json.dumps(payload.get("generated_wav_paths", []), ensure_ascii=False))
        print("Rutas de playback: " + json.dumps(payload.get("playback_paths", []), ensure_ascii=False))
        if payload.get("error"):
            print("TTS cause: " + str(payload["error"]))


def case_payload(index: int, expected: str, result, audio_path: Path | None) -> dict:
    trace = dict(result.trace or {})
    stt_trace = dict(trace.get("stt") or {})
    atlas_timings = {key: value for key, value in result.timings_ms.items() if key.startswith("atlas.")}
    synthesis = result.synthesis
    return {
        "index": index, "case_id": f"E2E{index:03d}", "expected_phrase": expected,
        "expected_text": expected,
        "raw_transcript": stt_trace.get("raw", ""),
        "normalized_transcript": stt_trace.get("normalized", result.transcript),
        "stt_confidence": stt_trace.get("confidence"),
        "stt_corrections": stt_trace.get("corrections", []),
        "intent": trace.get("intent"), "entity": trace.get("detected_entity"),
        "command": trace.get("command"), "router_path": atlas_timings,
        "atlas_base_response": trace.get("atlas_base_response", ""),
        "styled_response": result.response, "daxter_styled_response": result.response,
        "spoken_response": result.spoken_response, "spoken_text": result.spoken_response,
        "emotion": trace.get("emotion"), "intensity": trace.get("intensity"),
        "confirmation_state": trace.get("confirmation_state"),
        "timings_ms": result.timings_ms, "timings": result.timings_ms,
        "tts_success": bool(synthesis and synthesis.success),
        "tts_provider": getattr(synthesis, "provider_id", None),
        "segment_count": getattr(synthesis, "segment_count", 0) if synthesis else 0,
        "spoken_chars": getattr(synthesis, "chars_sent_to_tts", 0) if synthesis else 0,
        "audio_duration": getattr(synthesis, "wav_duration_ms", 0.0) if synthesis else 0.0,
        "wav_duration": getattr(synthesis, "wav_duration_ms", 0.0) if synthesis else 0.0,
        "playback_started": bool(synthesis and synthesis.output_path),
        "playback_completed": getattr(synthesis, "playback_completed", None),
        "playback_interrupted": getattr(synthesis, "playback_interrupted", False),
        "recoverable_error": result.recoverable_error,
        "audio_path": str(audio_path) if audio_path else None,
        "recording_path": trace.get("recording_path"),
        "number_of_tts_segments_expected": int(trace.get("number_of_tts_segments_expected", 0)),
        "number_of_tts_segments_generated": len(getattr(synthesis, "segment_output_paths", ())) if synthesis else 0,
        "generated_wav_paths": [str(path) for path in getattr(synthesis, "segment_output_paths", ())] if synthesis else [],
        "playback_paths": [str(path) for path in getattr(synthesis, "segment_output_paths", ())] if synthesis else [],
        "generation_tokens_budgeted": getattr(synthesis, "generation_tokens_budgeted", 0) if synthesis else 0,
        "generation_tokens_used": getattr(synthesis, "generation_tokens_used", 0) if synthesis else 0,
        "reached_generation_limit": getattr(synthesis, "reached_generation_limit", False) if synthesis else False,
        "generation_units": list(getattr(synthesis, "generation_units", ())) if synthesis else [],
        "sources_passed_to_combine": [],
        "audio_preservation_error": None,
        "turn_status": "PENDING",
        "side_effect": None, "state_before": None, "state_after": None, "rated": False,
    }


def preflight(atlas, recorder, stt_provider, voice_service) -> dict:
    checks: dict[str, dict] = {}
    atlas_ready = callable(getattr(atlas, "process", None))
    checks["atlas"] = {"ready": atlas_ready, "status": "READY" if atlas_ready else "NO DISPONIBLE"}
    audio_ready = bool(getattr(voice_service, "player", None) and voice_service.player.is_available())
    checks["audio_output"] = {"ready": audio_ready, "status": "READY" if audio_ready else "NO DISPONIBLE"}
    try:
        checks["microphone"] = {"ready": recorder.is_available() and bool(recorder.selected_device())}
    except (OSError, RuntimeError, ValueError):
        checks["microphone"] = {"ready": False}
    stt_health = stt_provider.health()
    checks["stt"] = {"ready": bool(stt_health.get("available")), "model": "medium", "offline": True}
    ha = getattr(getattr(atlas, "stage_e_environment", None), "adapter", None)
    try:
        ha_health = ha.health() if ha is not None else {}
        ready = bool(ha_health.get("available"))
        checks["home_assistant"] = {"ready": ready, "status": "READY" if ready else "NO DISPONIBLE"}
    except (OSError, RuntimeError, ValueError):
        checks["home_assistant"] = {"ready": False, "status": "NO DISPONIBLE"}
    try:
        atlas._queue().list_pending(atlas.get_user())
        checks["reminders"] = {"ready": True, "status": "READY"}
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
        checks["reminders"] = {"ready": False, "status": "NO DISPONIBLE"}
    if any(not checks[key]["ready"] for key in ("microphone", "stt", "atlas", "audio_output")):
        checks["tts"] = {"ready": False, "provider": "es-ES", "status": "NOT RUN"}
        return checks
    probe = voice_service.speak(
        "Prueba de voz preparada.", identity=AssistantIdentity.DAXTER,
        emotion="neutral", intensity="baja", play_audio=True,
    )
    ready = bool(probe.success and probe.playback_completed is True)
    provider = getattr(voice_service, "provider", None)
    provider_health = provider.health() if provider is not None else {}
    checks["tts"] = {
        "ready": ready, "provider": "es-ES", "voice_reference": "Daxter",
        "status": "READY" if ready else "ERROR", "error": probe.error,
        "python": str(provider.worker_command[0]) if provider is not None else None,
        "source": str(getattr(provider, "source_path", "") or ""),
        "model_requested": provider_health.get("model_requested"),
        "model_effective": provider_health.get("model_effective"),
        "reference": str(getattr(provider, "reference_path", "") or ""),
    }
    return checks


def successful_playback(result) -> bool:
    return bool(result.recoverable_error is None and result.synthesis and result.synthesis.success
                and result.synthesis.playback_completed is True)


def preflight_has_fatal_failure(checks: dict[str, dict]) -> bool:
    return any(not checks[key]["ready"] for key in ("microphone", "stt", "atlas", "audio_output", "tts"))


def diagnose_turn(atlas, text: str, *, pending_confirmation: bool) -> dict:
    """Describe la ruta con resolutores productivos, sin ejecutar una segunda vez."""
    plain = " ".join(re.sub(r"[^a-z0-9áéíóúüñ]+", " ", text.casefold()).split())
    if pending_confirmation:
        return {"intent": "confirmation.resolve", "entity": None, "command": None}
    if plain in {"repite", "repite tu respuesta", "repite lo que he dicho", "que has entendido"}:
        return {"intent": "voice.repeat", "entity": None, "command": None}
    resolver = getattr(getattr(atlas, "home_intent_service", None), "resolver", None)
    home = resolver.resolve(text) if resolver is not None else None
    if home is not None:
        parameters = dict(home.parameters)
        entity = parameters.get("entity_id") or parameters.get("entity_ids")
        return {"intent": f"home.{home.intent_type.value}", "entity": entity, "command": home.action_id}
    if "docker" in plain:
        return {"intent": "infrastructure.status", "entity": "Docker", "command": None}
    if "home assistant" in plain:
        return {"intent": "infrastructure.status", "entity": "Home Assistant", "command": None}
    parsed = getattr(atlas, "personal_reminder_parser", None)
    if parsed is not None and parsed.parse(text) is not None:
        return {"intent": "reminder.create", "entity": "reminder", "command": "persist_reminder"}
    if "reinicia telegram" in plain:
        return {"intent": "telegram.restart", "entity": "Telegram", "command": "restart_telegram"}
    if plain.startswith("saluda a "):
        return {"intent": "conversation.social", "entity": plain.removeprefix("saluda a "), "command": None}
    return {"intent": "conversation", "entity": None, "command": None}


def home_state_snapshot(atlas, text: str) -> dict | None:
    resolver = getattr(getattr(atlas, "home_intent_service", None), "resolver", None)
    intent = resolver.resolve(text) if resolver is not None else None
    if intent is None:
        return None
    entity_ids = tuple(filter(None, str(intent.parameters.get("entity_ids") or intent.parameters.get("entity_id") or "").split("|")))
    states = {}
    for entity_id in entity_ids:
        try:
            states[entity_id] = atlas.stage_e_environment.adapter.get_state(entity_id).get("state")
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
            states[entity_id] = "unavailable"
    return states


def reminder_ids(atlas) -> set[str]:
    try:
        return {str(item.get("id")) for item in atlas._queue().list_pending(atlas.get_user())}
    except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
        return set()


def replay_audio(player, audio_path: Path) -> bool:
    return bool(player.play(audio_path))


def collect_human_evaluation(case: dict, *, input_func=input) -> None:
    if case.get("playback_completed") is not True:
        raise RuntimeError("No se puede puntuar un turno sin reproducción completa.")
    case["human_functional"] = input_func("Resultado funcional [s/n/parcial]: ").strip().casefold()
    case["human_stt"] = input_func("STT entendido correctamente [1-5]: ").strip()
    case["human_conversation_naturalness"] = input_func("Naturalidad de conversación [1-5]: ").strip()
    case["human_voice_naturalness"] = input_func("Naturalidad de voz [1-5]: ").strip()
    case["human_es_es"] = input_func("Español de España [1-5]: ").strip()
    case["human_pronunciation"] = input_func("Pronunciación [1-5]: ").strip()
    case["human_audio_complete"] = input_func("Audio completo/sin cortes [1-5]: ").strip()
    if case.get("state_before") is not None:
        case["human_physical_state"] = input_func("Estado físico [on/off/no_cambio/desconocido]: ").strip().casefold()
        case["human_home_assistant_ui"] = input_func("Estado UI Home Assistant [on/off/unavailable/desconocido]: ").strip().casefold()
    case["notes"] = input_func("Notas: ").strip()
    case["rated"] = True


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba humana E2E real y reanudable de Daxter.")
    parser.add_argument("--home-assistant-env", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--device"); parser.add_argument("--known-name", default="persona conocida")
    parser.add_argument("--stt-model-path", type=Path)
    parser.add_argument("--tts-python", type=Path)
    parser.add_argument("--tts-source", type=Path)
    parser.add_argument("--tts-model-dir", type=Path)
    parser.add_argument("--tts-reference", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--check-tts", action="store_true")
    parser.add_argument("--max-items", type=int)
    args = parser.parse_args()
    if args.max_items is not None and args.max_items < 1:
        parser.error("--max-items debe ser mayor que cero.")

    tts_paths = (args.tts_python, args.tts_source, args.tts_model_dir, args.tts_reference)
    if args.check_tts:
        if any(path is None for path in tts_paths):
            parser.error("--check-tts requiere --tts-python, --tts-source, --tts-model-dir y --tts-reference.")
        from tools.check_daxter_es_es_tts import run_check

        check_output = (
            args.output.parent / "TTS_CHECK_DAXTER_ES_ES.wav"
            if args.output is not None else Path.cwd() / "TTS_CHECK_DAXTER_ES_ES.wav"
        )
        check_args = argparse.Namespace(
            tts_python=args.tts_python, tts_source=args.tts_source,
            tts_model_dir=args.tts_model_dir, tts_reference=args.tts_reference,
            output=check_output, no_play=False,
        )
        report = run_check(check_args)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["success"] else 2

    required = (args.home_assistant_env, args.output, args.stt_model_path, *tts_paths)
    if any(path is None for path in required):
        parser.error("Faltan dependencias locales requeridas para la E2E.")
    if (not all(path.is_file() for path in (args.home_assistant_env, args.tts_python, args.tts_reference))
            or not all(path.is_dir() for path in (args.stt_model_path, args.tts_source, args.tts_model_dir))):
        parser.error("Falta al menos una dependencia privada local requerida.")

    from main import build_atlas
    from tools.run_daxter_voice_pc import choose_microphone

    os.environ.update(load_env_file(args.home_assistant_env))
    recorder = ManualMicrophoneRecorder(device_name=args.device)
    selected = choose_microphone(recorder)
    config = STTConfig(model="medium", model_path=args.stt_model_path, device="auto", compute_type="auto",
                       allow_model_download=False, language_hint="es", timeout_seconds=120.0)
    stt_provider = FasterWhisperSTTProvider(config)
    stt = STTService(stt_provider, AudioConverter(timeout_seconds=30.0), config=config,
                     work_dir=args.output.parent / "e2e_audio_converted")
    provider = ChatterboxDaxterProvider(
        candidate="es_es", source_path=args.tts_source, model_dir=args.tts_model_dir,
        reference_path=args.tts_reference,
        worker_command=[str(args.tts_python), str(ROOT / "tools" / "chatterbox_worker.py")],
        cache_dir=args.output.parent / "e2e_tts_cache_es_es",
    )
    voice_service = VoiceService(provider=provider, output_dir=args.output.parent / "e2e_tts_segments")
    atlas = build_atlas()
    session = ManualVoiceSession(
        atlas=atlas, recorder=recorder, stt=stt, voice_service=voice_service,
        work_dir=args.output.parent / "e2e_audio_input", trace_callback=print_voice_trace,
    )
    report = load_or_initialize(args.output, microphone=selected)
    report["preflight"] = preflight(atlas, recorder, stt_provider, voice_service)
    report["updated_at"] = datetime.now(timezone.utc).isoformat(); save(args.output, report)
    print("STT: medium local")
    print("Atlas: " + report["preflight"]["atlas"]["status"])
    print("Audio output: " + report["preflight"]["audio_output"]["status"])
    print("TTS provider: es-ES\nvoice reference: Daxter\nstatus: " + report["preflight"]["tts"]["status"])
    print("Python: " + str(report["preflight"]["tts"].get("python") or "[no configurado]"))
    print("source: " + str(report["preflight"]["tts"].get("source") or "[no configurado]"))
    print("model_dir requested: " + str(report["preflight"]["tts"].get("model_requested") or "[no configurado]"))
    print("model_dir effective: " + str(report["preflight"]["tts"].get("model_effective") or "[no configurado]"))
    print("reference: " + str(report["preflight"]["tts"].get("reference") or "[no configurado]"))
    if report["preflight"]["tts"].get("error"):
        print("cause: " + str(report["preflight"]["tts"]["error"]))
    print("Home Assistant: " + report["preflight"]["home_assistant"]["status"])
    print("Recordatorios: " + report["preflight"]["reminders"]["status"])
    fatal = preflight_has_fatal_failure(report["preflight"])
    if fatal or args.preflight_only:
        session.close(); return 2 if fatal else 0

    guided = limited_phrases(known_name=args.known_name, max_items=args.max_items)
    report["run_scope"] = {"max_items": args.max_items, "planned_cases": len(guided)}
    completed_indexes = {int(case["index"]) for case in report["cases"] if case.get("rated")}
    try:
        for index, phrase in enumerate(guided, 1):
            if index in completed_indexes:
                continue
            while True:
                print(f"\nCaso {index}/{len(guided)}. Di exactamente:\n\"{phrase}\"")
                pending_before = session._has_pending_confirmation()
                state_before = home_state_snapshot(atlas, phrase)
                reminders_before = reminder_ids(atlas)
                result = session.capture_turn(); audio_path = None
                case = case_payload(index, phrase, result, audio_path)
                diagnosis = diagnose_turn(atlas, case["normalized_transcript"] or phrase, pending_confirmation=pending_before)
                case.update(diagnosis)
                preservation_error = None
                try:
                    sources = played_audio_sources(result)
                    case["sources_passed_to_combine"] = [str(path) for path in sources]
                    print("Sources para conservar: " + json.dumps(case["sources_passed_to_combine"], ensure_ascii=False))
                    audio_path = preserve_played_audio(
                        sources, args.output.parent / "e2e_audio" / f"case_{index:03d}.wav"
                    )
                    case["audio_path"] = str(audio_path)
                    case["turn_status"] = "READY_FOR_HUMAN_REVIEW"
                    print("Audio: " + str(audio_path))
                except TurnAudioError as exc:
                    preservation_error = str(exc)
                    case["audio_preservation_error"] = preservation_error
                    case["turn_status"] = "ERROR"
                    print("Turno ERROR: " + preservation_error)
                if state_before is not None:
                    time.sleep(0.6)
                state_after = home_state_snapshot(atlas, phrase)
                reminders_after = reminder_ids(atlas)
                case["state_before"] = state_before
                case["state_after"] = state_after
                if state_before is not None:
                    case["side_effect"] = {
                        "service_sent": diagnosis.get("command"),
                        "api_state_changed": state_before != state_after,
                    }
                created_reminders = sorted(reminders_after - reminders_before)
                if created_reminders:
                    case["side_effect"] = {
                        "reminder_created": True, "reminder_ids": created_reminders,
                        "cleanup_required": True,
                    }
                case["confirmation_before"] = pending_before
                case["confirmation_after"] = session._has_pending_confirmation()
                report["cases"] = [row for row in report["cases"] if int(row["index"]) != index] + [case]
                report["cases"].sort(key=lambda row: int(row["index"]))
                report["updated_at"] = datetime.now(timezone.utc).isoformat(); save(args.output, report)
                print("Intent: " + str(case["intent"] or "no identificado"))
                if case["entity"]:
                    print("Entidad: " + str(case["entity"]))
                if preservation_error is not None or not successful_playback(result):
                    print("Turno no evaluable: " + (preservation_error or "no hubo reproducción completa."))
                    if input("[R] repetir turno / [Q] guardar y salir: ").strip().casefold() == "q":
                        return 0
                    continue
                while True:
                    action = input("[Enter] evaluar / [A] oír de nuevo / [R] repetir turno / [T] ver texto / [Q] guardar y salir: ").strip().casefold()
                    if action == "a": replay_audio(voice_service.player, audio_path)
                    elif action == "t":
                        print("Transcripción: " + case["normalized_transcript"]); print("Respuesta: " + case["styled_response"])
                    elif action == "r": break
                    elif action == "q": return 0
                    elif not action:
                        collect_human_evaluation(case)
                        save(args.output, report); break
                if case.get("rated"): break
        scope_completed = all(
            any(int(case["index"]) == index and case.get("rated") for case in report["cases"])
            for index in range(1, len(guided) + 1)
        )
        report["scope_completed"] = scope_completed
        report["completed"] = bool(
            scope_completed and len(guided) == len(phrases(known_name=args.known_name))
        )
        report["updated_at"] = datetime.now(timezone.utc).isoformat(); save(args.output, report)
    finally:
        session.close()
    print(f"Informe privado actualizado: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
