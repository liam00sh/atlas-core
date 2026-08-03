"""Consola interactiva con avisos de fallback de voz."""
from __future__ import annotations
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys
from voice.config import VOICE_SPEAK_CONSOLE_OUTPUT
from voice.models import AssistantIdentity
from voice.preferences.manager import VoicePreferenceManager
from voice.runtime import build_voice_service
from voice.status import VoiceStatusTracker

class _TeeOutput:
    def __init__(self, original, buffer: StringIO) -> None:
        self.original, self.buffer = original, buffer
    def write(self, text: str) -> int:
        self.original.write(text); self.buffer.write(text); return len(text)
    def flush(self) -> None:
        self.original.flush(); self.buffer.flush()

def _active_identity(atlas) -> AssistantIdentity:
    try:
        name = atlas.identity_manager.get_active_identity_name()
    except (AttributeError, RuntimeError):
        return AssistantIdentity.DAXTER
    return AssistantIdentity.COCO if str(name).strip().casefold() == "coco" else AssistantIdentity.DAXTER

def _root() -> Path:
    return Path(__file__).resolve().parent.parent

def start_shell(atlas) -> None:
    running = True
    voice_service = build_voice_service()
    preferences = VoicePreferenceManager(
        storage_path=_root() / "data" / "voice" / "user_preferences.json",
        user_provider=lambda: atlas.get_user(),
    )
    tracker = VoiceStatusTracker(_root() / "data" / "voice" / "status.json")

    while running:
        try:
            command = input("\nAtlas > ")
            if voice_service is None or not VOICE_SPEAK_CONSOLE_OUTPUT:
                running = atlas.process(command); continue

            captured = StringIO()
            with redirect_stdout(_TeeOutput(sys.stdout, captured)):
                running = atlas.process(command)

            text = voice_service.clean_console_text(captured.getvalue())
            if not text:
                continue
            pref = preferences.get_current()
            identity = _active_identity(atlas)
            result = voice_service.speak(
                text, identity=identity, preferences=pref,
                speed=pref.speech_rate, volume=pref.speech_volume,
            )
            event = tracker.register(
                user_id=atlas.get_user(), identity=identity, result=result,
                notify_enabled=pref.notify_voice_fallback,
            )
            if event is not None:
                print(f"\n[Aviso de voz] {event.message}")
            if not result.success and result.error:
                print(f"\n[Voz no disponible: {result.error}]")
        except KeyboardInterrupt:
            print("\n\nAtlas se ha cerrado manualmente.")
            running = False
