"""
===============================================================================
Proyecto Atlas
Archivo: tools/google_drive.py

Descripción:
    Contratos y herramienta de solo lectura para Google Drive.

    El módulo no depende directamente del SDK de Google. La conexión real se
    inyecta mediante un cliente que cumple GoogleDriveClient, lo que permite
    probar la herramienta sin red ni credenciales.
===============================================================================
"""

from dataclasses import asdict, dataclass
import re
from typing import Any, Protocol, runtime_checkable

from tools.base_tool import BaseTool, ToolRisk
from tools.capability import Capability
from tools.context import ToolContext
from tools.result import ToolResult


@dataclass(frozen=True, slots=True)
class DriveItem:
    """Representación mínima y neutral de un elemento de Google Drive."""

    item_id: str
    name: str
    mime_type: str
    modified_time: str | None = None
    parent_id: str | None = None
    web_url: str | None = None
    size_bytes: int | None = None
    is_folder: bool = False


@dataclass(frozen=True, slots=True)
class DriveDocument:
    """Documento de Drive con su contenido textual."""

    item: DriveItem
    content: str
    truncated: bool = False


@dataclass(frozen=True, slots=True)
class DriveContentMatch:
    """Fragmento relevante localizado dentro de un documento."""

    item: DriveItem
    snippet: str
    score: float
    occurrence_count: int = 1


@runtime_checkable
class GoogleDriveClient(Protocol):
    """
    Contrato que deberá cumplir cualquier proveedor real de Google Drive.

    Todas las operaciones definidas aquí son de solo lectura.
    """

    def is_available(self) -> bool:
        ...

    def search_documents(
        self,
        query: str,
        *,
        limit: int,
        parent_id: str | None = None,
    ) -> list[DriveItem]:
        ...

    def read_document(
        self,
        file_id: str,
        *,
        max_chars: int,
    ) -> DriveDocument:
        ...

    def search_content(
        self,
        query: str,
        *,
        limit: int,
        max_documents: int,
        context_chars: int,
    ) -> list[DriveContentMatch]:
        ...

    def list_folder(
        self,
        folder_id: str | None,
        *,
        limit: int,
    ) -> list[DriveItem]:
        ...

    def get_item(self, file_id: str) -> DriveItem:
        ...


class UnavailableGoogleDriveClient:
    """Cliente seguro utilizado mientras Drive no está configurado."""

    def is_available(self) -> bool:
        return False

    def _raise(self) -> None:
        raise RuntimeError(
            "Google Drive todavía no está configurado en Atlas."
        )

    def search_documents(
        self,
        query: str,
        *,
        limit: int,
        parent_id: str | None = None,
    ) -> list[DriveItem]:
        self._raise()

    def read_document(
        self,
        file_id: str,
        *,
        max_chars: int,
    ) -> DriveDocument:
        self._raise()

    def search_content(
        self,
        query: str,
        *,
        limit: int,
        max_documents: int,
        context_chars: int,
    ) -> list[DriveContentMatch]:
        self._raise()

    def list_folder(
        self,
        folder_id: str | None,
        *,
        limit: int,
    ) -> list[DriveItem]:
        self._raise()

    def get_item(self, file_id: str) -> DriveItem:
        self._raise()


class InMemoryGoogleDriveClient:
    """
    Cliente en memoria destinado a pruebas y desarrollo local.

    No realiza conexiones externas.
    """

    def __init__(
        self,
        items: list[DriveItem] | None = None,
        contents: dict[str, str] | None = None,
    ) -> None:
        self._items = {
            item.item_id: item
            for item in (items or [])
        }
        self._contents = dict(contents or {})

    def is_available(self) -> bool:
        return True

    def search_documents(
        self,
        query: str,
        *,
        limit: int,
        parent_id: str | None = None,
    ) -> list[DriveItem]:
        normalized = query.casefold().strip()

        matches = [
            item
            for item in self._items.values()
            if not item.is_folder
            and normalized in item.name.casefold()
            and (
                parent_id is None
                or item.parent_id == parent_id
            )
        ]

        matches.sort(
            key=lambda item: item.name.casefold()
        )
        return matches[:limit]

    def read_document(
        self,
        file_id: str,
        *,
        max_chars: int,
    ) -> DriveDocument:
        try:
            item = self._items[file_id]
        except KeyError as exception:
            raise FileNotFoundError(
                f"No existe el documento de Drive: {file_id}"
            ) from exception

        if item.is_folder:
            raise IsADirectoryError(
                f"El elemento de Drive es una carpeta: {file_id}"
            )

        try:
            content = self._contents[file_id]
        except KeyError as exception:
            raise FileNotFoundError(
                "No hay contenido textual disponible para "
                f"el documento: {file_id}"
            ) from exception

        truncated = len(content) > max_chars

        return DriveDocument(
            item=item,
            content=content[:max_chars],
            truncated=truncated,
        )

    @staticmethod
    def _normalize_for_search(
        value: str,
    ) -> str:
        import unicodedata

        normalized = unicodedata.normalize(
            "NFKD",
            value.casefold(),
        )
        return "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        )

    @classmethod
    def _content_match(
        cls,
        item: DriveItem,
        content: str,
        query: str,
        *,
        context_chars: int,
    ) -> DriveContentMatch | None:
        normalized_content = cls._normalize_for_search(
            content
        )
        normalized_query = cls._normalize_for_search(
            query.strip()
        )
        terms = [
            term
            for term in re.findall(
                r"[\w-]+",
                normalized_query,
            )
            if len(term) >= 2
        ]

        if not terms:
            return None

        positions = [
            normalized_content.find(term)
            for term in terms
            if normalized_content.find(term) >= 0
        ]
        if not positions:
            return None

        phrase_count = normalized_content.count(
            normalized_query
        )
        term_counts = [
            normalized_content.count(term)
            for term in terms
        ]
        occurrence_count = max(
            phrase_count,
            sum(term_counts),
        )

        matched_terms = sum(
            1
            for count in term_counts
            if count > 0
        )
        coverage = matched_terms / len(terms)
        score = (
            coverage * 10.0
            + min(occurrence_count, 20) * 0.25
            + (5.0 if phrase_count else 0.0)
        )

        center = min(positions)
        half = max(40, context_chars // 2)
        start = max(0, center - half)
        end = min(
            len(content),
            center + half,
        )

        while start > 0 and not content[start].isspace():
            start -= 1
        while end < len(content) and not content[end - 1].isspace():
            end += 1

        snippet = " ".join(
            content[start:end].split()
        )
        if start > 0:
            snippet = "…" + snippet
        if end < len(content):
            snippet += "…"

        return DriveContentMatch(
            item=item,
            snippet=snippet,
            score=round(score, 3),
            occurrence_count=occurrence_count,
        )

    def search_content(
        self,
        query: str,
        *,
        limit: int,
        max_documents: int,
        context_chars: int,
    ) -> list[DriveContentMatch]:
        matches: list[DriveContentMatch] = []

        documents = [
            item
            for item in self._items.values()
            if not item.is_folder
        ][:max_documents]

        for item in documents:
            content = self._contents.get(
                item.item_id
            )
            if content is None:
                continue

            match = self._content_match(
                item,
                content,
                query,
                context_chars=context_chars,
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
        matches = [
            item
            for item in self._items.values()
            if item.parent_id == folder_id
        ]

        matches.sort(
            key=lambda item: (
                not item.is_folder,
                item.name.casefold(),
            )
        )
        return matches[:limit]

    def get_item(self, file_id: str) -> DriveItem:
        try:
            return self._items[file_id]
        except KeyError as exception:
            raise FileNotFoundError(f"No existe el elemento de Drive: {file_id}") from exception


class GoogleDriveReadTool(BaseTool):
    """Herramienta de Google Drive limitada estrictamente a lectura."""

    tool_id = "google.drive.read"
    name = "Google Drive Reader"
    capabilities = (
        Capability("documents.search"),
        Capability("documents.read"),
        Capability("documents.search_content"),
        Capability("folders.list"),
    )
    required_permissions = frozenset(
        {
            "google.drive.read",
        }
    )
    risk = ToolRisk.MEDIUM

    DEFAULT_LIMIT = 20
    MAX_LIMIT = 100
    DEFAULT_MAX_CHARS = 100_000
    MAX_ALLOWED_CHARS = 500_000
    DEFAULT_MAX_DOCUMENTS = 30
    MAX_DOCUMENTS = 100
    DEFAULT_CONTEXT_CHARS = 700
    MAX_CONTEXT_CHARS = 4000

    def __init__(
        self,
        client: GoogleDriveClient,
    ) -> None:
        super().__init__()

        if not isinstance(client, GoogleDriveClient):
            raise TypeError(
                "El cliente debe cumplir GoogleDriveClient."
            )

        self.client = client

        if not client.is_available():
            self.disable()

    def validate_arguments(
        self,
        arguments: dict[str, Any],
    ) -> None:
        super().validate_arguments(arguments)

        limit = arguments.get(
            "limit",
            self.DEFAULT_LIMIT,
        )
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or limit < 1
            or limit > self.MAX_LIMIT
        ):
            raise ValueError(
                f"'limit' debe estar entre 1 y {self.MAX_LIMIT}."
            )

        max_chars = arguments.get(
            "max_chars",
            self.DEFAULT_MAX_CHARS,
        )
        if (
            isinstance(max_chars, bool)
            or not isinstance(max_chars, int)
            or max_chars < 1
            or max_chars > self.MAX_ALLOWED_CHARS
        ):
            raise ValueError(
                "'max_chars' debe estar entre 1 y "
                f"{self.MAX_ALLOWED_CHARS}."
            )

        max_documents = arguments.get(
            "max_documents",
            self.DEFAULT_MAX_DOCUMENTS,
        )
        if (
            isinstance(max_documents, bool)
            or not isinstance(max_documents, int)
            or max_documents < 1
            or max_documents > self.MAX_DOCUMENTS
        ):
            raise ValueError(
                "'max_documents' debe estar entre 1 y "
                f"{self.MAX_DOCUMENTS}."
            )

        context_chars = arguments.get(
            "context_chars",
            self.DEFAULT_CONTEXT_CHARS,
        )
        if (
            isinstance(context_chars, bool)
            or not isinstance(context_chars, int)
            or context_chars < 80
            or context_chars > self.MAX_CONTEXT_CHARS
        ):
            raise ValueError(
                "'context_chars' debe estar entre 80 y "
                f"{self.MAX_CONTEXT_CHARS}."
            )

        for key in ("parent_id", "folder_id"):
            value = arguments.get(key)
            if value is not None and (
                not isinstance(value, str)
                or not value.strip()
            ):
                raise ValueError(
                    f"'{key}' debe ser texto no vacío."
                )

    def _validate_for_capability(
        self,
        capability: Capability,
        arguments: dict[str, Any],
    ) -> None:
        if capability in {
            Capability("documents.search"),
            Capability("documents.search_content"),
        }:
            query = arguments.get("query")
            if not isinstance(query, str) or not query.strip():
                raise ValueError(
                    "'query' es obligatorio para la búsqueda."
                )

        elif capability == Capability("documents.read"):
            file_id = arguments.get("file_id")
            if not isinstance(file_id, str) or not file_id.strip():
                raise ValueError(
                    "'file_id' es obligatorio para documents.read."
                )

    @staticmethod
    def _serialize_item(
        item: DriveItem,
    ) -> dict[str, Any]:
        return asdict(item)

    def execute(
        self,
        capability: Capability,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        self._validate_for_capability(
            capability,
            arguments,
        )

        limit = arguments.get(
            "limit",
            self.DEFAULT_LIMIT,
        )

        if capability == Capability("documents.search"):
            items = self.client.search_documents(
                arguments["query"].strip(),
                limit=limit,
                parent_id=arguments.get("parent_id"),
            )

            return ToolResult.ok(
                "Búsqueda de Google Drive completada.",
                data={
                    "items": [
                        self._serialize_item(item)
                        for item in items
                    ],
                    "count": len(items),
                    "requested_by": context.requested_by,
                    "channel": context.channel,
                },
            )

        if capability == Capability(
            "documents.search_content"
        ):
            matches = self.client.search_content(
                arguments["query"].strip(),
                limit=limit,
                max_documents=arguments.get(
                    "max_documents",
                    self.DEFAULT_MAX_DOCUMENTS,
                ),
                context_chars=arguments.get(
                    "context_chars",
                    self.DEFAULT_CONTEXT_CHARS,
                ),
            )

            return ToolResult.ok(
                "Búsqueda por contenido de Google Drive completada.",
                data={
                    "matches": [
                        {
                            "item": self._serialize_item(
                                match.item
                            ),
                            "snippet": match.snippet,
                            "score": match.score,
                            "occurrence_count": (
                                match.occurrence_count
                            ),
                        }
                        for match in matches
                    ],
                    "count": len(matches),
                    "query": arguments["query"].strip(),
                    "requested_by": context.requested_by,
                    "channel": context.channel,
                },
            )

        if capability == Capability("documents.read"):
            document = self.client.read_document(
                arguments["file_id"].strip(),
                max_chars=arguments.get(
                    "max_chars",
                    self.DEFAULT_MAX_CHARS,
                ),
            )

            result = ToolResult.ok(
                "Documento de Google Drive leído.",
                data={
                    "item": self._serialize_item(
                        document.item
                    ),
                    "content": document.content,
                    "truncated": document.truncated,
                    "requested_by": context.requested_by,
                    "channel": context.channel,
                },
            )

            if document.truncated:
                result.warnings.append(
                    "El contenido se ha truncado al límite solicitado."
                )

            return result

        if capability == Capability("folders.list"):
            items = self.client.list_folder(
                arguments.get("folder_id"),
                limit=limit,
            )

            return ToolResult.ok(
                "Carpeta de Google Drive listada.",
                data={
                    "items": [
                        self._serialize_item(item)
                        for item in items
                    ],
                    "count": len(items),
                    "folder_id": arguments.get("folder_id"),
                    "requested_by": context.requested_by,
                    "channel": context.channel,
                },
            )

        raise ValueError(
            f"Capacidad no implementada: {capability}"
        )
