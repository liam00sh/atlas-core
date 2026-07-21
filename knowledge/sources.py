"""Adaptadores de solo lectura para subsistemas existentes de Atlas."""

from collections.abc import Callable, Iterable
from typing import Any

from identity.relationship import PERSON_ENTITY
from knowledge.fragment import KnowledgeFragment


class MemoryKnowledgeSource:
    source_type = "memory"

    def __init__(self, retriever: Any, profile_resolver: Callable[[str], dict[str, Any]]):
        self.retriever = retriever
        self.profile_resolver = profile_resolver

    def retrieve(self, query: str, *, user_id: str, limit: int) -> Iterable[KnowledgeFragment]:
        memories = self.retriever.find(
            query,
            owner=user_id,
            viewer=user_id,
            viewer_profile=self.profile_resolver(user_id),
            limit=limit,
        )
        for memory in memories:
            yield KnowledgeFragment(
                source_type=self.source_type,
                source_id=str(memory.get("id", memory.get("created_at", "memory"))),
                title=f"Memoria de {memory.get('owner', user_id)}",
                content=str(memory.get("content", "")),
                score=float(memory.get("relevance_score", 0.0)),
                metadata={
                    "visibility": memory.get("visibility"),
                    "confirmed": memory.get("confirmed", True),
                    "sensitivity": memory.get("sensitivity", ""),
                },
                verified=bool(memory.get("confirmed", True)),
                sensitive=bool(memory.get("sensitive", False)),
            )


class PersonalSemanticMemoryKnowledgeSource:
    """Adapta el índice semántico personal sin mezclarlo con Drive."""

    source_type = "personal_semantic_memory"

    def __init__(self, semantic_index: Any):
        self.semantic_index = semantic_index

    def retrieve(self, query: str, *, user_id: str, limit: int) -> Iterable[KnowledgeFragment]:
        for match in self.semantic_index.search(query, user_id=user_id, limit=limit):
            memory = match.memory
            yield KnowledgeFragment(
                source_type=self.source_type,
                source_id=str(memory["id"]),
                title=f"Memoria semántica de {user_id}",
                content=str(memory["content"]),
                score=match.score * 10,
                metadata={
                    "semantic_score": match.semantic_score,
                    "lexical_score": match.lexical_score,
                    "sensitivity": memory.get("sensitivity", ""),
                    "confirmed": memory.get("confirmed", True),
                },
                verified=bool(memory.get("confirmed", True)),
                sensitive=str(memory.get("sensitivity", "normal")) != "normal",
            )


class LinkedMemoryKnowledgeSource:
    """Recupera el contexto navegable de enlaces verificados."""

    source_type = "memory_context"

    def __init__(self, link_store: Any):
        self.link_store = link_store

    def retrieve(self, query: str, *, user_id: str, limit: int) -> Iterable[KnowledgeFragment]:
        for memory in self.link_store.context(user_id=user_id, query=query, limit=limit):
            yield KnowledgeFragment(
                source_type=self.source_type,
                source_id=str(memory["id"]),
                title="Contexto de memoria relacionado",
                content=str(memory["content"]),
                score=8.0,
                metadata={
                    "sensitivity": memory.get("sensitivity", ""),
                    "confirmed": memory.get("confirmed", True),
                    "link_provenance": "verified_memory_link",
                },
                verified=True,
                sensitive=str(memory.get("sensitivity", "normal")) != "normal",
            )


class IdentityKnowledgeSource:
    """Recupera personas por menciones y relaciones vinculadas."""

    source_type = "person"

    def __init__(self, people_manager: Any, relationship_engine: Any):
        self.people_manager = people_manager
        self.relationship_engine = relationship_engine

    def retrieve(self, query: str, *, user_id: str, limit: int) -> Iterable[KnowledgeFragment]:
        normalized = query.casefold()
        matched = [
            person for person in self.people_manager.get_people()
            if person.name.casefold() in normalized
            or any(alias.casefold() in normalized for alias in person.aliases)
        ]
        if any(term in normalized for term in ("familia", "relacion", "relación", "quien", "quién")):
            owner = self.people_manager.find_person_by_name(user_id)
            if owner is not None and owner not in matched:
                matched.append(owner)
        for person in matched[:limit]:
            content = person.name
            if person.summary:
                content += f": {person.summary}"
            yield KnowledgeFragment(
                source_type="person",
                source_id=person.id,
                title=person.name,
                content=content,
                score=10.0,
                metadata={"status": person.status},
                verified=True,
            )
            relationships = (
                self.relationship_engine
                .get_relationships_for_entity(
                    entity_id=person.id,
                    entity_type=PERSON_ENTITY,
                )
            )
            for relationship in relationships:
                description = self.relationship_engine.describe_relationship(relationship)
                yield KnowledgeFragment(
                    source_type="relationship",
                    source_id=relationship.id,
                    title="Relacion registrada",
                    content=description,
                    score=float(relationship.confidence) * 10,
                    metadata={
                        "subject": relationship.source_entity_id,
                        "predicate": relationship.relationship_type,
                        "value": relationship.target_entity_id,
                        "information_source": relationship.information_source,
                    },
                    verified=relationship.confirmed,
                )


class DriveIndexKnowledgeSource:
    source_type = "drive_document"

    def __init__(self, document_index: Any):
        self.document_index = document_index

    def retrieve(self, query: str, *, user_id: str, limit: int) -> Iterable[KnowledgeFragment]:
        return self.retrieve_scoped(query, user_id=user_id, limit=limit, scope=None)

    def retrieve_scoped(self, query: str, *, user_id: str, limit: int, scope: dict | None) -> Iterable[KnowledgeFragment]:
        requested_scope = dict(scope or {"type": "global"})
        requested_scope.setdefault("user_id", user_id)
        for match in self.document_index.search_chunks(query, limit=limit, max_per_document=2, scope=requested_scope):
            yield KnowledgeFragment(
                source_type=self.source_type,
                source_id=match.item.item_id,
                title=match.item.name,
                content=match.text,
                score=match.score,
                metadata={
                    "url": match.item.web_url,
                    "chunk_index": match.chunk_index,
                    "modified_time": match.item.modified_time,
                    "current": True,
                },
            )


class SemanticKnowledgeSource:
    source_type = "semantic_chunk"

    def __init__(self, semantic_index: Any):
        self.semantic_index = semantic_index

    def retrieve(self, query: str, *, user_id: str, limit: int) -> Iterable[KnowledgeFragment]:
        return self.retrieve_scoped(query, user_id=user_id, limit=limit, scope=None)

    def retrieve_scoped(self, query: str, *, user_id: str, limit: int, scope: dict | None) -> Iterable[KnowledgeFragment]:
        requested_scope = dict(scope or {"type": "global"})
        requested_scope.setdefault("user_id", user_id)
        for match in self.semantic_index.search(query, limit=limit, max_per_document=2, scope=requested_scope):
            yield KnowledgeFragment(
                source_type=self.source_type,
                source_id=match.item.item_id,
                title=match.item.name,
                content=match.text,
                score=match.score * 10,
                metadata={
                    "url": match.item.web_url,
                    "chunk_index": match.chunk_index,
                    "modified_time": match.item.modified_time,
                    "current": True,
                },
            )
