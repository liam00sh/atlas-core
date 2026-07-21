from core.atlas import Atlas
from tools.google_drive_oauth import (
    GoogleDriveOAuthProvider,
)
from tools.google_drive_rag import (
    GoogleDriveRagTool,
)


class FakeProvider:
    def is_available(self):
        return True

    def generate(self, prompt):
        return "Respuesta [FUENTE 1]."

    def get_provider_name(self):
        return "Fake"

    def get_model_name(self):
        return "fake"


def test_atlas_registers_rag_tool(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        GoogleDriveOAuthProvider,
        "build_client",
        lambda self, *, interactive=False: None,
    )

    atlas = Atlas(
        ai_provider=FakeProvider()
    )

    tool = atlas.framework_tool_registry.get(
        "google.drive.rag"
    )

    assert isinstance(
        tool,
        GoogleDriveRagTool,
    )
