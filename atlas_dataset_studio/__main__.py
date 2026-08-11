from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from .app.main_window import MainWindow
from .config import last_project, load_project
from .dataset import DatasetProject


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Atlas Dataset Studio")
    parser.add_argument("--project", type=Path, help="Configuración local de proyecto JSON")
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--smoke-test", action="store_true", help="Arranca y cierra la UI sin interacción")
    args = parser.parse_args(argv)
    app = QApplication(sys.argv[:1]); app.setApplicationName("Atlas Dataset Studio")
    project_file = args.project or last_project()
    project = None
    if project_file and project_file.is_file():
        try: project = DatasetProject.open(load_project(project_file), args.read_only)
        except RuntimeError:
            project = DatasetProject.open(load_project(project_file), True)
        except Exception as exc:
            QMessageBox.warning(None, "Proyecto", f"No se pudo reabrir el último proyecto: {exc}")
    window = MainWindow(project, project_file); window.show()
    if args.smoke_test:
        from PySide6.QtCore import QTimer
        QTimer.singleShot(800, window.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
