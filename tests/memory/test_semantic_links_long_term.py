"""Pruebas de aceptación de los Sprints 14, 15 y 16."""

from time import perf_counter

from memory.links import MemoryLinkStore
from memory.long_term import LongTermMemoryService
from memory.memory_manager import MemoryManager
from memory.semantic_index import PersonalMemorySemanticIndex


class FakeEmbedder:
    model_name = "fake-local"

    def embed_many(self, texts):
        vectors = []
        for text in texts:
            value = text.casefold()
            if any(word in value for word in ("coche", "hyundai", "vehiculo", "conduzco")):
                vectors.append([1.0, 0.0, 0.0])
            elif any(word in value for word in ("neumatic", "rueda", "michelin")):
                vectors.append([0.8, 0.2, 0.0])
            else:
                vectors.append([0.0, 0.0, 1.0])
        return vectors


def build(tmp_path):
    memory = MemoryManager(tmp_path / "memory")
    semantic = PersonalMemorySemanticIndex(tmp_path / "semantic.json", memory, FakeEmbedder())
    return memory, semantic


def test_personal_semantic_recovery_and_user_isolation(tmp_path):
    memory, semantic = build(tmp_path)
    memory.remember("REDACTED_2c7b6821719d", "Conduzco un Hyundai i30 N", "private")
    memory.remember("REDACTED_bc04a68d9192", "Conduzco otro vehículo", "private")
    matches = semantic.search("Háblame de mi coche", user_id="REDACTED_2c7b6821719d")
    assert [item.memory["owner"] for item in matches] == ["REDACTED_2c7b6821719d"]
    assert "Hyundai" in matches[0].memory["content"]


def test_semantic_index_updates_and_deletes_immediately(tmp_path):
    memory, semantic = build(tmp_path)
    memory.remember("REDACTED_2c7b6821719d", "Conduzco un Hyundai i30 N", "private")
    stored = memory.list_memories(owner="REDACTED_2c7b6821719d")[0]
    assert stored["id"] in semantic.load()["entries"]
    memory.update_memory(memory_id=stored["id"], owner="REDACTED_2c7b6821719d", content="Uso neumáticos Michelin")
    assert semantic.load()["entries"][stored["id"]]["content"] == "Uso neumáticos Michelin"
    memory.delete_memory(memory_id=stored["id"], owner="REDACTED_2c7b6821719d")
    assert stored["id"] not in semantic.load()["entries"]


def test_semantic_sensitive_memory_is_excluded_without_permission(tmp_path):
    memory, semantic = build(tmp_path)
    memory.remember(
        "REDACTED_2c7b6821719d", "Mi coche está ligado al DNI 12345678Z", "private",
        metadata={"sensitivity": "personal"},
    )
    assert semantic.search("Qué coche conduzco", user_id="REDACTED_2c7b6821719d") == []
    assert semantic.search(
        "Qué coche conduzco", user_id="REDACTED_2c7b6821719d", allow_sensitive=True,
        has_sensitive_permission=True,
    )


def test_incremental_sync_does_not_reembed_unchanged_memories(tmp_path):
    memory, semantic = build(tmp_path)
    memory.remember("REDACTED_2c7b6821719d", "Conduzco un Hyundai", "private")
    assert semantic.sync(user_id="REDACTED_2c7b6821719d")["embedded"] == 0


def test_verified_memory_links_and_context_navigation(tmp_path):
    memory, _ = build(tmp_path)
    for content in ("Conduzco un Hyundai i30 N", "Quiero neumáticos Michelin", "Haré tandas en circuito"):
        memory.remember("REDACTED_2c7b6821719d", content, "private")
    items = memory.list_memories(owner="REDACTED_2c7b6821719d")
    links = MemoryLinkStore(tmp_path / "links.json", memory)
    links.create(
        user_id="REDACTED_2c7b6821719d", source_memory_id=items[0]["id"], target_memory_id=items[1]["id"],
        link_type="related_to", explanation="Ambos datos describen el coche",
        evidence={"source": "user_confirmation"},
    )
    links.create(
        user_id="REDACTED_2c7b6821719d", source_memory_id=items[1]["id"], target_memory_id=items[2]["id"],
        link_type="supports", explanation="Los neumáticos se usarán en tandas",
        evidence={"source": "user_confirmation"},
    )
    context = links.context(user_id="REDACTED_2c7b6821719d", query="Hyundai")
    assert {item["id"] for item in context} == {item["id"] for item in items}
    assert links.context(user_id="REDACTED_bc04a68d9192", query="Hyundai") == []


def test_topic_project_and_entity_grouping_is_user_scoped(tmp_path):
    memory, _ = build(tmp_path)
    memory.remember(
        "REDACTED_2c7b6821719d", "Cambiar neumáticos", "private",
        metadata={"topic": "coche", "project": "Hyundai i30N", "entities": ["Hyundai"]},
    )
    memory.remember("REDACTED_bc04a68d9192", "Otro proyecto", "private", metadata={"topic": "coche"})
    links = MemoryLinkStore(tmp_path / "links.json", memory)
    assert len(links.groups(user_id="REDACTED_2c7b6821719d", dimension="topic")["coche"]) == 1
    assert "Hyundai i30N" in links.groups(user_id="REDACTED_2c7b6821719d", dimension="project")
    assert "Hyundai" in links.groups(user_id="REDACTED_2c7b6821719d", dimension="entity")


def test_links_require_evidence_and_detect_structured_contradictions(tmp_path):
    memory, _ = build(tmp_path)
    memory.remember("REDACTED_2c7b6821719d", "Mi color favorito es azul", "private", metadata={"memory_key": "favorite_color"})
    memory.remember("REDACTED_2c7b6821719d", "Mi color favorito es verde", "private", metadata={"memory_key": "favorite_color"})
    links = MemoryLinkStore(tmp_path / "links.json", memory)
    assert links.contradiction_candidates(user_id="REDACTED_2c7b6821719d")[0]["action"] == "propose_review"
    items = memory.list_memories(owner="REDACTED_2c7b6821719d")
    try:
        links.create(
            user_id="REDACTED_2c7b6821719d", source_memory_id=items[0]["id"], target_memory_id=items[1]["id"],
            link_type="related_to", explanation="", evidence={},
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Un enlace sin evidencia no debe persistirse")


def test_long_term_history_archive_restore_and_summary_sources(tmp_path):
    memory, _ = build(tmp_path)
    memory.remember("REDACTED_2c7b6821719d", "Proyecto Atlas usa Ollama", "private", metadata={"importance": 0.9})
    item = memory.list_memories(owner="REDACTED_2c7b6821719d")[0]
    assert item["state"] == "active" and item["access_count"] == 0
    memory.update_memory(memory_id=item["id"], owner="REDACTED_2c7b6821719d", content="Proyecto Atlas usa Ollama local")
    assert memory.get_memory_by_id(item["id"], owner="REDACTED_2c7b6821719d")["history"]
    assert memory.archive_memory(memory_id=item["id"], owner="REDACTED_2c7b6821719d")
    assert memory.list_memories(owner="REDACTED_2c7b6821719d") == []
    assert memory.restore_memory(memory_id=item["id"], owner="REDACTED_2c7b6821719d")
    assert memory.expire_memory(memory_id=item["id"], owner="REDACTED_2c7b6821719d")
    assert memory.get_memory_by_id(item["id"], owner="REDACTED_2c7b6821719d")["state"] == "expired"
    assert memory.restore_memory(memory_id=item["id"], owner="REDACTED_2c7b6821719d")
    service = LongTermMemoryService(tmp_path / "long_term.json", memory)
    summary = service.regenerate_summary(user_id="REDACTED_2c7b6821719d", context="Proyecto Atlas", memory_ids=[item["id"]])
    assert summary["source_memory_ids"] == [item["id"]]
    assert summary["updated_at"]


def test_consolidation_only_proposes_and_preserves_originals(tmp_path):
    memory, _ = build(tmp_path)
    memory.remember("REDACTED_2c7b6821719d", "Mi coche es un Hyundai i30 N", "private")
    memory.remember("REDACTED_2c7b6821719d", "Mi coche es Hyundai i30 N", "private")
    service = LongTermMemoryService(tmp_path / "long_term.json", memory)
    candidates = service.consolidation_candidates(user_id="REDACTED_2c7b6821719d", threshold=0.7)
    assert candidates and candidates[0]["action"] == "propose_merge"
    assert memory.count_memories("REDACTED_2c7b6821719d") == 2


def test_semantic_search_performance_on_hundreds_of_memories(tmp_path):
    memory = MemoryManager(tmp_path / "memory")
    for index in range(200):
        memory.remember("REDACTED_2c7b6821719d", f"Dato personal número {index}", "private")
    memory.remember("REDACTED_2c7b6821719d", "Conduzco un Hyundai i30 N", "private")
    semantic = PersonalMemorySemanticIndex(tmp_path / "semantic.json", memory, FakeEmbedder())
    semantic.sync(user_id="REDACTED_2c7b6821719d")
    started = perf_counter()
    matches = semantic.search("Qué coche conduzco", user_id="REDACTED_2c7b6821719d", limit=5)
    elapsed = perf_counter() - started
    assert any("Hyundai" in item.memory["content"] for item in matches)
    assert elapsed < 1.0
