from voice.models import AssistantIdentity, SynthesisResult
from voice.status import VoiceStatusTracker

def result(requested, active, fallback):
    return SynthesisResult(True, None, active, "kokoro",
                           requested_voice_id=requested,
                           fallback_used=fallback)

def test_fallback_is_notified_once(tmp_path):
    tracker = VoiceStatusTracker(tmp_path / "status.json")
    value = result("daxter_official", "daxter_alex", True)
    first = tracker.register(user_id="REDACTED_2c7b6821719d", identity=AssistantIdentity.DAXTER,
                             result=value, notify_enabled=True)
    second = tracker.register(user_id="REDACTED_2c7b6821719d", identity=AssistantIdentity.DAXTER,
                              result=value, notify_enabled=True)
    assert first is not None
    assert first.event_type == "fallback_started"
    assert second is None

def test_recovery_is_notified(tmp_path):
    tracker = VoiceStatusTracker(tmp_path / "status.json")
    tracker.register(user_id="REDACTED_2c7b6821719d", identity="daxter",
                     result=result("daxter_official", "daxter_alex", True),
                     notify_enabled=True)
    event = tracker.register(user_id="REDACTED_2c7b6821719d", identity="daxter",
                             result=result("daxter_official", "daxter_official", False),
                             notify_enabled=True)
    assert event is not None
    assert event.event_type == "voice_recovered"

def test_selected_alternative_is_not_failure(tmp_path):
    tracker = VoiceStatusTracker(tmp_path / "status.json")
    event = tracker.register(user_id="REDACTED_2c7b6821719d", identity="daxter",
                             result=result("daxter_alex", "daxter_alex", False),
                             notify_enabled=True)
    assert event is None
