"""Captura manual de micrófono con FFmpeg; nunca escucha en segundo plano."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import threading


class MicrophoneError(RuntimeError):
    pass


class ManualMicrophoneRecorder:
    """Graba solo entre dos acciones explícitas del usuario."""

    def __init__(
        self,
        *,
        device_name: str | None = None,
        ffmpeg_path: str | None = None,
        sample_rate: int = 16000,
    ) -> None:
        self.device_name = device_name or os.getenv("ATLAS_MICROPHONE_DEVICE", "").strip() or None
        self.ffmpeg_path = shutil.which("ffmpeg") if ffmpeg_path is None else ffmpeg_path
        self.sample_rate = sample_rate
        self._process: subprocess.Popen[bytes] | None = None
        self._lock = threading.RLock()

    def is_available(self) -> bool:
        return bool(os.name == "nt" and self.ffmpeg_path)

    def list_devices(self) -> tuple[str, ...]:
        if not self.is_available():
            return ()
        completed = subprocess.run(
            [str(self.ffmpeg_path), "-hide_banner", "-list_devices", "true", "-f", "dshow", "-i", "dummy"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        text = completed.stderr.decode("utf-8", errors="replace")
        devices: list[str] = []
        for line in text.splitlines():
            match = re.search(r'"([^"]+)"\s+\(audio\)', line)
            if match and match.group(1) not in devices:
                devices.append(match.group(1))
        return tuple(devices)

    def selected_device(self) -> str:
        if self.device_name:
            return self.device_name
        devices = self.list_devices()
        if not devices:
            raise MicrophoneError("No se ha detectado ningún micrófono de Windows.")
        return devices[0]

    def start(self, destination: str | Path) -> Path:
        with self._lock:
            if not self.is_available():
                raise MicrophoneError("FFmpeg no está disponible para grabar el micrófono.")
            if self._process is not None and self._process.poll() is None:
                raise MicrophoneError("Ya hay una grabación manual activa.")
            target = Path(destination)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.unlink(missing_ok=True)
            command = [
                str(self.ffmpeg_path), "-hide_banner", "-loglevel", "error", "-y",
                "-f", "dshow", "-i", f"audio={self.selected_device()}",
                "-ac", "1", "-ar", str(self.sample_rate), "-c:a", "pcm_s16le", str(target),
            ]
            self._process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return target

    def stop(self, *, timeout_seconds: float = 5.0) -> None:
        with self._lock:
            process = self._process
            if process is None:
                return
            if process.poll() is None:
                try:
                    if process.stdin is not None:
                        process.stdin.write(b"q\n")
                        process.stdin.flush()
                    process.wait(timeout=timeout_seconds)
                except (BrokenPipeError, OSError, subprocess.TimeoutExpired):
                    process.terminate()
                    try:
                        process.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        process.kill()
            self._process = None

    def record_on_enter(self, destination: str | Path, *, input_func=input) -> Path:
        input_func("Pulsa Enter para empezar a hablar…")
        target = self.start(destination)
        try:
            input_func("Grabando. Pulsa Enter para detener…")
        finally:
            self.stop()
        if not target.is_file() or target.stat().st_size <= 44:
            target.unlink(missing_ok=True)
            raise MicrophoneError("La grabación no contiene audio utilizable.")
        return target

    def close(self) -> None:
        self.stop()
