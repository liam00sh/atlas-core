from pathlib import Path

from voice.microphone import ManualMicrophoneRecorder
from tools.run_daxter_voice_pc import choose_microphone


class _Process:
    stdin = None

    def poll(self):
        return None


def test_manual_microphone_uses_selected_device_and_pcm_wav(monkeypatch, tmp_path):
    observed = {}
    def fake_popen(command, **kwargs):
        observed["command"] = command
        return _Process()
    monkeypatch.setattr("voice.microphone.subprocess.Popen", fake_popen)
    recorder = ManualMicrophoneRecorder(device_name="Auriculares Bluetooth", ffmpeg_path="ffmpeg.exe")
    target = recorder.start(tmp_path / "capture.wav")
    assert target == tmp_path / "capture.wav"
    assert "audio=Auriculares Bluetooth" in observed["command"]
    assert observed["command"][-1] == str(target)
    assert "16000" in observed["command"]
    recorder._process = None


def test_voice_command_prompts_when_multiple_microphones_are_connected(monkeypatch):
    recorder = ManualMicrophoneRecorder(ffmpeg_path="ffmpeg.exe")
    monkeypatch.setattr(recorder, "list_devices", lambda: ("Micrófono ASUS", "Cascos Bluetooth"))
    answers = iter(("x", "2"))
    selected = choose_microphone(recorder, input_func=lambda _prompt: next(answers))
    assert selected == "Cascos Bluetooth"
    assert recorder.device_name == "Cascos Bluetooth"
