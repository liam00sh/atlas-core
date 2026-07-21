"""Recuperador comun sobre repositorios que permanecen fisicamente separados."""

from collections.abc import Callable, Iterable
from dataclasses import replace
from typing import Protocol

from knowledge.conflict import KnowledgeConflict, detect_conflicts
from knowledge.fragment import KnowledgeFragment
from knowledge.privacy import KnowledgePrivacyFilter


class KnowledgeSource(Protocol):
    source_type: str

    def retrieve(self, query: str, *, user_id: str, limit: int) -> Iterable[KnowledgeFragment]:
        ...


SOURCE_PRIORITY = {
    "relationship": 1.00,
    "person": 0.95,
    "memory": 0.90,
    "personal_semantic_memory": 0.88,
    "memory_context": 0.89,
    "system_fact": 0.88,
    "drive_document": 0.75,
    "semantic_chunk": 0.65,
    "conversation_context": 0.45,
}


class CallableKnowledgeSource:
    """Adaptador ligero para servicios existentes e inyeccion en pruebas."""

    def __init__(self, source_type: str, callback: Callable[..., Iterable[KnowledgeFragment]]):
        self.source_type = source_type
        self._callback = callback

    def retrieve(self, query: str, *, user_id: str, limit: int) -> Iterable[KnowledgeFragment]:
        return self._callback(query=query, user_id=user_id, limit=limit)


class KnowledgeRetriever:
    """Consulta fuentes autorizadas, normaliza, filtra, deduplica y ordena."""

    def __init__(
        self,
        sources: Iterable[KnowledgeSource] = (),
        *,
        privacy_filter: KnowledgePrivacyFilter | None = None,
    ) -> None:
        self.sources = tuple(sources)
        self.privacy_filter = privacy_filter or KnowledgePrivacyFilter()
        self.last_conflicts: tuple[KnowledgeConflict, ...] = ()
        self.last_excluded_sensitive = 0
        self.last_source_errors: tuple[dict[str, str], ...] = ()

    @staticmethod
    def _rank(fragment: KnowledgeFragment) -> float:
        priority = SOURCE_PRIORITY.get(fragment.source_type, 0.4)
        verified_bonus = 0.20 if fragment.verified else 0.0
        current_bonus = 0.08 if fragment.metadata.get("current", True) else -0.10
        relevance = max(0.0, min(float(fragment.score), 20.0))
        return round(priority * 100 + relevance + verified_bonus * 100 + current_bonus * 100, 6)

    def retrieve(
        self,
        query: str,
        *,
        user_id: str,
        source_types: set[str] | None = None,
        limit: int = 10,
        allow_sensitive: bool = False,
        has_sensitive_permission: bool = False,
        mask_sensitive: bool = True,
        drive_scope: dict | None = None,
    ) -> list[KnowledgeFragment]:
        if not query.strip() or limit < 1:
            return []
        candidates: list[KnowledgeFragment] = []
        source_errors: list[dict[str, str]] = []
        per_source_limit = max(3, limit)
        for source in self.sources:
            if source_types is not None and source.source_type not in source_types:
                continue
            try:
                scoped = getattr(source, "retrieve_scoped", None)
                if drive_scope is not None and callable(scoped):
                    candidates.extend(scoped(
                        query, user_id=user_id, limit=per_source_limit, scope=drive_scope
                    ))
                else:
                    candidates.extend(source.retrieve(query, user_id=user_id, limit=per_source_limit))
            except Exception as exception:
                # Los adaptadores son limites de aislamiento. Solo se
                # conserva el tipo del error para no filtrar secretos.
                source_errors.append(
                    {
                        "source_type": source.source_type,
                        "error_type": type(exception).__name__,
                    }
                )
                continue

        self.last_source_errors = tuple(source_errors)

        safe, excluded = self.privacy_filter.filter(
            candidates,
            allow_sensitive=allow_sensitive,
            has_permission=has_sensitive_permission,
            mask_sensitive=mask_sensitive,
        )
        self.last_excluded_sensitive = excluded
        best: dict[str, KnowledgeFragment] = {}
        for fragment in safe:
            ranked = replace(fragment, score=self._rank(fragment))
            previous = best.get(ranked.deduplication_key)
            if previous is None or ranked.score > previous.score:
                best[ranked.deduplication_key] = ranked
        ordered = sorted(
            best.values(),
            key=lambda item: (-item.score, item.source_type, item.source_id),
        )
        self.last_conflicts = tuple(detect_conflicts(ordered))
        return ordered[:limit]
