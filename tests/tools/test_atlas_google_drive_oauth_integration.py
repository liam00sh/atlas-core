"""
Integración OAuth con Atlas sin credenciales reales.
"""

from pathlib import Path

from core.atlas import Atlas
from tools.base_tool import ToolState
from tools.google_drive_oauth import (
    GoogleDriveOAuthConfig,
    GoogleDriveOAuthProvider,
)


def test_atlas_starts_without_google_credentials(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        GoogleDriveOAuthProvider,
        "build_client",
        lambda self, *, interactive=False: None,
    )

    atlas = Atlas(ai_provider=None)

    tool = atlas.framework_tool_registry.get(
        "google.drive.read"
    )

    assert tool.state is ToolState.DISABLED


def test_oauth_configuration_fails_safely(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        GoogleDriveOAuthProvider,
        "build_client",
        lambda self, *, interactive=False: None,
    )

    atlas = Atlas(ai_provider=None)

    configured = atlas.configure_google_drive_oauth(
        config=GoogleDriveOAuthConfig.default(
            tmp_path
        ),
        interactive=False,
    )

    assert configured is False
    tool = atlas.framework_tool_registry.get(
        "google.drive.read"
    )
    assert tool.state is ToolState.DISABLED
