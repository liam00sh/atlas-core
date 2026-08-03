from core.atlas_commands import AtlasCommandsMixin


class FakeAtlas(AtlasCommandsMixin):
    pass


def test_command_with_argument_is_resolved(
    monkeypatch,
) -> None:
    received = {}

    class FakeModule:
        @staticmethod
        def execute(argument=None):
            received["argument"] = argument

    monkeypatch.setattr(
        "core.atlas_commands.resolve_command",
        lambda text: "voz" if text == "voz" else None,
    )
    monkeypatch.setitem(
        __import__(
            "core.atlas_commands",
            fromlist=["COMMANDS"],
        ).COMMANDS,
        "voz",
        FakeModule,
    )

    result = FakeAtlas()._handle_command(
        "voz daxter alex",
        "voz daxter alex",
    )

    assert result is True
    assert received["argument"] == "daxter alex"
