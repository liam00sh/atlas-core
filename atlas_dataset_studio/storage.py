from __future__ import annotations

import csv
import json
import os
import shutil
import socket
import tempfile
import time
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from .constants import CORE_FIELDS
from .models import Sample


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        last_error: PermissionError | None = None
        for delay in (0.0, 0.02, 0.05, 0.1, 0.2, 0.4):
            if delay:
                time.sleep(delay)
            try:
                os.replace(tmp, path)
                last_error = None
                break
            except PermissionError as exc:
                last_error = exc
        if last_error is not None:
            raise last_error
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def read_samples(path: Path) -> list[Sample]:
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix.lower() == ".jsonl":
        rows = []
        with path.open(encoding="utf-8-sig") as stream:
            for line_number, line in enumerate(stream, 1):
                if line.strip():
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"JSONL corrupto en línea {line_number}: {exc.msg}") from exc
    else:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("El archivo de metadatos está vacío")
    required = {"sample_id", "text"}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"Esquema inválido; faltan campos: {', '.join(sorted(missing))}")
    return [Sample.from_mapping(row) for row in rows]


def serialize_csv(samples: Iterable[Sample]) -> str:
    rows = [sample.to_mapping() for sample in samples]
    extras = sorted({key for row in rows for key in row if key not in CORE_FIELDS})
    fields = [*CORE_FIELDS, *extras]
    output = __import__("io").StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def serialize_jsonl(samples: Iterable[Sample]) -> str:
    return "".join(json.dumps(sample.to_mapping(), ensure_ascii=False) + "\n" for sample in samples)


class SnapshotStore:
    def __init__(self, directory: Path, keep: int = 5):
        self.directory = directory
        self.keep = max(1, keep)

    def create(self, source: Path) -> Path | None:
        if not source.is_file():
            return None
        self.directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        target = self.directory / f"{source.stem}.{stamp}{source.suffix}"
        shutil.copy2(source, target)
        snapshots = sorted(self.directory.glob(f"{source.stem}.*{source.suffix}"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in snapshots[self.keep:]:
            old.unlink(missing_ok=True)
        return target

    def latest_valid(self) -> Path | None:
        for candidate in sorted(self.directory.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                read_samples(candidate)
                return candidate
            except (OSError, ValueError):
                continue
        return None


class DatasetLock(AbstractContextManager["DatasetLock"]):
    def __init__(self, path: Path, read_only: bool = False, stale_after: int = 86_400):
        self.path = path
        self.read_only = read_only
        self.stale_after = stale_after
        self.acquired = False

    def acquire(self) -> "DatasetLock":
        if self.read_only:
            return self
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"pid": os.getpid(), "host": socket.gethostname(), "created_at": time.time()}
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                current = json.loads(self.path.read_text(encoding="utf-8"))
                age = time.time() - float(current.get("created_at", 0))
                if age > self.stale_after and not _pid_alive(int(current.get("pid", -1))):
                    self.path.unlink()
                    return self.acquire()
            except (OSError, ValueError, json.JSONDecodeError):
                pass
            raise RuntimeError("Dataset abierto en otra instancia.")
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream)
        self.acquired = True
        return self

    def release(self) -> None:
        if self.acquired:
            self.path.unlink(missing_ok=True)
            self.acquired = False

    def __enter__(self) -> "DatasetLock":
        return self.acquire()

    def __exit__(self, *_: object) -> None:
        self.release()


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True
