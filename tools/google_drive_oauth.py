"""
===============================================================================
Proyecto Atlas
Archivo: tools/google_drive_oauth.py

Descripción:
    Proveedor real de Google Drive mediante OAuth 2.0 y Drive API v3.

    Las dependencias de Google se importan de forma diferida. Por ello Atlas
    puede arrancar aunque el módulo opcional no esté instalado o no existan
    credenciales.

    La integración utiliza exclusivamente el alcance de solo lectura.
===============================================================================
"""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any, Callable

from tools.google_drive import (
    DriveContentMatch,
    DriveDocument,
    DriveItem,
    GoogleDriveClient,
    InMemoryGoogleDriveClient,
)


DRIVE_READONLY_SCOPE = (
    "https://www.googleapis.com/auth/drive.readonly"
)

GOOGLE_FOLDER_MIME = (
    "application/vnd.google-apps.folder"
)
GOOGLE_DOC_MIME = (
    "application/vnd.google-apps.document"
)
GOOGLE_SHEET_MIME = (
    "application/vnd.google-apps.spreadsheet"
)
GOOGLE_SLIDES_MIME = (
    "application/vnd.google-apps.presentation"
)

TEXTUAL_MIME_TYPES = frozenset(
    {
        "application/json",
        "application/ld+json",
        "application/xml",
        "application/x-yaml",
        "application/yaml",
        "text/csv",
        "text/markdown",
        "text/plain",
        "text/tab-separated-values",
        "text/xml",
    }
)

METADATA_FIELDS = (
    "id,name,mimeType,modifiedTime,parents,"
    "webViewLink,size,trashed"
)


@dataclass(frozen=True, slots=True)
class GoogleDriveOAuthConfig:
    """Configuración local y segura de OAuth para Google Drive."""

    credentials_path: Path
    token_path: Path
    root_folder_id: str | None = None
    scopes: tuple[str, ...] = (
        DRIVE_READONLY_SCOPE,
    )

    @classmethod
    def default(
        cls,
        project_root: str | Path,
        *,
        root_folder_id: str | None = None,
    ) -> "GoogleDriveOAuthConfig":
        root = Path(project_root).expanduser().resolve()
        integration_dir = (
            root
            / "data"
            / "integrations"
            / "google_drive"
        )

        return cls(
            credentials_path=(
                integration_dir
                / "credentials.json"
            ),
            token_path=integration_dir / "token.json",
            root_folder_id=root_folder_id,
        )


class GoogleDriveApiClient:
    """
    Implementación de GoogleDriveClient sobre Drive API v3.

    Cuando se configura `root_folder_id`, cada consulta y lectura queda
    restringida a esa carpeta y sus descendientes.
    """

    def __init__(
        self,
        service: Any,
        *,
        root_folder_id: str | None = None,
    ) -> None:
        if service is None:
            raise ValueError(
                "El servicio de Google Drive es obligatorio."
            )

        self.service = service
        self.root_folder_id = (
            root_folder_id.strip()
            if isinstance(root_folder_id, str)
            and root_folder_id.strip()
            else None
        )

        # Evita repetir consultas de metadatos durante recorridos amplios.
        self._metadata_cache: dict[
            str,
            dict[str, Any],
        ] = {}
        self._known_within_root: set[str] = set()

        if self.root_folder_id is not None:
            self._known_within_root.add(
                self.root_folder_id
            )

    def is_available(self) -> bool:
        return True

    @staticmethod
    def _escape_query_literal(
        value: str,
    ) -> str:
        return (
            value
            .replace("\\", "\\\\")
            .replace("'", "\\'")
        )

    @staticmethod
    def _decode_text(
        payload: bytes | str,
        mime_type: str,
    ) -> str:
        if isinstance(payload, str):
            return payload

        if b"\x00" in payload[:4096]:
            raise ValueError(
                "El documento parece binario."
            )

        try:
            return payload.decode("utf-8-sig")
        except UnicodeDecodeError:
            if (
                mime_type.startswith("text/")
                or mime_type in TEXTUAL_MIME_TYPES
            ):
                return payload.decode("latin-1")

            raise ValueError(
                "El documento no contiene texto compatible."
            )

    @staticmethod
    def _to_item(
        metadata: dict[str, Any],
    ) -> DriveItem:
        parents = metadata.get("parents") or []
        raw_size = metadata.get("size")

        try:
            size_bytes = (
                int(raw_size)
                if raw_size is not None
                else None
            )
        except (TypeError, ValueError):
            size_bytes = None

        mime_type = str(
            metadata.get("mimeType", "")
        )

        return DriveItem(
            item_id=str(metadata["id"]),
            name=str(metadata.get("name", "")),
            mime_type=mime_type,
            modified_time=metadata.get(
                "modifiedTime"
            ),
            parent_id=(
                str(parents[0])
                if parents
                else None
            ),
            web_url=metadata.get("webViewLink"),
            size_bytes=size_bytes,
            is_folder=(
                mime_type == GOOGLE_FOLDER_MIME
            ),
        )

    def _get_metadata(
        self,
        file_id: str,
    ) -> dict[str, Any]:
        cached = self._metadata_cache.get(
            file_id
        )
        if cached is not None:
            return cached

        metadata = (
            self.service
            .files()
            .get(
                fileId=file_id,
                fields=METADATA_FIELDS,
                supportsAllDrives=True,
            )
            .execute()
        )
        self._metadata_cache[file_id] = metadata
        return metadata

    def _is_within_root(
        self,
        file_id: str,
    ) -> bool:
        root = self.root_folder_id
        if root is None:
            return True

        if file_id in self._known_within_root:
            return True

        current_id = file_id
        visited: set[str] = set()
        path: list[str] = []

        while current_id and current_id not in visited:
            if current_id in self._known_within_root:
                self._known_within_root.update(path)
                return True

            if current_id == root:
                self._known_within_root.update(path)
                self._known_within_root.add(root)
                return True

            visited.add(current_id)
            path.append(current_id)

            metadata = self._get_metadata(
                current_id
            )
            parents = metadata.get("parents") or []

            if not parents:
                return False

            current_id = str(parents[0])

        return False

    def _assert_within_root(
        self,
        file_id: str,
    ) -> None:
        if not self._is_within_root(file_id):
            raise PermissionError(
                "El elemento solicitado está fuera de la "
                "carpeta autorizada de Google Drive."
            )

    def search_documents(
        self,
        query: str,
        *,
        limit: int,
        parent_id: str | None = None,
    ) -> list[DriveItem]:
        effective_parent = (
            parent_id
            or self.root_folder_id
        )

        if effective_parent is not None:
            self._assert_within_root(
                effective_parent
            )

        escaped_query = self._escape_query_literal(
            query.strip()
        )
        clauses = [
            "trashed = false",
            (
                "mimeType != "
                f"'{GOOGLE_FOLDER_MIME}'"
            ),
            f"name contains '{escaped_query}'",
        ]

        if effective_parent is not None:
            escaped_parent = (
                self._escape_query_literal(
                    effective_parent
                )
            )
            clauses.append(
                f"'{escaped_parent}' in parents"
            )

        response = (
            self.service
            .files()
            .list(
                q=" and ".join(clauses),
                pageSize=limit,
                fields=(
                    "nextPageToken,"
                    f"files({METADATA_FIELDS})"
                ),
                orderBy="name_natural",
                spaces="drive",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )

        items = [
            self._to_item(metadata)
            for metadata in response.get(
                "files",
                [],
            )
        ]

        if self.root_folder_id is not None:
            return [
                item
                for item in items
                if self._is_within_root(
                    item.item_id
                )
            ][:limit]

        return items[:limit]

    def read_document(
        self,
        file_id: str,
        *,
        max_chars: int,
    ) -> DriveDocument:
        metadata = self._get_metadata(file_id)
        self._assert_within_root(file_id)

        item = self._to_item(metadata)
        mime_type = item.mime_type

        if item.is_folder:
            raise IsADirectoryError(
                "El elemento solicitado es una carpeta."
            )

        if mime_type == GOOGLE_DOC_MIME:
            request = (
                self.service
                .files()
                .export_media(
                    fileId=file_id,
                    mimeType="text/plain",
                )
            )
            export_mime = "text/plain"

        elif mime_type == GOOGLE_SHEET_MIME:
            request = (
                self.service
                .files()
                .export_media(
                    fileId=file_id,
                    mimeType="text/csv",
                )
            )
            export_mime = "text/csv"

        elif mime_type == GOOGLE_SLIDES_MIME:
            request = (
                self.service
                .files()
                .export_media(
                    fileId=file_id,
                    mimeType="text/plain",
                )
            )
            export_mime = "text/plain"

        elif (
            mime_type.startswith("text/")
            or mime_type in TEXTUAL_MIME_TYPES
        ):
            request = (
                self.service
                .files()
                .get_media(
                    fileId=file_id,
                    supportsAllDrives=True,
                )
            )
            export_mime = mime_type

        else:
            raise ValueError(
                "El tipo de archivo no admite lectura "
                f"textual segura: {mime_type}"
            )

        payload = request.execute()
        content = self._decode_text(
            payload,
            export_mime,
        )
        truncated = len(content) > max_chars

        return DriveDocument(
            item=item,
            content=content[:max_chars],
            truncated=truncated,
        )

    @staticmethod
    def _query_terms(
        query: str,
    ) -> list[str]:
        import unicodedata

        normalized = unicodedata.normalize(
            "NFKD",
            query.casefold(),
        )
        normalized = "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        )
        stopwords = {
            "de",
            "del",
            "donde",
            "el",
            "en",
            "la",
            "las",
            "los",
            "por",
            "que",
            "qué",
            "se",
            "sobre",
            "un",
            "una",
            "y",
        }
        terms = [
            term
            for term in re.findall(
                r"[\w-]+",
                normalized,
            )
            if len(term) >= 3
            and term not in stopwords
        ]
        return list(dict.fromkeys(terms))[:8]

    def search_content(
        self,
        query: str,
        *,
        limit: int,
        max_documents: int,
        context_chars: int,
    ) -> list[DriveContentMatch]:
        terms = self._query_terms(query)
        if not terms:
            return []

        full_text_clauses = [
            "fullText contains "
            f"'{self._escape_query_literal(term)}'"
            for term in terms
        ]
        clauses = [
            "trashed = false",
            (
                "mimeType != "
                f"'{GOOGLE_FOLDER_MIME}'"
            ),
            "(" + " or ".join(full_text_clauses) + ")",
        ]

        response = (
            self.service
            .files()
            .list(
                q=" and ".join(clauses),
                pageSize=max_documents,
                fields=(
                    "nextPageToken,"
                    f"files({METADATA_FIELDS})"
                ),
                orderBy="modifiedTime desc",
                spaces="drive",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )

        candidate_items = [
            self._to_item(metadata)
            for metadata in response.get(
                "files",
                [],
            )
        ]

        if self.root_folder_id is not None:
            candidate_items = [
                item
                for item in candidate_items
                if self._is_within_root(
                    item.item_id
                )
            ]

        matches: list[DriveContentMatch] = []
        scan_chars = min(
            250_000,
            max(
                20_000,
                context_chars * 30,
            ),
        )

        for item in candidate_items[:max_documents]:
            try:
                document = self.read_document(
                    item.item_id,
                    max_chars=scan_chars,
                )
            except (
                FileNotFoundError,
                IsADirectoryError,
                RuntimeError,
                ValueError,
            ):
                continue

            match = (
                InMemoryGoogleDriveClient
                ._content_match(
                    item,
                    document.content,
                    query,
                    context_chars=context_chars,
                )
            )
            if match is not None:
                matches.append(match)

        matches.sort(
            key=lambda match: (
                -match.score,
                match.item.name.casefold(),
            )
        )
        return matches[:limit]

    def list_folder(
        self,
        folder_id: str | None,
        *,
        limit: int,
    ) -> list[DriveItem]:
        effective_folder = (
            folder_id
            or self.root_folder_id
            or "root"
        )

        if self.root_folder_id is not None:
            self._assert_within_root(
                effective_folder
            )

        escaped_folder = (
            self._escape_query_literal(
                effective_folder
            )
        )

        response = (
            self.service
            .files()
            .list(
                q=(
                    "trashed = false and "
                    f"'{escaped_folder}' in parents"
                ),
                pageSize=limit,
                fields=(
                    "nextPageToken,"
                    f"files({METADATA_FIELDS})"
                ),
                orderBy="folder,name_natural",
                spaces="drive",
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )

        raw_items = response.get("files", [])

        # Los elementos devueltos son hijos directos de una carpeta que ya
        # ha sido validada. No es necesario recorrer sus ancestros uno a uno.
        for metadata in raw_items:
            item_id = str(metadata.get("id", ""))
            if not item_id:
                continue
            self._metadata_cache[item_id] = metadata
            if self.root_folder_id is not None:
                self._known_within_root.add(
                    item_id
                )

        return [
            self._to_item(metadata)
            for metadata in raw_items
        ][:limit]

    def get_item(self, file_id: str) -> DriveItem:
        """Obtiene metadatos de un elemento después de validar la raíz."""
        metadata = self._get_metadata(file_id)
        self._assert_within_root(file_id)
        return self._to_item(metadata)


class GoogleDriveOAuthProvider:
    """
    Gestiona OAuth y construye GoogleDriveApiClient.

    La autorización interactiva solo se inicia cuando `interactive=True`.
    """

    def __init__(
        self,
        config: GoogleDriveOAuthConfig,
    ) -> None:
        self.config = config
        self.last_error: str | None = None

    @staticmethod
    def _load_dependencies() -> dict[str, Any]:
        try:
            from google.auth.transport.requests import (
                Request,
            )
            from google.oauth2.credentials import (
                Credentials,
            )
            from google_auth_oauthlib.flow import (
                InstalledAppFlow,
            )
            from googleapiclient.discovery import (
                build,
            )
        except ModuleNotFoundError as exception:
            raise RuntimeError(
                "Faltan las dependencias opcionales de "
                "Google Drive. Instala "
                "requirements-google-drive.txt."
            ) from exception

        return {
            "Request": Request,
            "Credentials": Credentials,
            "InstalledAppFlow": InstalledAppFlow,
            "build": build,
        }

    def dependencies_available(self) -> bool:
        try:
            self._load_dependencies()
        except RuntimeError:
            return False
        return True

    def is_configured(self) -> bool:
        return self.config.credentials_path.is_file()

    def has_saved_token(self) -> bool:
        return self.config.token_path.is_file()

    def _save_token(
        self,
        credentials: Any,
    ) -> None:
        token_path = self.config.token_path
        token_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        token_path.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

        try:
            token_path.chmod(0o600)
        except OSError:
            # Windows puede ignorar los permisos POSIX.
            pass

    def build_client(
        self,
        *,
        interactive: bool = False,
    ) -> GoogleDriveClient | None:
        self.last_error = None

        try:
            dependencies = self._load_dependencies()
            Credentials = dependencies["Credentials"]
            Request = dependencies["Request"]
            InstalledAppFlow = dependencies[
                "InstalledAppFlow"
            ]
            build = dependencies["build"]

            credentials = None

            if self.has_saved_token():
                credentials = (
                    Credentials
                    .from_authorized_user_file(
                        str(self.config.token_path),
                        list(self.config.scopes),
                    )
                )

            if (
                credentials is not None
                and not credentials.valid
                and credentials.expired
                and credentials.refresh_token
            ):
                credentials.refresh(Request())
                self._save_token(credentials)

            if (
                credentials is None
                or not credentials.valid
            ):
                if not interactive:
                    return None

                if not self.is_configured():
                    raise FileNotFoundError(
                        "No existe credentials.json en "
                        f"{self.config.credentials_path}"
                    )

                flow = (
                    InstalledAppFlow
                    .from_client_secrets_file(
                        str(
                            self.config.credentials_path
                        ),
                        list(self.config.scopes),
                    )
                )
                credentials = flow.run_local_server(
                    port=0
                )
                self._save_token(credentials)

            service = build(
                "drive",
                "v3",
                credentials=credentials,
                cache_discovery=False,
            )

            return GoogleDriveApiClient(
                service,
                root_folder_id=(
                    self.config.root_folder_id
                ),
            )

        except Exception as exception:
            self.last_error = str(exception)
            raise
