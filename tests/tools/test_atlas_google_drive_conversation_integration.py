"""
Pruebas de integración del flujo conversacional de Drive con Atlas.
"""

from core.atlas import Atlas
from tools.google_drive import (
    DriveItem,
    InMemoryGoogleDriveClient,
)
from tools.google_drive_oauth import (
    GoogleDriveOAuthProvider,
)


def build_atlas(
    monkeypatch,
) -> Atlas:
    # Las pruebas no deben utilizar el token OAuth real del equipo.
    monkeypatch.setattr(
        GoogleDriveOAuthProvider,
        "build_client",
        lambda self, *, interactive=False: None,
    )

    atlas = Atlas(ai_provider=None)
    atlas.configure_google_drive_client(
        InMemoryGoogleDriveClient(
            items=[
                DriveItem(
                    item_id="doc-1",
                    name="Constitución de Atlas",
                    mime_type="text/plain",
                ),
                DriveItem(
                    item_id="doc-2",
                    name="Manual de Atlas",
                    mime_type="text/plain",
                ),
            ],
            contents={
                "doc-1": "Atlas debe priorizar seguridad.",
                "doc-2": "Manual técnico del proyecto.",
            },
        )
    )
    return atlas


def test_process_searches_google_drive(
    capsys,
    monkeypatch,
) -> None:
    atlas = build_atlas(monkeypatch)

    result = atlas.process(
        "Busca en Drive Constitución"
    )

    output = capsys.readouterr().out

    assert result is True
    assert "Constitución de Atlas" in output


def test_process_reads_selected_result(
    capsys,
    monkeypatch,
) -> None:
    atlas = build_atlas(monkeypatch)

    atlas.process(
        "Busca en Drive Atlas"
    )
    capsys.readouterr()

    result = atlas.process(
        "Abre el primero"
    )
    output = capsys.readouterr().out

    assert result is True
    assert "Atlas debe priorizar seguridad." in output


def test_process_does_not_capture_generic_search(
    monkeypatch,
) -> None:
    atlas = build_atlas(monkeypatch)

    monkeypatch.setattr(
        atlas,
        "_handle_conversation",
        lambda *_args: False,
    )
    monkeypatch.setattr(
        atlas,
        "_handle_user_context_query",
        lambda *_args: False,
    )
    monkeypatch.setattr(
        atlas,
        "_handle_tool",
        lambda *_args: False,
    )
    monkeypatch.setattr(
        atlas,
        "_handle_ai",
        lambda *_args: True,
    )

    result = atlas.process(
        "Busca información sobre redes"
    )

    assert result is True
