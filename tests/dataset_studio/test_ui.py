from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QApplication

from atlas_dataset_studio.app.main_window import MainWindow
from atlas_dataset_studio.dataset import DatasetProject


def test_ui_load_navigation_filters_and_shortcuts(dataset_fixture):
    app = QApplication.instance() or QApplication([])
    project = DatasetProject.open(dataset_fixture)
    window = MainWindow(project)
    try:
        assert window.position_label.text() == "Audio 1 / 3"
        window.search_edit.setText("carrera"); app.processEvents(); assert window.sample_list.count() == 1
        window.search_edit.clear(); window.next(); assert project.current_index == 1
        shortcuts = {shortcut.key().toString() for shortcut in window.findChildren(__import__('PySide6.QtGui', fromlist=['QShortcut']).QShortcut)}
        assert {"Space", "Ctrl+Right", "Ctrl+Left", "Enter"} <= shortcuts
        assert len(window.emotion_buttons) == 15
    finally:
        window.project = None; project.close(); window.close()
