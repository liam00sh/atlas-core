"""
===============================================================================
Proyecto Atlas
Archivo: tools/google_drive_semantic.py

Descripción:
    Índice semántico persistente para la documentación de Atlas Project.

    Utiliza embeddings locales de Ollama y se mantiene separado del índice
    documental léxico. Si Ollama o el modelo de embeddings no están
    disponibles, el RAG puede continuar utilizando la recuperación léxica.
===============================================================================
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from tools.base_tool import BaseTool, ToolRisk
from tools.capability import Capability
from tools.context import ToolContext
from tools.google_drive import DriveItem
from tools.google_drive_index import GoogleDriveDocumentIndex
from tools.result import ToolResult


SEMANTIC_INDEX_VERSION = 1
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"


class EmbeddingClient(Protocol):
    """Contrato mínimo para generar embeddings."""

    model_name: str

    def is_available(self) -> bool:
        ...

    def embed_many(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        ...


@dataclass(frozen=True, slots=True)
class SemanticChunkMatch:
    """Fragmento encontrado mediante similitud vectorial."""

    item: DriveItem
    text: str
    score: float
    chunk_index: int


class OllamaEmbeddingClient:
    """
    Cliente de embeddings compatible con las APIs actuales y heredadas
    de Ollama.

    Primero intenta `/api/embed` en lote. Si el servidor no admite ese
    endpoint, utiliza `/api/embeddings` elemento por elemento.
    """

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        timeout: int = 180,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name.strip()
        self.timeout = timeout

        if not self.model_name:
            raise ValueError(
                "El modelo de embeddings no puede estar vacío."
            )

    def _request(
        self,
        path: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        request = Request(
            url=f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exception:
            detail = ""
            try:
                detail = exception.read().decode("utf-8")
            except OSError:
                pass
            raise RuntimeError(
                f"Ollama devolvió HTTP {exception.code}. {detail}".strip()
            ) from exception
        except URLError as exception:
            raise RuntimeError(
                "No se ha podido conectar con Ollama."
            ) from exception
        except TimeoutError as exception:
            raise RuntimeError(
                "Ollama ha tardado demasiado al generar embeddings."
            ) from exception

        try:
            return json.loads(raw)
        except json.JSONDecodeError as exception:
            raise RuntimeError(
                "Ollama devolvió JSON no válido al generar embeddings."
            ) from exception

    def is_available(self) -> bool:
        try:
            self.embed_many(["prueba"])
            return True
        except RuntimeError:
            return False

    @staticmethod
    def _validate_vectors(
        vectors: list[list[float]],
        expected: int,
    ) -> list[list[float]]:
        if len(vectors) != expected:
            raise RuntimeError(
                "Ollama devolvió un número inesperado de embeddings."
            )

        normalized: list[list[float]] = []
        dimension: int | None = None

        for vector in vectors:
            if not isinstance(vector, list) or not vector:
                raise RuntimeError(
                    "Ollama devolvió un embedding vacío."
                )
            converted = [float(value) for value in vector]
            if dimension is None:
                dimension = len(converted)
            elif len(converted) != dimension:
                raise RuntimeError(
                    "Los embeddings tienen dimensiones diferentes."
                )
            normalized.append(converted)

        return normalized

    def embed_many(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        cleaned = [
            str(text).strip()
            for text in texts
            if str(text).strip()
        ]
        if len(cleaned) != len(texts) or not cleaned:
            raise ValueError(
                "Todos los textos para embeddings deben contener información."
            )

        try:
            response = self._request(
                "/api/embed",
                {
                    "model": self.model_name,
                    "input": cleaned,
                    "truncate": True,
                    "keep_alive": "5m",
                },
            )
            vectors = response.get("embeddings")
            if isinstance(vectors, list):
                return self._validate_vectors(
                    vectors,
                    len(cleaned),
                )
        except RuntimeError as modern_error:
            legacy_vectors: list[list[float]] = []
            try:
                for text in cleaned:
                    response = self._request(
                        "/api/embeddings",
                        {
                            "model": self.model_name,
                            "prompt": text,
                            "keep_alive": "5m",
                        },
                    )
                    vector = response.get("embedding")
                    if not isinstance(vector, list):
                        raise RuntimeError(
                            "Ollama no devolvió el campo embedding."
                        )
                    legacy_vectors.append(vector)
            except RuntimeError:
                raise modern_error

            return self._validate_vectors(
                legacy_vectors,
                len(cleaned),
            )

        raise RuntimeError(
            "Ollama no devolvió embeddings reconocibles."
        )


def build_embedding_client_from_provider(
    provider: Any,
) -> OllamaEmbeddingClient | None:
    """Crea el cliente usando la configuración del proveedor local."""

    if provider is None:
        return None

    base_url = getattr(provider, "base_url", None)
    if not isinstance(base_url, str) or not base_url.strip():
        return None

    timeout = getattr(provider, "timeout", 180)
    if not isinstance(timeout, int):
        timeout = 180

    return OllamaEmbeddingClient(
        base_url=base_url,
        model_name=DEFAULT_EMBEDDING_MODEL,
        timeout=timeout,
    )


class GoogleDriveSemanticIndex:
    """Persistencia y búsqueda vectorial sin dependencias externas."""

    DEFAULT_BATCH_SIZE = 16

    def __init__(
        self,
        path: Path,
        document_index: GoogleDriveDocumentIndex,
        embedder: EmbeddingClient | None,
    ) -> None:
        self.path = Path(path).resolve()
        self.document_index = document_index
        self.embedder = embedder

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _empty(self) -> dict[str, Any]:
        return {
            "version": SEMANTIC_INDEX_VERSION,
            "updated_at": None,
            "embedding_model": (
                self.embedder.model_name
                if self.embedder is not None
                else None
            ),
            "source_index_version": None,
            "chunks": {},
        }

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._empty()

        try:
            payload = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return self._empty()

        if payload.get("version") != SEMANTIC_INDEX_VERSION:
            return self._empty()
        if not isinstance(payload.get("chunks"), dict):
            return self._empty()
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        temporary = self.path.with_suffix(
            self.path.suffix + ".tmp"
        )
        temporary.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def clear(self) -> bool:
        if not self.path.exists():
            return False
        self.path.unlink()
        return True

    def status(self) -> dict[str, Any]:
        payload = self.load()
        chunks = payload["chunks"]
        documents = {
            chunk.get("item", {}).get("item_id")
            for chunk in chunks.values()
            if chunk.get("item", {}).get("item_id")
        }
        dimensions = {
            len(chunk.get("vector", []))
            for chunk in chunks.values()
            if chunk.get("vector")
        }

        return {
            "path": str(self.path),
            "exists": self.path.exists(),
            "updated_at": payload.get("updated_at"),
            "embedding_model": payload.get("embedding_model"),
            "chunk_count": len(chunks),
            "document_count": len(documents),
            "dimension": (
                next(iter(dimensions))
                if len(dimensions) == 1
                else None
            ),
        }

    @staticmethod
    def _chunk_key(
        item_id: str,
        chunk_index: int,
    ) -> str:
        return f"{item_id}:{chunk_index}"

    def sync(
        self,
        *,
        batch_size: int = DEFAULT_BATCH_SIZE,
        force: bool = False,
        scope: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.embedder is None:
            raise RuntimeError(
                "No hay un cliente de embeddings configurado."
            )

        document_payload = self.document_index.load()
        documents = document_payload.get("documents", {})
        if not documents:
            raise RuntimeError(
                "El índice documental está vacío. "
                "Actualiza primero el índice de Drive."
            )

        previous = self.load()
        previous_chunks = previous.get("chunks", {})
        current: dict[str, Any] = dict(previous_chunks) if scope else {}
        pending: list[tuple[str, dict[str, Any]]] = []
        scoped_previous_keys = {
            key for key, chunk in previous_chunks.items()
            if self.document_index._matches_search_scope(
                {"item": chunk.get("item", {}), "provenance": chunk.get("provenance", {})},
                scope,
            )
        } if scope else set(previous_chunks)
        scoped_current_keys: set[str] = set()

        stats = {
            "total": 0,
            "embedded": 0,
            "unchanged": 0,
            "removed": 0,
        }

        for document in documents.values():
            if not self.document_index._matches_search_scope(document, scope):
                continue
            item = document.get("item", {})
            provenance = document.get("provenance", {})
            content_hash = str(
                document.get("content_hash", "")
            )
            for chunk_index, chunk in enumerate(
                document.get("chunks", [])
            ):
                text = str(chunk.get("text", "")).strip()
                if not text:
                    continue

                key = self._chunk_key(
                    str(item.get("item_id", "")),
                    chunk_index,
                )
                stats["total"] += 1
                scoped_current_keys.add(key)

                old = previous_chunks.get(key)
                same = (
                    not force
                    and old is not None
                    and old.get("content_hash") == content_hash
                    and old.get("text") == text
                    and old.get("embedding_model")
                    == self.embedder.model_name
                )
                if same:
                    current[key] = {
                        **old,
                        "item": item,
                        "provenance": provenance,
                    }
                    stats["unchanged"] += 1
                    continue

                pending.append(
                    (
                        key,
                        {
                            "item": item,
                            "chunk_index": chunk_index,
                            "text": text,
                            "content_hash": content_hash,
                            "provenance": provenance,
                        },
                    )
                )

        for offset in range(0, len(pending), batch_size):
            batch = pending[
                offset:offset + batch_size
            ]
            vectors = self.embedder.embed_many(
                [entry[1]["text"] for entry in batch]
            )

            for (key, data), vector in zip(batch, vectors):
                current[key] = {
                    **data,
                    "embedding_model": self.embedder.model_name,
                    "vector": vector,
                }
                stats["embedded"] += 1

        removed_keys = scoped_previous_keys - scoped_current_keys
        for key in removed_keys:
            current.pop(key, None)
        stats["removed"] = len(removed_keys)

        payload = {
            "version": SEMANTIC_INDEX_VERSION,
            "updated_at": self._now(),
            "embedding_model": self.embedder.model_name,
            "source_index_version": document_payload.get(
                "version"
            ),
            "chunks": current,
        }
        self.save(payload)
        stats.update(self.status())
        return stats

    @staticmethod
    def _cosine(
        left: list[float],
        right: list[float],
    ) -> float:
        if len(left) != len(right) or not left:
            return -1.0

        dot = sum(
            a * b
            for a, b in zip(left, right)
        )
        left_norm = math.sqrt(
            sum(value * value for value in left)
        )
        right_norm = math.sqrt(
            sum(value * value for value in right)
        )

        if left_norm == 0.0 or right_norm == 0.0:
            return -1.0

        return dot / (left_norm * right_norm)

    def search(
        self,
        query: str,
        *,
        limit: int = 8,
        max_per_document: int = 3,
        minimum_score: float = 0.15,
        scope: dict[str, Any] | None = None,
    ) -> list[SemanticChunkMatch]:
        if self.embedder is None:
            return []

        payload = self.load()
        if not payload["chunks"]:
            return []

        query_vector = self.embedder.embed_many(
            [query.strip()]
        )[0]
        candidates: list[SemanticChunkMatch] = []

        for chunk in payload["chunks"].values():
            if not self.document_index._matches_search_scope(
                {"item": chunk.get("item", {}), "provenance": chunk.get("provenance", {})},
                scope,
            ):
                continue
            vector = chunk.get("vector")
            item_data = chunk.get("item")
            if not isinstance(vector, list):
                continue
            if not isinstance(item_data, dict):
                continue

            score = self._cosine(
                query_vector,
                [float(value) for value in vector],
            )
            if score < minimum_score:
                continue

            try:
                item = DriveItem(**item_data)
            except TypeError:
                continue

            candidates.append(
                SemanticChunkMatch(
                    item=item,
                    text=str(chunk.get("text", "")),
                    score=round(score, 6),
                    chunk_index=int(
                        chunk.get("chunk_index", 0)
                    ),
                )
            )

        candidates.sort(
            key=lambda match: (
                -match.score,
                match.item.name.casefold(),
                match.chunk_index,
            )
        )

        selected: list[SemanticChunkMatch] = []
        per_document: dict[str, int] = {}

        for match in candidates:
            count = per_document.get(
                match.item.item_id,
                0,
            )
            if count >= max_per_document:
                continue

            selected.append(match)
            per_document[match.item.item_id] = count + 1
            if len(selected) >= limit:
                break

        return selected


class GoogleDriveSemanticTool(BaseTool):
    """Herramienta del framework para el índice semántico."""

    tool_id = "google.drive.semantic"
    name = "Índice semántico de Google Drive"
    capabilities = (
        Capability("documents.semantic.sync"),
        Capability("documents.semantic.search"),
        Capability("documents.semantic.status"),
        Capability("documents.semantic.clear"),
    )
    required_permissions = frozenset(
        {"google.drive.read"}
    )
    risk = ToolRisk.LOW

    def __init__(
        self,
        semantic_index: GoogleDriveSemanticIndex,
    ) -> None:
        super().__init__()
        self.semantic_index = semantic_index
        if semantic_index.embedder is None:
            self.disable()

    def validate_arguments(
        self,
        arguments: dict[str, Any],
    ) -> None:
        super().validate_arguments(arguments)

        query = arguments.get("query")
        if query is not None and (
            not isinstance(query, str)
            or not query.strip()
        ):
            raise ValueError(
                "'query' debe ser texto no vacío."
            )

        for key, minimum, maximum in (
            ("limit", 1, 50),
            ("max_per_document", 1, 10),
            ("batch_size", 1, 64),
        ):
            value = arguments.get(key)
            if value is None:
                continue
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not minimum <= value <= maximum
            ):
                raise ValueError(
                    f"'{key}' debe estar entre {minimum} y {maximum}."
                )

    def execute(
        self,
        capability: Capability,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        self.validate_arguments(arguments)

        try:
            if capability == Capability(
                "documents.semantic.sync"
            ):
                requested_scope = dict(arguments.get("scope") or {"type": "global"})
                requested_scope.setdefault("user_id", context.requested_by)
                requested_scope.setdefault("drive_account_id", str(context.metadata.get("drive_account_id") or "default"))
                requested_scope.setdefault(
                    "root_folder_id",
                    self.semantic_index.document_index.load().get("root_folder_id"),
                )
                data = self.semantic_index.sync(
                    batch_size=arguments.get(
                        "batch_size",
                        GoogleDriveSemanticIndex.DEFAULT_BATCH_SIZE,
                    ),
                    force=bool(
                        arguments.get("force", False)
                    ),
                    scope=requested_scope,
                )
                return ToolResult.ok(
                    "Índice semántico actualizado.",
                    data=data,
                )

            if capability == Capability(
                "documents.semantic.search"
            ):
                query = arguments.get("query")
                if not isinstance(query, str):
                    raise ValueError(
                        "'query' es obligatorio."
                    )

                requested_scope = dict(arguments.get("scope") or {"type": "global"})
                requested_scope.setdefault("user_id", context.requested_by)
                requested_scope.setdefault("drive_account_id", str(context.metadata.get("drive_account_id") or "default"))
                requested_scope.setdefault(
                    "root_folder_id",
                    self.semantic_index.document_index.load().get("root_folder_id"),
                )
                matches = self.semantic_index.search(
                    query,
                    limit=arguments.get("limit", 8),
                    max_per_document=arguments.get(
                        "max_per_document",
                        3,
                    ),
                    scope=requested_scope,
                )
                return ToolResult.ok(
                    "Búsqueda semántica completada.",
                    data={
                        "query": query.strip(),
                        "count": len(matches),
                        "matches": [
                            {
                                "item": asdict(match.item),
                                "text": match.text,
                                "score": match.score,
                                "chunk_index": match.chunk_index,
                            }
                            for match in matches
                        ],
                    },
                )

            if capability == Capability(
                "documents.semantic.status"
            ):
                return ToolResult.ok(
                    "Estado semántico obtenido.",
                    data=self.semantic_index.status(),
                )

            if capability == Capability(
                "documents.semantic.clear"
            ):
                deleted = self.semantic_index.clear()
                return ToolResult.ok(
                    (
                        "Índice semántico eliminado."
                        if deleted
                        else "El índice semántico ya estaba vacío."
                    ),
                    data={"deleted": deleted},
                )
        except (RuntimeError, ValueError) as exception:
            return ToolResult.fail(
                str(exception),
                error="semantic_unavailable",
            )

        return ToolResult.fail(
            "Capacidad semántica no compatible.",
            error="unsupported_capability",
        )
