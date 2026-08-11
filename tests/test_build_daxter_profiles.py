import csv
import hashlib

from tools.build_daxter_profiles import EMOTIONS, build_emotion_catalog, build_personality_profile, load_metadata


def _row(sample_id="s1", emotion="neutral", tags="humor"):
    return {
        "sample_id": sample_id, "audio_file": f"{sample_id}.wav", "text": "Una frase breve.",
        "duration_seconds": "2.0", "emotion": emotion, "emotion_confidence": "alta",
        "emotion_source": "human", "intention": "afirmacion", "energy": "media",
        "emotion_intensity": "media", "quality": "buena", "personality_usable": "true",
        "personality_tags": tags, "personality_strength": "media", "context_confidence": "alta",
        "source_game": "jak2",
    }


def test_catalog_contains_all_fifteen_emotions_and_sonoliento_fallback():
    catalog = build_emotion_catalog([_row()], "abc", {"profile_id": "winner"})
    assert [item["id"] for item in catalog["emotions"]] == list(EMOTIONS)
    sonoliento = next(item for item in catalog["emotions"] if item["id"] == "sonoliento")
    assert sonoliento["dataset_evidence"]["examples"] == 0
    assert sonoliento["fallback_emotion"] == "cansado"


def test_personality_profile_requires_evidence_before_supporting_trait():
    rows = [_row(f"s{index}") for index in range(3)]
    profile = build_personality_profile(rows, "abc")
    assert profile["traits"]["humor"]["supported"] is True
    assert profile["traits"]["sarcasmo"]["supported"] is False


def test_metadata_input_is_never_modified(tmp_path):
    metadata = tmp_path / "metadata.csv"
    rows = [_row(f"s{index:04d}") for index in range(1300)]
    with metadata.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    before = hashlib.sha256(metadata.read_bytes()).hexdigest()
    loaded = load_metadata(metadata)
    build_emotion_catalog(loaded, before, {"profile_id": "winner"})
    build_personality_profile(loaded, before)
    assert hashlib.sha256(metadata.read_bytes()).hexdigest() == before
