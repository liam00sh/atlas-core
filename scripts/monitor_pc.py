"""Overlay ligero de monitorización para Proyecto Atlas en Windows."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time
import tkinter as tk

try:
    import psutil
except ImportError as exc:
    raise SystemExit("Falta psutil. Ejecuta: python -m pip install psutil") from exc

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "data" / "monitoring" / "pc_status.json"
REFRESH_MS = 2000


def _run(command: list[str], timeout: float = 2.0) -> str:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return result.stdout.strip()
    except Exception:
        return ""


def gpu_status() -> dict[str, str]:
    if not shutil.which("nvidia-smi"):
        return {}
    output = _run([
        "nvidia-smi",
        "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
        "--format=csv,noheader,nounits",
    ])
    if not output:
        return {}
    try:
        usage, used, total, temp = [part.strip() for part in output.splitlines()[0].split(",")]
        return {"usage": usage, "used": used, "total": total, "temp": temp}
    except ValueError:
        return {}


def wifi_status() -> str:
    output = _run(["netsh", "wlan", "show", "interfaces"])
    for line in output.splitlines():
        if "Signal" in line or "Señal" in line:
            return line.split(":", 1)[-1].strip()
    return "—"


def internet_status() -> str:
    try:
        with socket.create_connection(("1.1.1.1", 53), timeout=1.0):
            return "OK"
    except OSError:
        return "Sin conexión"


def temperatures() -> str:
    try:
        values = psutil.sensors_temperatures(fahrenheit=False)
    except Exception:
        values = {}
    readings = [entry.current for entries in values.values() for entry in entries if entry.current is not None]
    return f"{max(readings):.0f} °C" if readings else "—"


def disk_lines() -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for part in psutil.disk_partitions(all=False):
        mount = part.mountpoint
        if mount in seen:
            continue
        seen.add(mount)
        try:
            usage = psutil.disk_usage(mount)
        except (PermissionError, OSError):
            continue
        lines.append(f"DISCO {mount[:2]}  {usage.percent:>4.0f}%  {usage.free / 1024**3:>5.0f} GB libres")
    return lines[:6]


def snapshot() -> tuple[str, dict]:
    cpu = psutil.cpu_percent(interval=None)
    memory = psutil.virtual_memory()
    gpu = gpu_status()
    data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "cpu_percent": cpu,
        "ram_percent": memory.percent,
        "ram_used_gb": round(memory.used / 1024**3, 1),
        "ram_total_gb": round(memory.total / 1024**3, 1),
        "cpu_temperature": temperatures(),
        "wifi_signal": wifi_status(),
        "internet": internet_status(),
        "gpu": gpu,
    }
    lines = [
        "ATLAS · ESTADO DEL PC",
        f"CPU       {cpu:>5.1f}%   TEMP {data['cpu_temperature']}",
        f"RAM       {memory.percent:>5.1f}%   {data['ram_used_gb']:.1f}/{data['ram_total_gb']:.1f} GB",
    ]
    if gpu:
        lines.append(f"GPU       {gpu['usage']:>5}%   {gpu['used']}/{gpu['total']} MB   {gpu['temp']} °C")
    else:
        lines.append("GPU          —")
    lines.extend(disk_lines())
    lines.extend((f"WIFI      {data['wifi_signal']}", f"INTERNET  {data['internet']}"))
    return "\n".join(lines), data


class Overlay:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", False)
        self.root.configure(bg="#111111")
        try:
            self.root.attributes("-transparentcolor", "#111111")
        except tk.TclError:
            pass
        self.label = tk.Label(
            self.root,
            text="Iniciando monitor...",
            justify="left",
            anchor="nw",
            font=("Consolas", 11),
            fg="#a9adb3",
            bg="#111111",
        )
        self.label.pack(padx=12, pady=10)
        self.root.geometry("430x360+0+50")
        self._place_right()
        self._make_click_through()
        self._send_behind_app_windows()
        self.update()

    def _place_right(self) -> None:
        self.root.update_idletasks()
        width = 430
        x = max(0, self.root.winfo_screenwidth() - width - 20)
        self.root.geometry(f"{width}x360+{x}+80")

    def _make_click_through(self) -> None:
        if os.name != "nt":
            return
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20)
        except Exception:
            pass


    def _send_behind_app_windows(self) -> None:
        """Mantiene el monitor sobre el fondo, pero debajo de aplicaciones."""
        if os.name != "nt":
            return
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            HWND_BOTTOM = 1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            ctypes.windll.user32.SetWindowPos(
                hwnd, HWND_BOTTOM, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
            )
        except Exception:
            pass

    def update(self) -> None:
        def worker() -> None:
            text, data = snapshot()
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            temp = STATE_PATH.with_suffix(".tmp")
            temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(STATE_PATH)
            self.root.after(0, lambda: self.label.config(text=text))
        threading.Thread(target=worker, daemon=True).start()
        self._send_behind_app_windows()
        self.root.after(REFRESH_MS, self.update)

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    Overlay().run()
