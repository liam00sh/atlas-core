from types import SimpleNamespace

from identity.identity_storage import IdentityStorage
from identity.people_manager import PeopleManager
from identity.relationship import PARTNER, PERSON_ENTITY
from identity.relationship_engine import RelationshipEngine
from knowledge.sources import (
    DriveIndexKnowledgeSource,
    IdentityKnowledgeSource,
    MemoryKnowledgeSource,
    SemanticKnowledgeSource,
)
from tools.google_drive import DriveItem
from tools.google_drive_index import IndexChunkMatch
from tools.google_drive_semantic import SemanticChunkMatch


def test_memory_source_preserves_authorization_metadata():
    class Retriever:
        def find(self, query, **kwargs):
            assert kwargs["owner"] == kwargs["viewer"] == "Liam"
            return [{
                "id": "m1", "owner": "Liam", "content": "Prefiere trabajo local",
                "visibility": "private", "confirmed": True, "relevance_score": 4,
            }]

    items = list(MemoryKnowledgeSource(Retriever(), lambda _: {"roles": ["owner"]}).retrieve("local", user_id="Liam", limit=3))
    assert items[0].source_type == "memory"
    assert items[0].verified is True
    assert items[0].metadata["visibility"] == "private"


def test_identity_source_returns_person_and_verified_relationship():
    person = SimpleNamespace(id="p1", name="Saray", aliases=[], summary="Colabora", status="user")
    relationship = SimpleNamespace(
        id="r1", source_entity_id="p1", target_entity_id="p2",
        relationship_type="partner", information_source="user",
        confidence=1.0, confirmed=True,
    )

    class People:
        def get_people(self): return [person]
        def find_person_by_name(self, name): return person if name == "Saray" else None

    class Relationships:
        def get_relationships_for_entity(
            self,
            entity_id,
            entity_type,
        ):
            assert entity_id == person.id
            assert entity_type == PERSON_ENTITY
            return [relationship]

        def describe_relationship(self, item):
            return "Saray es pareja de Liam."

    items = list(IdentityKnowledgeSource(People(), Relationships()).retrieve("Que sabes sobre Saray", user_id="Liam", limit=5))
    assert [item.source_type for item in items] == ["person", "relationship"]
    assert items[1].verified is True


def test_lexical_and_semantic_sources_preserve_document_provenance():
    item = DriveItem("doc", "Constitucion", "text/plain", web_url="https://example/doc")

    class Lexical:
        def search_chunks(self, *args, **kwargs):
            return [IndexChunkMatch(item, "Privacidad local", 8.0, 2)]

    class Semantic:
        def search(self, *args, **kwargs):
            return [SemanticChunkMatch(item, "Privacidad local", 0.9, 2)]

    lexical = list(DriveIndexKnowledgeSource(Lexical()).retrieve("privacidad", user_id="Liam", limit=3))[0]
    semantic = list(SemanticKnowledgeSource(Semantic()).retrieve("privacidad", user_id="Liam", limit=3))[0]
    assert lexical.metadata["url"] == semantic.metadata["url"]
    assert lexical.source_id == semantic.source_id == "doc"


def test_identity_source_uses_real_relationship_engine_contract(tmp_path):
    storage = IdentityStorage(tmp_path)
    people = PeopleManager(storage)
    saray = people.create_person("Saray", summary="Colabora")
    liam = people.create_person("Liam")

    assert saray is not None
    assert liam is not None

    relationships = RelationshipEngine(people, storage)
    created, _ = relationships.create_relationship(
        source_entity_id=saray.id,
        source_entity_type=PERSON_ENTITY,
        relationship_type=PARTNER,
        target_entity_id=liam.id,
        target_entity_type=PERSON_ENTITY,
        confirmed=True,
        create_inverse=False,
    )
    assert created is not None

    fragments = list(
        IdentityKnowledgeSource(
            people,
            relationships,
        ).retrieve(
            "Que informacion tienes sobre Saray",
            user_id="Liam",
            limit=5,
        )
    )

    relationship_fragments = [
        fragment
        for fragment in fragments
        if fragment.source_type == "relationship"
    ]
    assert len(relationship_fragments) == 1
    assert relationship_fragments[0].source_id == created.id
    assert relationship_fragments[0].verified is True
