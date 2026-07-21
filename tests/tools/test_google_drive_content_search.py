"""Pruebas de búsqueda por contenido en Google Drive."""

import pytest

from tools.capability import Capability
from tools.context import ToolContext
from tools.google_drive import (
    DriveItem,
    GoogleDriveReadTool,
    InMemoryGoogleDriveClient,
)


def build_tool() -> GoogleDriveReadTool:
    return GoogleDriveReadTool(
        InMemoryGoogleDriveClient(
            items=[
                DriveItem(
                    item_id="doc-1",
                    name="Decisiones Técnicas",
                    mime_type="text/plain",
                    web_url="https://example/doc-1",
                ),
                DriveItem(
                    item_id="doc-2",
                    name="Manual de memoria",
                    mime_type="text/plain",
                ),
                DriveItem(
                    item_id="doc-3",
                    name="Documento no relacionado",
                    mime_type="text/plain",
                ),
            ],
            contents={
                "doc-1": (
                    "Atlas utiliza memoria persistente para conservar "
                    "información entre reinicios."
                ),
                "doc-2": (
                    "La memoria de Atlas necesita confirmación antes "
                    "de guardar datos personales."
                ),
                "doc-3": "Docker se utiliza para algunos servicios.",
            },
        )
    )


def context() -> ToolContext:
    return ToolContext(
        requested_by="Liam",
        permissions=frozenset({
            "google.drive.read",
        }),
        channel="test",
    )


def test_search_content_returns_relevant_documents() -> None:
    tool = build_tool()

    result = tool.execute(
        Capability("documents.search_content"),
        {
            "query": "memoria",
            "limit": 10,
            "max_documents": 20,
            "context_chars": 200,
        },
        context(),
    )

    assert result.success is True
    assert result.data["count"] == 2
    names = [
        match["item"]["name"]
        for match in result.data["matches"]
    ]
    assert "Decisiones Técnicas" in names
    assert "Manual de memoria" in names


def test_search_content_is_accent_insensitive() -> None:
    client = InMemoryGoogleDriveClient(
        items=[
            DriveItem(
                item_id="doc-1",
                name="Documento",
                mime_type="text/plain",
            )
        ],
        contents={
            "doc-1": "La autenticación usa OAuth."
        },
    )

    matches = client.search_content(
        "autenticacion",
        limit=5,
        max_documents=5,
        context_chars=120,
    )

    assert len(matches) == 1
    assert "autenticación" in matches[0].snippet


def test_search_content_prefers_exact_phrase() -> None:
    client = InMemoryGoogleDriveClient(
        items=[
            DriveItem(
                item_id="exact",
                name="Exacto",
                mime_type="text/plain",
            ),
            DriveItem(
                item_id="split",
                name="Separado",
                mime_type="text/plain",
            ),
        ],
        contents={
            "exact": "La memoria persistente es una decisión central.",
            "split": "La memoria existe. El almacenamiento es persistente.",
        },
    )

    matches = client.search_content(
        "memoria persistente",
        limit=5,
        max_documents=5,
        context_chars=120,
    )

    assert matches[0].item.item_id == "exact"
    assert matches[0].score > matches[1].score


def test_search_content_rejects_empty_query() -> None:
    tool = build_tool()

    with pytest.raises(ValueError):
        tool.execute(
            Capability("documents.search_content"),
            {
                "query": "   ",
            },
            context(),
        )


def test_search_content_validates_context_chars() -> None:
    tool = build_tool()

    with pytest.raises(ValueError):
        tool.validate_arguments(
            {
                "context_chars": 20,
            }
        )


def test_search_content_does_not_return_unrelated_docs() -> None:
    tool = build_tool()

    result = tool.execute(
        Capability("documents.search_content"),
        {
            "query": "calendario",
        },
        context(),
    )

    assert result.data["matches"] == []
