"""
Pruebas del proveedor OAuth y del cliente real de Google Drive.

No requieren red, cuenta de Google ni dependencias externas.
"""

from pathlib import Path
from typing import Any

import pytest

from tools.google_drive_oauth import (
    DRIVE_READONLY_SCOPE,
    GOOGLE_DOC_MIME,
    GOOGLE_FOLDER_MIME,
    GoogleDriveApiClient,
    GoogleDriveOAuthConfig,
    GoogleDriveOAuthProvider,
)


class FakeRequest:
    def __init__(self, payload: Any) -> None:
        self.payload = payload

    def execute(self) -> Any:
        return self.payload


class FakeFiles:
    def __init__(
        self,
        metadata: dict[str, dict[str, Any]],
        *,
        list_payload: dict[str, Any] | None = None,
        media: dict[str, bytes] | None = None,
        exports: dict[str, bytes] | None = None,
    ) -> None:
        self.metadata = metadata
        self.list_payload = list_payload or {
            "files": []
        }
        self.media = media or {}
        self.exports = exports or {}
        self.last_list_kwargs: dict[str, Any] = {}
        self.last_export_kwargs: dict[str, Any] = {}

    def get(self, **kwargs: Any) -> FakeRequest:
        return FakeRequest(
            self.metadata[kwargs["fileId"]]
        )

    def list(self, **kwargs: Any) -> FakeRequest:
        self.last_list_kwargs = kwargs
        return FakeRequest(
            self.list_payload
        )

    def get_media(
        self,
        **kwargs: Any,
    ) -> FakeRequest:
        return FakeRequest(
            self.media[kwargs["fileId"]]
        )

    def export_media(
        self,
        **kwargs: Any,
    ) -> FakeRequest:
        self.last_export_kwargs = kwargs
        return FakeRequest(
            self.exports[kwargs["fileId"]]
        )


class FakeService:
    def __init__(self, files: FakeFiles) -> None:
        self._files = files

    def files(self) -> FakeFiles:
        return self._files


def test_default_config_uses_private_directory(
    tmp_path: Path,
) -> None:
    config = GoogleDriveOAuthConfig.default(
        tmp_path
    )

    assert (
        config.credentials_path
        == tmp_path
        / "data"
        / "integrations"
        / "google_drive"
        / "credentials.json"
    )
    assert config.token_path.name == "token.json"
    assert config.scopes == (
        DRIVE_READONLY_SCOPE,
    )


def test_provider_does_not_authorize_noninteractive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = GoogleDriveOAuthConfig.default(
        tmp_path
    )
    provider = GoogleDriveOAuthProvider(
        config
    )

    class FakeCredentials:
        @classmethod
        def from_authorized_user_file(
            cls,
            *_args: Any,
            **_kwargs: Any,
        ) -> Any:
            raise AssertionError(
                "No debería cargar credenciales."
            )

    monkeypatch.setattr(
        provider,
        "_load_dependencies",
        lambda: {
            "Credentials": FakeCredentials,
            "Request": object,
            "InstalledAppFlow": object,
            "build": object,
        },
    )

    assert (
        provider.build_client(
            interactive=False
        )
        is None
    )


def test_interactive_requires_credentials_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = GoogleDriveOAuthProvider(
        GoogleDriveOAuthConfig.default(
            tmp_path
        )
    )

    monkeypatch.setattr(
        provider,
        "_load_dependencies",
        lambda: {
            "Credentials": object,
            "Request": object,
            "InstalledAppFlow": object,
            "build": object,
        },
    )

    with pytest.raises(FileNotFoundError):
        provider.build_client(
            interactive=True
        )


def test_search_maps_drive_items() -> None:
    metadata = {
        "root": {
            "id": "root",
            "name": "Root",
            "mimeType": GOOGLE_FOLDER_MIME,
            "parents": [],
        },
        "doc-1": {
            "id": "doc-1",
            "name": "Atlas",
            "mimeType": "text/plain",
            "parents": ["root"],
            "modifiedTime": "2026-07-18T10:00:00Z",
            "size": "12",
        },
    }
    files = FakeFiles(
        metadata,
        list_payload={
            "files": [metadata["doc-1"]]
        },
    )
    client = GoogleDriveApiClient(
        FakeService(files),
        root_folder_id="root",
    )

    items = client.search_documents(
        "Atlas",
        limit=10,
    )

    assert len(items) == 1
    assert items[0].item_id == "doc-1"
    assert items[0].size_bytes == 12
    assert "'root' in parents" in (
        files.last_list_kwargs["q"]
    )


def test_reads_google_document_as_plain_text() -> None:
    metadata = {
        "doc-1": {
            "id": "doc-1",
            "name": "Documento",
            "mimeType": GOOGLE_DOC_MIME,
            "parents": [],
        }
    }
    files = FakeFiles(
        metadata,
        exports={
            "doc-1": b"Hola desde Docs",
        },
    )
    client = GoogleDriveApiClient(
        FakeService(files)
    )

    document = client.read_document(
        "doc-1",
        max_chars=100,
    )

    assert document.content == "Hola desde Docs"
    assert (
        files.last_export_kwargs["mimeType"]
        == "text/plain"
    )


def test_reads_uploaded_text_file() -> None:
    metadata = {
        "file-1": {
            "id": "file-1",
            "name": "notas.txt",
            "mimeType": "text/plain",
            "parents": [],
        }
    }
    client = GoogleDriveApiClient(
        FakeService(
            FakeFiles(
                metadata,
                media={
                    "file-1": b"Notas Atlas",
                },
            )
        )
    )

    document = client.read_document(
        "file-1",
        max_chars=100,
    )

    assert document.content == "Notas Atlas"


def test_root_restriction_blocks_external_file() -> None:
    metadata = {
        "allowed": {
            "id": "allowed",
            "name": "Permitida",
            "mimeType": GOOGLE_FOLDER_MIME,
            "parents": [],
        },
        "external": {
            "id": "external",
            "name": "Externo",
            "mimeType": "text/plain",
            "parents": [],
        },
    }
    client = GoogleDriveApiClient(
        FakeService(
            FakeFiles(
                metadata,
                media={
                    "external": b"No permitido",
                },
            )
        ),
        root_folder_id="allowed",
    )

    with pytest.raises(PermissionError):
        client.read_document(
            "external",
            max_chars=100,
        )


def test_root_restriction_allows_descendant() -> None:
    metadata = {
        "allowed": {
            "id": "allowed",
            "name": "Permitida",
            "mimeType": GOOGLE_FOLDER_MIME,
            "parents": [],
        },
        "subfolder": {
            "id": "subfolder",
            "name": "Subcarpeta",
            "mimeType": GOOGLE_FOLDER_MIME,
            "parents": ["allowed"],
        },
        "document": {
            "id": "document",
            "name": "Documento",
            "mimeType": "text/plain",
            "parents": ["subfolder"],
        },
    }
    client = GoogleDriveApiClient(
        FakeService(
            FakeFiles(
                metadata,
                media={
                    "document": b"Permitido",
                },
            )
        ),
        root_folder_id="allowed",
    )

    document = client.read_document(
        "document",
        max_chars=100,
    )

    assert document.content == "Permitido"


def test_rejects_binary_mime_type() -> None:
    metadata = {
        "pdf": {
            "id": "pdf",
            "name": "archivo.pdf",
            "mimeType": "application/pdf",
            "parents": [],
        }
    }
    client = GoogleDriveApiClient(
        FakeService(
            FakeFiles(metadata)
        )
    )

    with pytest.raises(ValueError):
        client.read_document(
            "pdf",
            max_chars=100,
        )
