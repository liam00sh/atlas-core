"""Widgets de escritorio para Raspberry e incidencias.

Se ejecutan como ventanas sin marco. Permanecen en el fondo del
escritorio y las ventanas normales pueden colocarse encima.
"""

from __future__ import annotations

import json
from pathlib import Path
import time
import tkinter as tk


BANNER_ALPHA = 0.82
RASPBERRY_PANEL_TITLE = "ATLAS · ESTADO DE LA RPi"
SERVICES_PANEL_TITLE = "ATLAS · SERVICIOS"


class DesktopWidgets:
    def __init__(
        self,
        status_path: str | Path,
        *,
        refresh_ms: int = 2000,
        demo_mode: bool = False,
    ) -> None:
        self.status_path = Path(status_path)
        self.refresh_ms = refresh_ms
        self.demo_mode = demo_mode
        self.demo_index = 0
        self.root = tk.Tk()
        self.root.withdraw()

        self.raspberry = self._build_window(
            width=430,
            height=560,
            x_offset=19,
            y_offset=390,
            anchor_right=True,
            alpha=None,
        )
        self.raspberry_title_label = tk.Label(
            self.raspberry,
            text=f"{RASPBERRY_PANEL_TITLE}\n",
            justify="left",
            anchor="nw",
            fg="#a9adb3",
            bg="#111111",
            font=("Consolas", 12, "bold"),
        )
        self.raspberry_title_label.pack(
            anchor="w",
            padx=12,
            pady=(10, 0),
        )

        self.raspberry_label = tk.Label(
            self.raspberry,
            text="\nSin datos",
            justify="left",
            anchor="nw",
            fg="#a9adb3",
            bg="#111111",
            font=("Consolas", 11),
        )
        self.raspberry_label.pack(
            anchor="w",
            padx=12,
            pady=(0, 10),
        )

        self.raspberry_services_title_label = tk.Label(
            self.raspberry,
            text=f"{SERVICES_PANEL_TITLE}\n",
            justify="left",
            anchor="nw",
            fg="#a9adb3",
            bg="#111111",
            font=("Consolas", 12, "bold"),
        )
        self.raspberry_services_title_label.pack(
            anchor="w",
            padx=12,
            pady=(8, 0),
        )

        self.raspberry_services_label = tk.Label(
            self.raspberry,
            text="Sin datos",
            justify="left",
            anchor="nw",
            fg="#a9adb3",
            bg="#111111",
            font=("Consolas", 11),
        )
        self.raspberry_services_label.pack(
            anchor="w",
            padx=12,
            pady=(0, 10),
        )

        # Fondo semitransparente común para todos los avisos del banner.
        # La opacidad se aplica a la ventana completa para que el fondo
        # del escritorio siga siendo visible sin perder legibilidad.
        self.banner = self._build_window(
            width=520,
            height=230,
            x_offset=520,
            y_offset=97,
            anchor_right=True,
            alpha=BANNER_ALPHA,
        )
        self.banner.configure(bg="#111111")

        self.banner_title_label = tk.Label(
            self.banner,
            text="ATLAS · AVISO",
            justify="left",
            anchor="nw",
            fg="#a9adb3",
            bg="#111111",
            font=("Segoe UI", 13, "bold"),
        )
        self.banner_title_label.pack(
            fill="x",
            padx=16,
            pady=(14, 0),
        )

        self.banner_type_label = tk.Label(
            self.banner,
            text="",
            justify="left",
            anchor="nw",
            fg="#ff5c5c",
            bg="#111111",
            font=("Segoe UI", 13, "bold"),
        )
        self.banner_type_label.pack(
            fill="x",
            padx=16,
            pady=(12, 0),
        )

        self.banner_message_label = tk.Label(
            self.banner,
            text="",
            justify="left",
            anchor="nw",
            fg="#ff5c5c",
            bg="#111111",
            font=("Segoe UI", 13),
            wraplength=488,
        )
        self.banner_message_label.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=(4, 14),
        )
        self.banner.withdraw()

        self.started_at = time.monotonic()

    def _build_window(
        self,
        *,
        width: int,
        height: int,
        x_offset: int,
        y_offset: int,
        anchor_right: bool,
        alpha: float | None,
    ) -> tk.Toplevel:
        window = tk.Toplevel(self.root)
        screen_w = window.winfo_screenwidth()
        x = screen_w - width - x_offset if anchor_right else x_offset
        window.geometry(f"{width}x{height}+{x}+{y_offset}")
        window.overrideredirect(True)
        window.attributes("-topmost", False)
        if alpha is not None:
            try:
                window.attributes("-alpha", alpha)
            except tk.TclError:
                pass
        window.configure(bg="#111111")
        if alpha is None:
            try:
                window.wm_attributes("-transparentcolor", "#111111")
            except tk.TclError:
                pass
        self._make_click_through(window)
        self._send_behind_app_windows(window)
        return window

    @staticmethod
    def _window_handle(window: tk.Toplevel) -> int:
        import ctypes

        return ctypes.windll.user32.GetParent(window.winfo_id())

    def _make_click_through(self, window: tk.Toplevel) -> None:
        import os

        if os.name != "nt":
            return

        try:
            import ctypes

            hwnd = self._window_handle(window)
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ctypes.windll.user32.SetWindowLongW(
                hwnd,
                -20,
                style | 0x80000 | 0x20,
            )
        except Exception:
            pass

    def _send_behind_app_windows(self, window: tk.Toplevel) -> None:
        import os

        if os.name != "nt":
            return

        try:
            import ctypes

            hwnd = self._window_handle(window)

            HWND_BOTTOM = 1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010

            ctypes.windll.user32.SetWindowPos(
                hwnd,
                HWND_BOTTOM,
                0,
                0,
                0,
                0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE,
            )
        except Exception:
            pass

    @staticmethod
    def _gib(value: int | float | None) -> str:
        if not isinstance(value, (int, float)):
            return "N/D"
        return f"{value / (1024 ** 3):.1f} GB"

    def _render_raspberry(self, payload: dict) -> str:
        result = payload.get("raspberry") or {}
        details = result.get("details") or {}
        memory = details.get("memory") or {}
        sd = details.get("sd") or {}
        usb = details.get("usb") or {}
        docker = details.get("docker") or {}
        ha = details.get("home_assistant") or {}

        state = str(result.get("state", "unknown")).upper()
        return "\n".join([
            f"ESTADO       {state}",
            f"HOST         {details.get('hostname', 'N/D')}",
            f"IP           {(details.get('network') or {}).get('primary_ip', 'N/D')}",
            f"TEMP         {details.get('temperature_c', 'N/D')} ºC",
            f"RAM          {self._gib(memory.get('used_bytes'))} / {self._gib(memory.get('total_bytes'))}",
            f"SD USO       {sd.get('used_percent', 'N/D')} %",
            f"SD LIBRE     {self._gib(sd.get('free_bytes'))}",
            f"DISCO ATLAS  {'OK' if usb.get('mounted') else 'NO MONTADO'}",
            f"DISCO LIBRE  {self._gib(usb.get('free_bytes'))}",
            f"DOCKER       {'OK' if docker.get('service_active') else 'ERROR'}",
            f"HOME ASSIST. {'OK' if ha.get('container_running') else 'ERROR'}",
            f"UPTIME       {int(details.get('uptime_seconds', 0) // 3600)} h",
            f"ÚLTIMO CHECK {result.get('checked_at', 'N/D')[-14:-6]}",
        ])

    def _render_services(self, payload: dict) -> str:
        supervisor = payload.get("supervisor") or {}
        checks = supervisor.get("checks") or {}
        if not checks:
            checks = payload.get("services") or {}
        if not checks:
            return "Sin datos"

        lines: list[str] = []
        for check_id, check in sorted(checks.items()):
            item = check or {}
            if "state" in item:
                status = str(item.get("state", "unknown")).upper()
            else:
                status = "OK" if bool(item.get("healthy", False)) else "ERROR"
            lines.append(f"{check_id[:18]:18} {status}")
        return "\n".join(lines)

    def _render_banner(self, payload: dict) -> tuple[str, str, str] | None:
        incidents = payload.get("incidents") or []
        if not incidents:
            raspberry = payload.get("raspberry") or {}
            state = str(raspberry.get("state", "unknown")).casefold()
            available = raspberry.get("available")
            message = str(raspberry.get("message", "")).strip()
            if available is False or state in {
                "critical",
                "error",
                "offline",
                "unavailable",
                "unknown",
                "",
            }:
                return (
                    "🔴 CRÍTICO",
                    message or (
                        "No se puede obtener el estado de la Raspberry. "
                        "Puede estar apagada, sin red o sin acceso SSH. "
                        "Las funciones alojadas en ella no estarán disponibles."
                    ),
                    "#ff5c5c",
                )
            if state == "warning":
                return (
                    "🟡 ADVERTENCIA",
                    message or "La Raspberry funciona con avisos.",
                    "#ffd166",
                )

            services = payload.get("services") or {}
            unhealthy = [
                name
                for name, item in services.items()
                if not bool((item or {}).get("healthy", False))
            ]
            if state == "ok" and not unhealthy:
                return (
                    "🟢 INFORMACIÓN",
                    "Atlas funciona correctamente. La Raspberry, Telegram, los avisos y los servicios monitorizados están operativos.",
                    "#42d392",
                )
            return None

        incident = incidents[0]
        severity = str(incident.get("severity", "critical")).lower()
        title = str(incident.get("title", "Incidencia"))
        message = str(incident.get("message", ""))

        severity_map = {
            "info": ("🟢 INFORMACIÓN", "#42d392"),
            "information": ("🟢 INFORMACIÓN", "#42d392"),
            "warning": ("🟡 ADVERTENCIA", "#ffd166"),
            "critical": ("🔴 CRÍTICO", "#ff5c5c"),
            "recovery": ("🔵 RECUPERACIÓN", "#5aa9ff"),
        }
        label, color = severity_map.get(
            severity,
            ("🔴 CRÍTICO", "#ff5c5c"),
        )
        body = title if not message else f"{title}\n{message}"
        return label, body, color

    def _demo_banner(self) -> tuple[str, str, str]:
        demos = [
            (
                "🟢 INFORMACIÓN",
                "Atlas funciona correctamente. Este aviso es solo una demostración visual.",
                "#42d392",
            ),
            (
                "🟡 ADVERTENCIA",
                "La temperatura de la Raspberry está acercándose al límite configurado.",
                "#ffd166",
            ),
            (
                "🔴 CRÍTICO",
                "Home Assistant no responde. Algunas automatizaciones pueden no estar disponibles.",
                "#ff5c5c",
            ),
            (
                "🔵 RECUPERACIÓN",
                "Home Assistant vuelve a estar disponible y la incidencia se ha cerrado.",
                "#5aa9ff",
            ),
        ]
        return demos[self.demo_index % len(demos)]

    def _advance_demo(self) -> None:
        self.demo_index = (self.demo_index + 1) % 4
        self.root.after(3500, self._advance_demo)

    def _information_window_active(self) -> bool:
        """
        El aviso verde aparece durante los primeros 30 minutos tras iniciar
        sesión y vuelve a mostrarse cada 3 horas durante 30 minutos.
        """
        elapsed_seconds = time.monotonic() - self.started_at
        cycle_seconds = 3 * 60 * 60
        visible_seconds = 30 * 60
        return (elapsed_seconds % cycle_seconds) < visible_seconds

    def _show_banner(
        self,
        type_text: str,
        message_text: str,
        *,
        color: str,
    ) -> None:
        self.banner_title_label.configure(fg=color)
        self.banner_type_label.configure(
            text=type_text,
            fg=color,
        )
        self.banner_message_label.configure(
            text=message_text,
            fg=color,
        )
        self.banner.deiconify()
        self._send_behind_app_windows(self.banner)

    def refresh(self) -> None:
        try:
            payload = json.loads(self.status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}

        self.raspberry_label.config(text=self._render_raspberry(payload))
        self.raspberry_services_label.config(text=self._render_services(payload))

        if self.demo_mode:
            type_text, message_text, color = self._demo_banner()
            if type_text == "🟢 INFORMACIÓN" and not self._information_window_active():
                self.banner.withdraw()
            else:
                self._show_banner(
                    type_text,
                    message_text,
                    color=color,
                )
        else:
            banner = self._render_banner(payload)
            if banner is None:
                self.banner.withdraw()
            else:
                type_text, message_text, color = banner
                if type_text == "🟢 INFORMACIÓN" and not self._information_window_active():
                    self.banner.withdraw()
                else:
                    self._show_banner(
                        type_text,
                        message_text,
                        color=color,
                    )

        self._send_behind_app_windows(self.raspberry)
        self.root.after(self.refresh_ms, self.refresh)

    def run(self) -> None:
        if self.demo_mode:
            self.root.after(3500, self._advance_demo)
        self.refresh()
        self.root.mainloop()


def main() -> None:
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="Widgets de escritorio de Atlas.",
    )
    parser.add_argument(
        "--demo-banner",
        action="store_true",
        help=(
            "Muestra automáticamente avisos de información, "
            "advertencia, crítico y recuperación."
        ),
    )
    args = parser.parse_args()

    status_path = os.getenv(
        "ATLAS_SUPERVISOR_STATUS_PATH",
        "data/monitoring/supervisor_status.json",
    )
    DesktopWidgets(
        status_path,
        demo_mode=args.demo_banner,
    ).run()


if __name__ == "__main__":
    main()
