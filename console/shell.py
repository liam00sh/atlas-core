"""Consola interactiva con avisos de fallback de voz."""
from __future__ import annotations
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from voice.config import VOICE_SPEAK_CONSOLE_OUTPUT
from voice.models import AssistantIdentity
from voice.preferences.manager import VoicePreferenceManager
from voice.runtime import build_voice_service
from voice.service import VoiceService
from voice.status import VoiceStatusTracker
from conversation.response_pipeline import DaxterResponsePipeline

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
    response_pipeline = DaxterResponsePipeline()
    previous_styled_text = ""

    try:
        while running:
            try:
                command = input("\nAtlas > ")
                captured = StringIO()
                with redirect_stdout(captured):
                    running = atlas.process(command)

                base_text = VoiceService.clean_console_text(captured.getvalue())
                if not base_text:
                    continue
                identity = _active_identity(atlas)
                if identity is AssistantIdentity.DAXTER:
                    styled = response_pipeline.adapt(
                        base_text,
                        channel="cli",
                        request_text=command,
                        user=atlas.get_user(),
                        previous_styled_text=previous_styled_text,
                    )
                    text = styled.styled_text
                    previous_styled_text = text
                else:
                    text = base_text
                print(text)
                if voice_service is None or not VOICE_SPEAK_CONSOLE_OUTPUT:
                    continue
                pref = preferences.get_current()
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
                voice_service.stop_current_audio() if voice_service is not None else None
                print("\n\nAtlas se ha cerrado manualmente.")
                running = False
    finally:
        if voice_service is not None:
            voice_service.close()
