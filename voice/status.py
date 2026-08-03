"""Estado persistente de fallback y recuperación de voz."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from voice.models import AssistantIdentity, SynthesisResult

@dataclass(frozen=True, slots=True)
class VoiceStatusEvent:
    event_type: str
    user_id: str
    identity: str
    requested_voice_id: str
    active_voice_id: str | None
    message: str
    occurred_at: str

class VoiceStatusTracker:
    def __init__(self, path: Path) -> None:
        self.path = path

    def register(self, *, user_id: str, identity: AssistantIdentity | str,
                 result: SynthesisResult, notify_enabled: bool) -> VoiceStatusEvent | None:
        identity = AssistantIdentity(identity)
        key = f"{user_id.casefold()}:{identity.value}"
        state = self._read_all()
        previous = state.get(key, {})
        requested = result.requested_voice_id or result.voice_id
        active = result.voice_id if result.success else None
        degraded = bool(result.success and result.fallback_used and active != requested)
        event = None

        if degraded and (not previous.get("degraded") or previous.get("active_voice_id") != active):
            event = VoiceStatusEvent(
                "fallback_started", user_id, identity.value, requested, active,
                f"La voz {requested} no está disponible. Se utilizará temporalmente {active}.",
                self._now(),
            )
        elif result.success and not degraded and previous.get("degraded"):
            event = VoiceStatusEvent(
                "voice_recovered", user_id, identity.value, requested, active,
                f"La voz {requested} vuelve a estar disponible. Atlas ha recuperado la voz configurada.",
                self._now(),
            )
        elif not result.success and not previous.get("unavailable"):
            event = VoiceStatusEvent(
                "voice_unavailable", user_id, identity.value, requested, None,
                "No hay ninguna voz disponible. Atlas mantendrá la respuesta escrita.",
                self._now(),
            )

        state[key] = {
            "requested_voice_id": requested,
            "active_voice_id": active,
            "degraded": degraded,
            "unavailable": not result.success,
            "updated_at": self._now(),
        }
        self._write_all(state)

        if event is None or not notify_enabled:
            return None
        self._append_event(event)
        return event

    def _read_all(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write_all(self, data: dict[str, dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.path)

    def _append_event(self, event: VoiceStatusEvent) -> None:
        path = self.path.with_name("events.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
