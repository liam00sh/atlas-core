from knowledge.conflict import detect_conflicts
from knowledge.context_builder import KnowledgeContextBuilder
from knowledge.fragment import KnowledgeFragment
from knowledge.privacy import KnowledgePrivacyFilter, Sensitivity
from knowledge.retriever import CallableKnowledgeSource, KnowledgeRetriever


def fragment(source_type="memory", source_id="1", content="Atlas usa memoria local", **kwargs):
    return KnowledgeFragment(
        source_type=source_type,
        source_id=source_id,
        title=kwargs.pop("title", source_id),
        content=content,
        score=kwargs.pop("score", 1.0),
        **kwargs,
    )


def source(source_type, items):
    return CallableKnowledgeSource(
        source_type,
        lambda **_: items,
    )


def test_combines_sources_limits_and_removes_duplicates():
    duplicate = fragment(content="La privacidad es local")
    retriever = KnowledgeRetriever(
        [
            source("memory", [duplicate, duplicate]),
            source("drive_document", [fragment("drive_document", "doc", "Constitucion de privacidad")]),
        ]
    )
    results = retriever.retrieve("privacidad", user_id="Liam", limit=2)
    assert len(results) == 2
    assert {item.source_type for item in results} == {"memory", "drive_document"}


def test_verified_relationship_has_priority_over_document():
    retriever = KnowledgeRetriever(
        [
            source("drive_document", [fragment("drive_document", "old", "Saray era amiga", score=99)]),
            source("relationship", [fragment("relationship", "rel", "Saray es pareja", verified=True)]),
        ]
    )
    results = retriever.retrieve("Saray", user_id="Liam")
    assert results[0].source_type == "relationship"


def test_current_document_has_priority_over_old_document():
    retriever = KnowledgeRetriever(
        [source("drive_document", [
            fragment("drive_document", "old", "decision antigua", metadata={"current": False}),
            fragment("drive_document", "new", "decision actual", metadata={"current": True}),
        ])]
    )
    results = retriever.retrieve("decision", user_id="Liam")
    assert results[0].source_id == "new"


def test_privacy_classifies_excludes_and_masks():
    privacy = KnowledgePrivacyFilter()
    secret = fragment(content="token: abc123")
    assert privacy.classify(secret) is Sensitivity.SECRET
    assert privacy.filter([secret], allow_sensitive=False, has_permission=True) == ([], 1)
    masked, excluded = privacy.filter([secret], allow_sensitive=True, has_permission=True)
    assert excluded == 0
    assert "abc123" not in masked[0].content


def test_conflict_resolution_prefers_verified_source():
    verified = fragment(
        "relationship", "rel", "Saray es pareja de Liam", score=10,
        verified=True, metadata={"subject": "Saray", "predicate": "relation", "value": "partner"},
    )
    old = fragment(
        "drive_document", "old", "Saray era amiga de Liam", score=1,
        metadata={"subject": "Saray", "predicate": "relation", "value": "friend"},
    )
    conflict = detect_conflicts([old, verified])[0]
    assert conflict.requires_confirmation is False
    assert conflict.resolution == "prioritized:relationship:rel"


def test_unresolved_conflict_requires_confirmation():
    left = fragment("memory", "1", "A", score=2, metadata={"subject": "x", "predicate": "p", "value": "a"})
    right = fragment("memory", "2", "B", score=2, metadata={"subject": "x", "predicate": "p", "value": "b"})
    assert detect_conflicts([left, right])[0].requires_confirmation is True


def test_context_limits_characters_and_source_dominance():
    items = [fragment("drive_document", "doc", "x" * 200 + str(index)) for index in range(5)]
    built = KnowledgeContextBuilder(max_fragments=4, max_characters=260, max_per_source=1).build(items)
    assert len(built.fragments) == 1
    assert len(built.text) <= 260
    assert built.truncated is True


def test_broken_source_is_isolated_and_reported_without_secrets():
    class BrokenSource:
        source_type = "person"

        def retrieve(self, query, *, user_id, limit):
            raise TypeError("private value must not be exposed")

    retriever = KnowledgeRetriever(
        [
            BrokenSource(),
            source(
                "memory",
                [fragment(content="Fuente disponible")],
            ),
        ]
    )

    results = retriever.retrieve(
        "fuente",
        user_id="Liam",
    )

    assert len(results) == 1
    assert retriever.last_source_errors == (
        {
            "source_type": "person",
            "error_type": "TypeError",
        },
    )
    assert "private value" not in str(retriever.last_source_errors)


def test_drive_scope_is_forwarded_only_to_scope_aware_sources():
    class ScopedSource:
        source_type = "drive_document"

        def retrieve(self, query, *, user_id, limit):
            raise AssertionError("La recuperación global no debe ejecutarse")

        def retrieve_scoped(self, query, *, user_id, limit, scope):
            assert scope == {"type": "subtree", "target_id": "folder"}
            return [fragment("drive_document", "doc", "resultado local")]

    results = KnowledgeRetriever([ScopedSource()]).retrieve(
        "local",
        user_id="Liam",
        drive_scope={"type": "subtree", "target_id": "folder"},
    )

    assert [item.source_id for item in results] == ["doc"]
