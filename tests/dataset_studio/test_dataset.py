from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path

import pytest

from atlas_dataset_studio.dataset import DatasetProject
from atlas_dataset_studio.storage import DatasetLock, atomic_write_text, read_samples
from atlas_dataset_studio.suggestions import HeuristicSuggestionProvider


def test_load_and_migrate_v1_preserves_fields(dataset_fixture):
    project = DatasetProject.open(dataset_fixture)
    try:
        assert len(project.samples) == 3
        assert project.current.original_normalized_text == "Hola Jak"
        assert project.current.extra["legacy_field"] == "keep-1"
        project.update_current(review_notes="migrated")
        reloaded = read_samples(dataset_fixture.metadata_path)
        assert reloaded[0].extra["legacy_field"] == "keep-1"
    finally: project.close()


def test_search_filters_navigation_and_history(dataset_fixture):
    project = DatasetProject.open(dataset_fixture)
    try:
        assert project.search("carrera") == [1]
        assert project.search(source_game="jak3") == [2]
        assert project.search(pending_only=True) == [0, 1, 2]
        assert project.find_index("daxter_0002") == 1
        project.navigate(2); assert project.current.sample_id == "daxter_0003"; assert project.navigation_history
        stats = project.statistics(); assert stats["last_sample"] == "daxter_0003"; assert stats["session_duration_seconds"] >= 0
    finally: project.close()


def test_text_normalized_and_human_emotion(dataset_fixture):
    project = DatasetProject.open(dataset_fixture)
    try:
        original = project.current.text
        project.update_current(normalized_text="Hola, Jak.", emotion="sonriente")
        assert project.current.text == original
        assert project.current.text_modified
        assert project.current.emotion_source == "human"
        with pytest.raises(PermissionError): project.update_current(text="silencioso")
    finally: project.close()


def test_multiple_tags_personality_and_conversation(dataset_fixture):
    project = DatasetProject.open(dataset_fixture)
    try:
        project.update_current(personality_usable=True, personality_tags=["humor", "leal"], personality_strength="iconica", conversation_use=["humor", "saludo"])
        project.close(); project = DatasetProject.open(dataset_fixture)
        assert project.current.personality_tags == ["humor", "leal"]
        assert project.current.conversation_use == ["humor", "saludo"]
    finally: project.close()


def test_autosave_atomic_snapshots_and_recovery(dataset_fixture):
    project = DatasetProject.open(dataset_fixture)
    try:
        project.update_current(review_notes="one")
        project.update_current(review_notes="two")
        assert list((dataset_fixture.workspace_dir / "snapshots").glob("*.csv"))
        latest = project.snapshots.latest_valid(); assert latest
        dataset_fixture.metadata_path.write_text("corrupt", encoding="utf-8")
        project._source_stat = (dataset_fixture.metadata_path.stat().st_mtime_ns, dataset_fixture.metadata_path.stat().st_size)
        project.recover_latest_snapshot()
        assert len(read_samples(dataset_fixture.metadata_path)) == 3
    finally: project.close()


def test_atomic_write_cleans_temporary_file(tmp_path):
    target = tmp_path / "data.txt"; atomic_write_text(target, "ok")
    assert target.read_text() == "ok"; assert not list(tmp_path.glob("*.tmp"))


def test_lock_read_only_and_orphan(dataset_fixture):
    first = DatasetLock(dataset_fixture.workspace_dir / "dataset.lock").acquire()
    try:
        with pytest.raises(RuntimeError): DatasetLock(first.path).acquire()
        readonly = DatasetLock(first.path, read_only=True).acquire(); assert not readonly.acquired
    finally: first.release()
    first.path.parent.mkdir(parents=True, exist_ok=True)
    first.path.write_text(json.dumps({"pid": 99999999, "created_at": time.time() - 100}), encoding="utf-8")
    recovered = DatasetLock(first.path, stale_after=1).acquire(); assert recovered.acquired; recovered.release()


def test_read_only_blocks_writes(dataset_fixture):
    project = DatasetProject.open(dataset_fixture, read_only=True)
    try:
        with pytest.raises(PermissionError): project.update_current(review_notes="no")
    finally: project.close()


def test_external_change_blocks_save(dataset_fixture):
    project = DatasetProject.open(dataset_fixture)
    try:
        dataset_fixture.metadata_path.write_text(dataset_fixture.metadata_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        assert project.external_changes_detected()
        with pytest.raises(RuntimeError): project.update_current(review_notes="no")
    finally:
        project.dirty = False; project.close()


def test_heuristic_never_overwrites_without_apply(dataset_fixture):
    project = DatasetProject.open(dataset_fixture)
    try:
        project.navigate(2); before = project.current.to_mapping().copy()
        suggestion = HeuristicSuggestionProvider().suggest(project.current)
        assert project.current.to_mapping() == before
        assert "humor" in suggestion.personality_tags
    finally: project.close()


@pytest.mark.parametrize("content,message", [("", "vacío"), ("wrong\nvalue\n", "faltan campos")])
def test_invalid_schema(tmp_path, content, message):
    path = tmp_path / "bad.csv"; path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=message): read_samples(path)


def test_corrupt_jsonl(tmp_path):
    path = tmp_path / "bad.jsonl"; path.write_text('{"sample_id":', encoding="utf-8")
    with pytest.raises(ValueError, match="JSONL corrupto"): read_samples(path)
