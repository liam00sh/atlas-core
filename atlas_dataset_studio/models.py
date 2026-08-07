from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .constants import CORE_FIELDS


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "si", "sí"}


def _tags(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [item for item in str(value or "").split("|") if item]


@dataclass(slots=True)
class Sample:
    sample_id: str
    audio_file: str
    relative_path: str
    text: str
    normalized_text: str
    original_normalized_text: str = ""
    source_game: str = ""
    duration_seconds: float = 0.0
    sample_rate: int = 0
    channels: int = 0
    sample_width_bits: int = 0
    sha256: str = ""
    emotion: str = "neutral"
    emotion_confidence: str = "baja"
    emotion_source: str = "automatic"
    intention: str = "indeterminada"
    energy: str = "media"
    emotion_intensity: str = "media"
    personality_usable: bool = False
    personality_tags: list[str] = field(default_factory=list)
    personality_reason: str = ""
    personality_strength: str = "baja"
    conversation_use: list[str] = field(default_factory=list)
    tts_usable: bool = True
    quality: str = "buena"
    review_status: str = "pending_review"
    review_notes: str = ""
    needs_human_review: bool = True
    text_modified: bool = False
    updated_at: str = ""
    reviewed_at: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, row: dict[str, Any]) -> "Sample":
        known = {key: row.get(key, "") for key in CORE_FIELDS}
        return cls(
            sample_id=str(known["sample_id"]),
            audio_file=str(known["audio_file"] or known["relative_path"]),
            relative_path=str(known["relative_path"] or known["audio_file"]),
            text=str(known["text"]),
            normalized_text=str(known["normalized_text"] or known["text"]),
            original_normalized_text=str(known["original_normalized_text"] or known["normalized_text"] or known["text"]),
            source_game=str(known["source_game"]),
            duration_seconds=float(known["duration_seconds"] or 0),
            sample_rate=int(float(known["sample_rate"] or 0)),
            channels=int(float(known["channels"] or 0)),
            sample_width_bits=int(float(known["sample_width_bits"] or 0)),
            sha256=str(known["sha256"]),
            emotion=str(known["emotion"] or "neutral"),
            emotion_confidence=str(known["emotion_confidence"] or "baja"),
            emotion_source=str(known["emotion_source"] or "automatic"),
            intention=str(known["intention"] or "indeterminada"),
            energy=str(known["energy"] or "media"),
            emotion_intensity=str(known["emotion_intensity"] or known["energy"] or "media"),
            personality_usable=_bool(known["personality_usable"]),
            personality_tags=_tags(known["personality_tags"]),
            personality_reason=str(known["personality_reason"]),
            personality_strength=str(known["personality_strength"] or "baja"),
            conversation_use=_tags(known["conversation_use"]),
            tts_usable=_bool(known["tts_usable"], True),
            quality=str(known["quality"] or "buena"),
            review_status=str(known["review_status"] or "pending_review"),
            review_notes=str(known["review_notes"]),
            needs_human_review=_bool(known["needs_human_review"], True),
            text_modified=_bool(known["text_modified"]),
            updated_at=str(known["updated_at"]), reviewed_at=str(known["reviewed_at"]),
            extra={key: value for key, value in row.items() if key not in CORE_FIELDS},
        )

    def to_mapping(self) -> dict[str, Any]:
        result = {name: getattr(self, name) for name in CORE_FIELDS}
        result["personality_tags"] = "|".join(self.personality_tags)
        result["conversation_use"] = "|".join(self.conversation_use)
        result.update(self.extra)
        return result


@dataclass(slots=True)
class ProjectConfig:
    name: str
    preset: str
    dataset_type: str
    audio_root: Path
    metadata_path: Path
    workspace_dir: Path
    dataset_version: str = "1.0.0"
    backup_count: int = 5

    @classmethod
    def from_dict(cls, data: dict[str, Any], base: Path | None = None) -> "ProjectConfig":
        base = base or Path.cwd()
        resolve = lambda value: (base / value).resolve() if not Path(value).is_absolute() else Path(value)
        return cls(
            name=str(data["name"]), preset=str(data.get("preset", "daxter_es")),
            dataset_type=str(data.get("dataset_type", "voice/personality")),
            audio_root=resolve(data["audio_root"]), metadata_path=resolve(data["metadata_path"]),
            workspace_dir=resolve(data.get("workspace_dir", ".atlas_dataset_studio")),
            dataset_version=str(data.get("dataset_version", "1.0.0")),
            backup_count=int(data.get("backup_count", 5)),
        )

    def to_dict(self, relative_to: Path | None = None) -> dict[str, Any]:
        def path_value(path: Path) -> str:
            if relative_to:
                try:
                    return path.resolve().relative_to(relative_to.resolve()).as_posix()
                except ValueError:
                    pass
            return str(path)
        return {
            "name": self.name, "preset": self.preset, "dataset_type": self.dataset_type,
            "audio_root": path_value(self.audio_root), "metadata_path": path_value(self.metadata_path),
            "workspace_dir": path_value(self.workspace_dir), "dataset_version": self.dataset_version,
            "backup_count": self.backup_count,
        }
