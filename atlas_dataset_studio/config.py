from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .models import ProjectConfig
from .storage import atomic_write_text


def app_data_dir() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return root / "AtlasDatasetStudio"


def workspace_for(metadata_path: Path) -> Path:
    key = hashlib.sha256(str(metadata_path.resolve()).encode("utf-8")).hexdigest()[:16]
    return app_data_dir() / "projects" / key


def load_project(path: Path) -> ProjectConfig:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return ProjectConfig.from_dict(data, path.parent)


def save_project(path: Path, config: ProjectConfig) -> None:
    atomic_write_text(path, json.dumps(config.to_dict(path.parent), ensure_ascii=False, indent=2))


def remember_last_project(path: Path) -> None:
    atomic_write_text(app_data_dir() / "state.json", json.dumps({"last_project": str(path.resolve())}, ensure_ascii=False, indent=2))


def last_project() -> Path | None:
    try:
        value = json.loads((app_data_dir() / "state.json").read_text(encoding="utf-8"))["last_project"]
        path = Path(value)
        return path if path.is_file() else None
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        return None

