from pathlib import Path

from voice.models import AssistantIdentity, SynthesisResult
from voice.service import VoiceService


class FakeProvider:
    provider_id = "kokoro"

    def is_available(self) -> bool:
        return True

    def supports_voice(self, provider_voice_id: str) -> bool:
        return provider_voice_id in {"em_alex", "em_santa", "ef_dora"}

    def synthesize(self, request):
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_bytes(b"RIFFfake")
        return SynthesisResult(
            success=True,
            output_path=request.output_path,
            voice_id=request.voice_id,
            provider_id=self.provider_id,
        )


class FakePlayer:
    def __init__(self) -> None:
        self.played: list[Path] = []

    def is_available(self) -> bool:
        return True

    def play(self, path: Path) -> bool:
        self.played.append(path)
        return True


def test_official_daxter_falls_back_to_alex(tmp_path) -> None:
    player = FakePlayer()
    service = VoiceService(
        provider=FakeProvider(),
        player=player,
        output_dir=tmp_path,
    )

    result = service.speak(
        "Hola, REDACTED_2c7b6821719d.",
        identity=AssistantIdentity.DAXTER,
        requested_voice_id="daxter_official",
    )

    assert result.success is True
    assert result.voice_id == "daxter_alex"
    assert len(player.played) == 1


def test_official_coco_falls_back_to_dora(tmp_path) -> None:
    service = VoiceService(
        provider=FakeProvider(),
        player=FakePlayer(),
        output_dir=tmp_path,
    )

    result = service.speak(
        "Hola, REDACTED_2c7b6821719d.",
        identity=AssistantIdentity.COCO,
        requested_voice_id="coco_official",
    )

    assert result.success is True
    assert result.voice_id == "coco_dora"


def test_console_cleanup_ignores_visual_separators() -> None:
    text = """
    ====================
    Hola, REDACTED_2c7b6821719d.

    INFO: prueba interna
    Todo está bien.
    """

    assert (
        VoiceService.clean_console_text(text)
        == "Hola, REDACTED_2c7b6821719d. Todo está bien."
    )
