from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .constants import REVIEWED_STATUS
from .models import ProjectConfig, Sample
from .storage import DatasetLock, SnapshotStore, atomic_write_text, read_samples, serialize_csv
from .suggestions import DatasetSuggestionProvider, Suggestion


class DatasetProject:
    def __init__(self, config: ProjectConfig, read_only: bool = False):
        self.config = config
        self.read_only = read_only
        self.samples: list[Sample] = []
        self.current_index = 0
        self.navigation_history: list[str] = []
        self.dirty = False
        self._source_stat: tuple[int, int] | None = None
        self.session_started = datetime.now(UTC)
        self.reviewed_this_session: set[str] = set()
        self.lock = DatasetLock(config.workspace_dir / "dataset.lock", read_only=read_only)
        self.snapshots = SnapshotStore(config.workspace_dir / "snapshots", config.backup_count)

    @classmethod
    def open(cls, config: ProjectConfig, read_only: bool = False) -> "DatasetProject":
        project = cls(config, read_only)
        project.lock.acquire()
        try:
            project.samples = read_samples(config.metadata_path)
            project._validate_unique()
            stat = config.metadata_path.stat()
            project._source_stat = (stat.st_mtime_ns, stat.st_size)
            project._load_session()
            return project
        except BaseException:
            project.lock.release()
            raise

    def close(self) -> None:
        if self.dirty and not self.read_only:
            self.save()
        self._save_session()
        self.lock.release()

    def _validate_unique(self) -> None:
        ids = [sample.sample_id for sample in self.samples]
        if len(ids) != len(set(ids)):
            duplicate = next(key for key, count in Counter(ids).items() if count > 1)
            raise ValueError(f"sample_id duplicado: {duplicate}")

    @property
    def current(self) -> Sample:
        return self.samples[self.current_index]

    def navigate(self, index: int) -> Sample:
        if not self.samples:
            raise IndexError("Dataset vacío")
        index = max(0, min(index, len(self.samples) - 1))
        if self.samples:
            self.navigation_history.append(self.current.sample_id)
            del self.navigation_history[:-100]
        self.current_index = index
        return self.current

    def find_index(self, sample_id_or_number: str | int) -> int:
        if isinstance(sample_id_or_number, int) or str(sample_id_or_number).isdigit():
            number = int(sample_id_or_number)
            if 1 <= number <= len(self.samples):
                return number - 1
        value = str(sample_id_or_number).casefold()
        for index, sample in enumerate(self.samples):
            if sample.sample_id.casefold() == value or sample.audio_file.casefold() == value:
                return index
        raise KeyError(sample_id_or_number)

    def search(self, query: str = "", **filters: Any) -> list[int]:
        words = [word for word in query.casefold().split() if word]
        result: list[int] = []
        for index, sample in enumerate(self.samples):
            haystack = f"{sample.sample_id} {sample.audio_file} {sample.text} {sample.normalized_text}".casefold()
            if not all(word in haystack for word in words):
                continue
            if filters.get("source_game") and sample.source_game != filters["source_game"]:
                continue
            if filters.get("review_status") and sample.review_status != filters["review_status"]:
                continue
            if filters.get("emotion") and sample.emotion != filters["emotion"]:
                continue
            personality = filters.get("personality")
            if personality and personality not in sample.personality_tags:
                continue
            if filters.get("pending_only") and sample.review_status != "pending_review":
                continue
            if filters.get("personality_strength") and sample.personality_strength != filters["personality_strength"]:
                continue
            result.append(index)
        return result

    def update_current(self, *, human: bool = True, autosave: bool = True, **changes: Any) -> Sample:
        if self.read_only:
            raise PermissionError("Dataset abierto en modo solo lectura")
        sample = self.current
        for key, value in changes.items():
            if not hasattr(sample, key) or key == "text":
                if key == "text":
                    raise PermissionError("El texto verificado no se sobrescribe desde la edición normal")
                raise AttributeError(key)
            setattr(sample, key, value)
        if "normalized_text" in changes:
            sample.text_modified = sample.normalized_text != sample.original_normalized_text
        if human and any(key in changes for key in ("emotion", "emotion_confidence")):
            sample.emotion_source = "human"
        sample.updated_at = datetime.now(UTC).isoformat()
        self.dirty = True
        if sample.review_status in REVIEWED_STATUS:
            sample.needs_human_review = False
            sample.reviewed_at = sample.reviewed_at or sample.updated_at
            self.reviewed_this_session.add(sample.sample_id)
        if autosave:
            self.save()
        return sample

    def apply_suggestion(self, provider: DatasetSuggestionProvider) -> Suggestion:
        suggestion = provider.suggest(self.current)
        self.update_current(
            human=True, emotion=suggestion.emotion, intention=suggestion.intention,
            energy=suggestion.energy, personality_tags=suggestion.personality_tags,
            conversation_use=suggestion.conversation_use,
        )
        return suggestion

    def save(self) -> None:
        if self.read_only:
            raise PermissionError("Dataset abierto en modo solo lectura")
        if self.external_changes_detected():
            raise RuntimeError("Los metadatos han cambiado externamente; no se sobrescriben")
        self.snapshots.create(self.config.metadata_path)
        journal = self.config.workspace_dir / "recovery.json"
        atomic_write_text(journal, json.dumps({"state": "saving", "target": str(self.config.metadata_path), "at": datetime.now(UTC).isoformat()}))
        atomic_write_text(self.config.metadata_path, serialize_csv(self.samples))
        stat = self.config.metadata_path.stat()
        self._source_stat = (stat.st_mtime_ns, stat.st_size)
        journal.unlink(missing_ok=True)
        self.dirty = False

    def external_changes_detected(self) -> bool:
        if self._source_stat is None or not self.config.metadata_path.exists():
            return True
        stat = self.config.metadata_path.stat()
        return (stat.st_mtime_ns, stat.st_size) != self._source_stat

    def recover_latest_snapshot(self) -> Path:
        if self.read_only:
            raise PermissionError("Dataset abierto en modo solo lectura")
        latest = self.snapshots.latest_valid()
        if latest is None:
            raise FileNotFoundError("No hay snapshots válidos")
        recovered = read_samples(latest)
        atomic_write_text(self.config.metadata_path, serialize_csv(recovered))
        self.samples = recovered
        stat = self.config.metadata_path.stat()
        self._source_stat = (stat.st_mtime_ns, stat.st_size)
        return latest

    def statistics(self) -> dict[str, Any]:
        total = len(self.samples)
        reviewed = [s for s in self.samples if s.review_status in REVIEWED_STATUS]
        return {
            "total": total,
            "duration_seconds": sum(s.duration_seconds for s in self.samples),
            "reviewed": len(reviewed),
            "reviewed_duration_seconds": sum(s.duration_seconds for s in reviewed),
            "pending": sum(s.review_status == "pending_review" for s in self.samples),
            "excluded": sum(s.review_status == "excluded" for s in self.samples),
            "completion_percent": (len(reviewed) / total * 100) if total else 0,
            "emotions": Counter(s.emotion for s in self.samples),
            "intentions": Counter(s.intention for s in self.samples),
            "energy": Counter(s.energy for s in self.samples),
            "quality": Counter(s.quality for s in self.samples),
            "games": Counter(s.source_game for s in self.samples),
            "personality": Counter(tag for s in self.samples for tag in s.personality_tags),
            "tts_candidates": sum(s.tts_usable and s.review_status in {"accepted", "accepted_with_notes"} for s in self.samples),
            "personality_candidates": sum(s.personality_usable for s in self.samples),
            "iconic": sum(s.personality_strength == "iconica" for s in self.samples),
            "reviewed_this_session": len(self.reviewed_this_session),
        }

    def _session_path(self) -> Path:
        return self.config.workspace_dir / "session.json"

    def _load_session(self) -> None:
        try:
            data = json.loads(self._session_path().read_text(encoding="utf-8"))
            self.current_index = self.find_index(data.get("last_sample", 1))
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            self.current_index = 0

    def _save_session(self) -> None:
        if not self.samples:
            return
        atomic_write_text(self._session_path(), json.dumps({
            "last_sample": self.current.sample_id,
            "reviewed_this_session": sorted(self.reviewed_this_session),
            "closed_at": datetime.now(UTC).isoformat(),
        }, ensure_ascii=False, indent=2))

