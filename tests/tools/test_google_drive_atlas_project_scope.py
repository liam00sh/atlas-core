"""Pruebas de la restricción de Google Drive a Atlas Project."""

from core.atlas_tools import (
    ATLAS_PROJECT_GOOGLE_DRIVE_FOLDER_ID,
)
from tools.google_drive_oauth import GoogleDriveOAuthConfig


def test_atlas_project_folder_id_is_fixed() -> None:
    assert (
        ATLAS_PROJECT_GOOGLE_DRIVE_FOLDER_ID
        == "1odTh2pF7A_HxaiAIH0h5zqcLOqHUTm3x"
    )


def test_google_drive_config_can_be_scoped(
    tmp_path,
) -> None:
    config = GoogleDriveOAuthConfig.default(
        tmp_path,
        root_folder_id=(
            ATLAS_PROJECT_GOOGLE_DRIVE_FOLDER_ID
        ),
    )

    assert config.root_folder_id == (
        ATLAS_PROJECT_GOOGLE_DRIVE_FOLDER_ID
    )
