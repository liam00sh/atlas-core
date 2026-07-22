"""Escucha apagado, reinicio, suspensión y reanudación de Windows.

La ventana oculta recibe WM_QUERYENDSESSION/WM_ENDSESSION para cierre de
sesión, apagado y reinicio. También recibe WM_POWERBROADCAST para suspensión
y reanudación. El envío a Telegram se realiza en un proceso independiente y
queda registrado con resultado detallado.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
NOTIFY_SCRIPT = PROJECT_ROOT / "scripts" / "notify_telegram_shutdown.py"
STATE_DIR = PROJECT_ROOT / "data" / "integrations" / "telegram"
LOG_DIR = PROJECT_ROOT / "logs" / "telegram"
LOCK_FILE = STATE_DIR / "windows_shutdown_listener.lock"
LOG_FILE = LOG_DIR / "windows_shutdown_listener.log"

LRESULT = ctypes.c_ssize_t
WM_QUERYENDSESSION = 0x0011
WM_ENDSESSION = 0x0016
WM_POWERBROADCAST = 0x0218
PBT_APMSUSPEND = 0x0004
PBT_APMRESUMEAUTOMATIC = 0x0012
PBT_APMRESUMESUSPEND = 0x0007
ENDSESSION_LOGOFF = 0x80000000
ENDSESSION_CRITICAL = 0x40000000

USER32 = ctypes.WinDLL("user32", use_last_error=True)
KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)

WNDPROC = ctypes.WINFUNCTYPE(
    LRESULT,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


USER32.DefWindowProcW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
USER32.DefWindowProcW.restype = LRESULT
USER32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
USER32.RegisterClassW.restype = wintypes.ATOM
USER32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    wintypes.HMENU,
    wintypes.HINSTANCE,
    wintypes.LPVOID,
]
USER32.CreateWindowExW.restype = wintypes.HWND
USER32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
]
USER32.GetMessageW.restype = wintypes.BOOL
USER32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
USER32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
KERNEL32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
KERNEL32.GetModuleHandleW.restype = wintypes.HMODULE

_notify_lock = threading.Lock()
_notified_events: set[str] = set()
_window_proc_reference = None


def _log(message: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    with LOG_FILE.open("a", encoding="utf-8") as stream:
        stream.write(f"{timestamp} {message}\n")


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    handle = KERNEL32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if handle:
        KERNEL32.CloseHandle(handle)
        return True
    return False


def _acquire_lock() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            previous_pid = int(LOCK_FILE.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            previous_pid = 0
        if _process_exists(previous_pid):
            raise RuntimeError("Ya existe un listener de ciclo de vida activo.")
        LOCK_FILE.unlink(missing_ok=True)

    descriptor = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
    finally:
        os.close(descriptor)


def _release_lock() -> None:
    try:
        if int(LOCK_FILE.read_text(encoding="utf-8").strip()) == os.getpid():
            LOCK_FILE.unlink(missing_ok=True)
    except (OSError, ValueError):
        pass


def _shutdown_kind(lparam: int) -> str:
    flags = int(lparam) & 0xFFFFFFFF
    if flags & ENDSESSION_LOGOFF:
        return "logoff"
    if flags & ENDSESSION_CRITICAL:
        return "critical_shutdown"
    return "shutdown"


def _send_notification(event: str) -> None:
    with _notify_lock:
        if event in _notified_events:
            return
        _notified_events.add(event)

    _log(f"Evento de Windows detectado: {event}; enviando aviso.")
    if not NOTIFY_SCRIPT.is_file():
        _log(f"No existe el script de notificación: {NOTIFY_SCRIPT}")
        return

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    command = [
        sys.executable,
        str(NOTIFY_SCRIPT),
        "--event",
        event,
        "--timeout",
        "3.5",
    ]

    try:
        completed = subprocess.run(
            command,
            cwd=str(PROJECT_ROOT),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
            creationflags=creation_flags,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        _log("La notificación excedió 5 segundos y Windows continuó el cierre.")
        return
    except OSError as exc:
        _log(f"No se pudo ejecutar la notificación: {exc}")
        return

    output = completed.stdout.strip()
    if output:
        for line in output.splitlines():
            _log(f"notifier: {line}")
    _log(f"Notificación finalizada con código {completed.returncode}.")


def _window_proc(hwnd, message, wparam, lparam):
    if message == WM_QUERYENDSESSION:
        _send_notification(_shutdown_kind(lparam))
        return 1

    if message == WM_ENDSESSION and bool(wparam):
        _send_notification(_shutdown_kind(lparam))
        return 0

    if message == WM_POWERBROADCAST:
        event = int(wparam)
        if event == PBT_APMSUSPEND:
            _send_notification("suspend")
            return 1
        if event in {PBT_APMRESUMEAUTOMATIC, PBT_APMRESUMESUSPEND}:
            _send_notification("resume")
            return 1

    return USER32.DefWindowProcW(hwnd, message, wparam, lparam)


def main() -> int:
    if os.name != "nt":
        print("Este listener solo funciona en Windows.")
        return 2

    try:
        _acquire_lock()
    except RuntimeError as exc:
        _log(str(exc))
        return 11

    global _window_proc_reference
    _window_proc_reference = WNDPROC(_window_proc)
    class_name = f"ProyectoAtlasWindowsLifecycle_{os.getpid()}"
    instance = KERNEL32.GetModuleHandleW(None)

    window_class = WNDCLASSW()
    window_class.lpfnWndProc = _window_proc_reference
    window_class.hInstance = instance
    window_class.lpszClassName = class_name

    try:
        if not USER32.RegisterClassW(ctypes.byref(window_class)):
            raise ctypes.WinError(ctypes.get_last_error())

        hwnd = USER32.CreateWindowExW(
            0,
            class_name,
            "Proyecto Atlas Windows Lifecycle",
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            instance,
            None,
        )
        if not hwnd:
            raise ctypes.WinError(ctypes.get_last_error())

        _log(f"Listener de ciclo de vida iniciado PID={os.getpid()} con {sys.executable}.")
        message = wintypes.MSG()
        while True:
            result = USER32.GetMessageW(ctypes.byref(message), None, 0, 0)
            if result == 0:
                break
            if result == -1:
                raise ctypes.WinError(ctypes.get_last_error())
            USER32.TranslateMessage(ctypes.byref(message))
            USER32.DispatchMessageW(ctypes.byref(message))
    finally:
        _release_lock()
        _log("Listener de ciclo de vida detenido.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
