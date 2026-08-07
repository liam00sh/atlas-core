from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtCore import QTimer, Qt, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence, QShortcut
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
    QPushButton, QScrollArea, QSlider, QSpinBox, QSplitter, QTabWidget,
    QTextBrowser, QVBoxLayout, QWidget,
)

from ..config import remember_last_project, save_project, workspace_for
from ..constants import (
    CONFIDENCE, CONVERSATION_USES, EMOTIONS, EMOTION_LABELS, INTENTIONS, LEVELS,
    PERSONALITY_STRENGTH, PERSONALITY_TAGS, QUALITY, REVIEW_STATUS,
)
from ..dataset import DatasetProject
from ..exporters import export_dataset
from ..models import ProjectConfig
from ..suggestions import HeuristicSuggestionProvider
from ..validators import validate_dataset


STYLE = """
QWidget { background: #17191c; color: #f3f3f3; font-size: 13px; }
QMainWindow, QTabWidget::pane { background: #17191c; }
QLineEdit, QPlainTextEdit, QTextBrowser, QListWidget, QComboBox, QSpinBox {
  background: #23262b; border: 1px solid #454a52; border-radius: 5px; padding: 5px;
}
QPushButton { background: #30343a; border: 1px solid #555b64; border-radius: 5px; padding: 7px; }
QPushButton:hover { border-color: #f28c28; }
QPushButton:checked { background: #c85f13; border-color: #ffad55; font-weight: bold; }
QPushButton#primary { background: #e36f1e; color: white; font-weight: bold; }
QProgressBar { border: 1px solid #454a52; border-radius: 4px; text-align: center; }
QProgressBar::chunk { background: #e36f1e; }
QGroupBox { border: 1px solid #3c4148; border-radius: 6px; margin-top: 9px; padding-top: 8px; }
QGroupBox::title { color: #ff9a3d; }
QTabBar::tab:selected { color: #ff9a3d; border-bottom: 2px solid #e36f1e; }
"""


class NewProjectDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Abrir dataset")
        form = QFormLayout(self)
        self.name = QLineEdit("Daxter")
        self.metadata = QLineEdit()
        self.audio = QLineEdit()
        metadata_row = QHBoxLayout(); metadata_row.addWidget(self.metadata)
        metadata_button = QPushButton("Examinar…"); metadata_button.clicked.connect(self._pick_metadata); metadata_row.addWidget(metadata_button)
        audio_row = QHBoxLayout(); audio_row.addWidget(self.audio)
        audio_button = QPushButton("Examinar…"); audio_button.clicked.connect(self._pick_audio); audio_row.addWidget(audio_button)
        self.read_only = QCheckBox("Abrir en modo solo lectura")
        form.addRow("Dataset", self.name); form.addRow("Metadatos", metadata_row); form.addRow("Carpeta WAV", audio_row); form.addRow("", self.read_only)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); form.addRow(buttons)

    def _pick_metadata(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Metadatos", "", "Metadatos (*.csv *.jsonl)")
        if path: self.metadata.setText(path)

    def _pick_audio(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Carpeta de audios WAV")
        if path: self.audio.setText(path)

    def config(self) -> ProjectConfig:
        metadata = Path(self.metadata.text()).resolve()
        return ProjectConfig(
            name=self.name.text().strip() or metadata.stem, preset="daxter_es",
            dataset_type="voice/personality", audio_root=Path(self.audio.text()).resolve(),
            metadata_path=metadata, workspace_dir=workspace_for(metadata),
        )


class MainWindow(QMainWindow):
    def __init__(self, project: DatasetProject | None = None, project_file: Path | None = None):
        super().__init__()
        self.project = project
        self.project_file = project_file
        self.filtered_indices: list[int] = []
        self.loading = False
        self.setWindowTitle("Atlas Dataset Studio v1")
        self.resize(1600, 960)
        self.setMinimumSize(1100, 700)
        self.setStyleSheet(STYLE)
        self._build_menu(); self._build_ui(); self._build_player(); self._build_shortcuts()
        self.autosave_timer = QTimer(self); self.autosave_timer.setSingleShot(True); self.autosave_timer.setInterval(900); self.autosave_timer.timeout.connect(self.save_current)
        self._connect_autosave()
        self.external_timer = QTimer(self); self.external_timer.timeout.connect(self._check_external); self.external_timer.start(3000)
        if project:
            self._bind_project()
        else:
            QTimer.singleShot(0, self.open_dataset)

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("Dataset")
        for text, slot, shortcut in (
            ("Abrir…", self.open_dataset, "Ctrl+O"), ("Guardar", self.save_current, "Ctrl+S"),
            ("Exportar…", self.export, "Ctrl+E"), ("Cerrar dataset", self.close_dataset, "Ctrl+W"),
        ):
            action = QAction(text, self); action.triggered.connect(slot); action.setShortcut(shortcut); menu.addAction(action)
        help_action = QAction("Atajos", self); help_action.triggered.connect(self.show_shortcuts); self.menuBar().addAction(help_action)

    def _build_ui(self) -> None:
        root = QWidget(); self.setCentralWidget(root); outer = QVBoxLayout(root)
        header = QHBoxLayout()
        self.dataset_label = QLabel("Sin dataset"); self.position_label = QLabel("0 / 0")
        self.progress_label = QLabel("0 %"); self.review_progress = QProgressBar(); self.review_progress.setRange(0, 1000)
        header.addWidget(self.dataset_label); header.addStretch(); header.addWidget(self.position_label); header.addWidget(self.progress_label); header.addWidget(self.review_progress, 2)
        outer.addLayout(header)
        splitter = QSplitter(); outer.addWidget(splitter, 1)
        splitter.addWidget(self._build_sidebar()); splitter.addWidget(self._build_tabs()); splitter.setSizes([360, 1200])

    def _build_sidebar(self) -> QWidget:
        panel = QWidget(); layout = QVBoxLayout(panel)
        self.search_edit = QLineEdit(); self.search_edit.setPlaceholderText("Buscar id, archivo o texto…"); self.search_edit.textChanged.connect(self.refresh_list)
        self.game_filter = QComboBox(); self.status_filter = QComboBox(); self.emotion_filter = QComboBox(); self.personality_filter = QComboBox()
        for combo, values in ((self.game_filter, []), (self.status_filter, REVIEW_STATUS), (self.emotion_filter, EMOTIONS), (self.personality_filter, PERSONALITY_TAGS)):
            combo.addItem("Todos", ""); combo.addItems(values); combo.currentIndexChanged.connect(self.refresh_list)
        self.pending_filter = QCheckBox("Solo pendientes"); self.pending_filter.toggled.connect(self.refresh_list)
        form = QFormLayout(); form.addRow("Buscar", self.search_edit); form.addRow("Juego", self.game_filter); form.addRow("Estado", self.status_filter); form.addRow("Expresión", self.emotion_filter); form.addRow("Personalidad", self.personality_filter); form.addRow("", self.pending_filter)
        layout.addLayout(form)
        jump_row = QHBoxLayout(); self.jump_edit = QLineEdit(); self.jump_edit.setPlaceholderText("número o sample_id"); jump = QPushButton("Ir"); jump.clicked.connect(self.jump_to); jump_row.addWidget(self.jump_edit); jump_row.addWidget(jump); layout.addLayout(jump_row)
        self.sample_list = QListWidget(); self.sample_list.currentRowChanged.connect(self._select_filtered); layout.addWidget(self.sample_list, 1)
        nav = QHBoxLayout(); prev = QPushButton("← Anterior"); prev.clicked.connect(self.previous); nxt = QPushButton("Siguiente →"); nxt.clicked.connect(self.next); nav.addWidget(prev); nav.addWidget(nxt); layout.addLayout(nav)
        return panel

    def _build_tabs(self) -> QTabWidget:
        tabs = QTabWidget(); self.tabs = tabs
        tabs.addTab(self._build_review_tab(), "Revisión")
        self.stats_browser = QTextBrowser(); tabs.addTab(self.stats_browser, "Estadísticas")
        self.personality_browser = QTextBrowser(); tabs.addTab(self.personality_browser, "Personalidad")
        self.validation_browser = QTextBrowser(); validation_widget = QWidget(); vl = QVBoxLayout(validation_widget); validate_button = QPushButton("Validate dataset"); validate_button.clicked.connect(self.validate); vl.addWidget(validate_button); vl.addWidget(self.validation_browser); tabs.addTab(validation_widget, "Validación")
        self.config_browser = QTextBrowser(); tabs.addTab(self.config_browser, "Configuración")
        tabs.currentChanged.connect(lambda _: self.refresh_summaries())
        return tabs

    def _build_review_tab(self) -> QWidget:
        scroll = QScrollArea(); scroll.setWidgetResizable(True); content = QWidget(); scroll.setWidget(content); layout = QVBoxLayout(content)
        audio_box = QGroupBox("Audio"); al = QHBoxLayout(audio_box)
        self.play_button = QPushButton("▶ Reproducir"); self.pause_button = QPushButton("⏸ Pausar"); self.stop_button = QPushButton("■ Detener"); self.restart_button = QPushButton("↺ Reiniciar")
        self.audio_slider = QSlider(Qt.Horizontal); self.time_label = QLabel("00:00 / 00:00"); self.volume = QSlider(Qt.Horizontal); self.volume.setRange(0, 100); self.volume.setValue(80); self.autoplay = QCheckBox("Autoplay")
        for button in (self.play_button, self.pause_button, self.stop_button, self.restart_button): al.addWidget(button)
        al.addWidget(self.audio_slider, 1); al.addWidget(self.time_label); al.addWidget(QLabel("Vol.")); al.addWidget(self.volume); al.addWidget(self.autoplay); layout.addWidget(audio_box)
        text_box = QGroupBox("Texto"); tf = QFormLayout(text_box)
        self.verified_text = QPlainTextEdit(); self.verified_text.setReadOnly(True); self.verified_text.setMaximumHeight(85)
        self.normalized_text = QPlainTextEdit(); self.normalized_text.setMaximumHeight(85)
        copy_button = QPushButton("Copiar text → normalized_text"); copy_button.clicked.connect(lambda: self.normalized_text.setPlainText(self.verified_text.toPlainText()))
        restore_button = QPushButton("Restaurar normalized_text"); restore_button.clicked.connect(self.restore_normalized)
        br = QHBoxLayout(); br.addWidget(copy_button); br.addWidget(restore_button)
        tf.addRow("Texto verificado", self.verified_text); tf.addRow("Texto normalizado", self.normalized_text); tf.addRow("", br); layout.addWidget(text_box)
        emotion_box = QGroupBox("Expresión — revisión humana"); eg = QGridLayout(emotion_box); self.emotion_group = QButtonGroup(self); self.emotion_group.setExclusive(True); self.emotion_buttons = {}
        for i, value in enumerate(EMOTIONS):
            button = QPushButton(EMOTION_LABELS[value]); button.setCheckable(True); self.emotion_group.addButton(button); self.emotion_buttons[value] = button; eg.addWidget(button, i // 5, i % 5)
        self.confidence = QComboBox(); self.confidence.addItems(CONFIDENCE); eg.addWidget(QLabel("Confianza"), 3, 0); eg.addWidget(self.confidence, 3, 1); layout.addWidget(emotion_box)
        form_box = QGroupBox("Clasificación"); form = QFormLayout(form_box)
        self.intention = QComboBox(); self.intention.addItems(INTENTIONS)
        self.energy = QComboBox(); self.energy.addItems(LEVELS); self.intensity = QComboBox(); self.intensity.addItems(LEVELS)
        self.quality = QComboBox(); self.quality.addItems(QUALITY); self.status = QComboBox(); self.status.addItems(REVIEW_STATUS)
        self.tts_usable = QCheckBox("Candidata para TTS"); self.notes = QPlainTextEdit(); self.notes.setMaximumHeight(70)
        for label, widget in (("Intención", self.intention), ("Energía", self.energy), ("Intensidad emocional", self.intensity), ("Calidad", self.quality), ("Estado", self.status), ("", self.tts_usable), ("Notas", self.notes)): form.addRow(label, widget)
        layout.addWidget(form_box)
        personality_box = QGroupBox("Personalidad"); pg = QGridLayout(personality_box)
        self.personality_usable = QCheckBox("Útil para personalidad"); self.personality_strength = QComboBox(); self.personality_strength.addItems(PERSONALITY_STRENGTH); self.personality_reason = QLineEdit()
        pg.addWidget(self.personality_usable, 0, 0, 1, 2); pg.addWidget(QLabel("Fuerza"), 0, 2); pg.addWidget(self.personality_strength, 0, 3); pg.addWidget(QLabel("Motivo"), 1, 0); pg.addWidget(self.personality_reason, 1, 1, 1, 4)
        self.personality_checks = {}; row = 2
        for i, value in enumerate(PERSONALITY_TAGS):
            check = QCheckBox(value.replace("_", " ").capitalize()); self.personality_checks[value] = check; pg.addWidget(check, row + i // 5, i % 5)
        layout.addWidget(personality_box)
        conversation_box = QGroupBox("Utilidad conversacional"); cg = QGridLayout(conversation_box); self.conversation_checks = {}
        for i, value in enumerate(CONVERSATION_USES):
            check = QCheckBox(value.replace("_", " ").capitalize()); self.conversation_checks[value] = check; cg.addWidget(check, i // 6, i % 6)
        layout.addWidget(conversation_box)
        actions = QHBoxLayout(); suggest = QPushButton("Propuesta automática"); suggest.clicked.connect(self.show_suggestion); apply = QPushButton("Aplicar propuesta"); apply.clicked.connect(self.apply_suggestion); save = QPushButton("Guardar"); save.clicked.connect(self.save_current); accept = QPushButton("Aceptar y siguiente →"); accept.setObjectName("primary"); accept.clicked.connect(self.accept_next)
        for widget in (suggest, apply, save, accept): actions.addWidget(widget)
        layout.addLayout(actions); layout.addStretch()
        return scroll

    def _build_player(self) -> None:
        self.audio_output = QAudioOutput(self); self.audio_output.setVolume(.8)
        self.player = QMediaPlayer(self); self.player.setAudioOutput(self.audio_output)
        self.play_button.clicked.connect(self.player.play); self.pause_button.clicked.connect(self.player.pause); self.stop_button.clicked.connect(self.player.stop); self.restart_button.clicked.connect(lambda: (self.player.setPosition(0), self.player.play()))
        self.volume.valueChanged.connect(lambda value: self.audio_output.setVolume(value / 100))
        self.player.durationChanged.connect(lambda value: self.audio_slider.setRange(0, value))
        self.player.positionChanged.connect(self._position_changed); self.audio_slider.sliderMoved.connect(self.player.setPosition)
        self.player.errorOccurred.connect(lambda _, message: QMessageBox.critical(self, "Audio", f"No se puede abrir el audio: {message}"))

    def _build_shortcuts(self) -> None:
        for sequence, slot in (("Space", self.toggle_play), ("Ctrl+Right", self.next), ("Ctrl+Left", self.previous), ("Enter", self.accept_next)):
            shortcut = QShortcut(QKeySequence(sequence), self); shortcut.activated.connect(slot)
        emotion_keys = [f"Alt+{i}" for i in range(1, 10)] + ["Alt+0", "F6", "F7", "F8", "F9", "F10"]
        for value, key in zip(EMOTIONS, emotion_keys):
            shortcut = QShortcut(QKeySequence(key), self); shortcut.activated.connect(lambda v=value: self.emotion_buttons[v].setChecked(True))

    def _connect_autosave(self) -> None:
        def changed(*_: object) -> None:
            if self.project and not self.loading and not self.project.read_only:
                self.autosave_timer.start()
        self.normalized_text.textChanged.connect(changed); self.notes.textChanged.connect(changed)
        self.personality_reason.textChanged.connect(changed)
        for combo in (self.confidence, self.intention, self.energy, self.intensity, self.quality, self.status, self.personality_strength):
            combo.currentIndexChanged.connect(changed)
        for check in (self.tts_usable, self.personality_usable, *self.personality_checks.values(), *self.conversation_checks.values()):
            check.toggled.connect(changed)
        self.emotion_group.buttonToggled.connect(changed)

    def open_dataset(self) -> None:
        dialog = NewProjectDialog(self)
        if dialog.exec() != QDialog.Accepted: return
        config = dialog.config()
        if not config.metadata_path.is_file() or not config.audio_root.is_dir():
            QMessageBox.warning(self, "Dataset", "Selecciona metadatos y carpeta WAV válidos."); return
        try:
            project = DatasetProject.open(config, dialog.read_only.isChecked())
        except RuntimeError as exc:
            choice = QMessageBox.question(self, "Dataset bloqueado", f"{exc}\n¿Abrir en modo solo lectura?")
            if choice != QMessageBox.Yes: return
            project = DatasetProject.open(config, True)
        except Exception as exc:
            QMessageBox.critical(self, "Dataset", str(exc)); return
        self.close_dataset(); self.project = project
        config.workspace_dir.mkdir(parents=True, exist_ok=True); self.project_file = config.workspace_dir / "project.json"; save_project(self.project_file, config); remember_last_project(self.project_file); self._bind_project()

    def close_dataset(self) -> None:
        if self.project:
            try: self.project.close()
            except Exception as exc: QMessageBox.critical(self, "Guardado", str(exc))
        self.project = None; self.sample_list.clear(); self.dataset_label.setText("Sin dataset")

    def _bind_project(self) -> None:
        assert self.project
        self.game_filter.clear(); self.game_filter.addItem("Todos", ""); self.game_filter.addItems(sorted({s.source_game for s in self.project.samples}))
        self.dataset_label.setText(f"Dataset {self.project.config.name}" + (" · SOLO LECTURA" if self.project.read_only else ""))
        self.refresh_list(); self.load_current(); self.refresh_summaries()

    def refresh_list(self) -> None:
        if not self.project: return
        self.filtered_indices = self.project.search(
            self.search_edit.text(),
            source_game=self.game_filter.currentText() if self.game_filter.currentIndex() > 0 else "",
            review_status=self.status_filter.currentText() if self.status_filter.currentIndex() > 0 else "",
            emotion=self.emotion_filter.currentText() if self.emotion_filter.currentIndex() > 0 else "",
            personality=self.personality_filter.currentText() if self.personality_filter.currentIndex() > 0 else "",
            pending_only=self.pending_filter.isChecked(),
        )
        self.sample_list.blockSignals(True); self.sample_list.clear()
        for index in self.filtered_indices:
            sample = self.project.samples[index]; self.sample_list.addItem(f"{index + 1:04d}  {sample.sample_id}  [{sample.review_status}]")
        if self.project.current_index in self.filtered_indices:
            self.sample_list.setCurrentRow(self.filtered_indices.index(self.project.current_index))
        self.sample_list.blockSignals(False)

    def _select_filtered(self, row: int) -> None:
        if self.project and 0 <= row < len(self.filtered_indices): self.project.navigate(self.filtered_indices[row]); self.load_current()

    def load_current(self) -> None:
        if not self.project or not self.project.samples: return
        self.loading = True; sample = self.project.current
        self.position_label.setText(f"Audio {self.project.current_index + 1} / {len(self.project.samples)}")
        self.verified_text.setPlainText(sample.text); self.normalized_text.setPlainText(sample.normalized_text)
        self.emotion_buttons.get(sample.emotion, self.emotion_buttons["neutral"]).setChecked(True)
        for combo, value in ((self.confidence, sample.emotion_confidence), (self.intention, sample.intention), (self.energy, sample.energy), (self.intensity, sample.emotion_intensity), (self.quality, sample.quality), (self.status, sample.review_status), (self.personality_strength, sample.personality_strength)):
            combo.setCurrentText(value)
        self.tts_usable.setChecked(sample.tts_usable); self.notes.setPlainText(sample.review_notes); self.personality_usable.setChecked(sample.personality_usable); self.personality_reason.setText(sample.personality_reason)
        for key, check in self.personality_checks.items(): check.setChecked(key in sample.personality_tags)
        for key, check in self.conversation_checks.items(): check.setChecked(key in sample.conversation_use)
        audio = self.project.config.audio_root / sample.relative_path
        if audio.is_file(): self.player.setSource(QUrl.fromLocalFile(str(audio))); self.play_button.setEnabled(True)
        else: self.player.setSource(QUrl()); self.play_button.setEnabled(False); self.statusBar().showMessage(f"Audio ausente: {sample.relative_path}")
        self.loading = False; self._update_progress()
        if self.autoplay.isChecked() and audio.is_file(): self.player.play()

    def save_current(self) -> None:
        if not self.project or self.loading: return
        emotion = next((key for key, button in self.emotion_buttons.items() if button.isChecked()), "neutral")
        try:
            self.project.update_current(
                normalized_text=self.normalized_text.toPlainText(), emotion=emotion,
                emotion_confidence=self.confidence.currentText(), intention=self.intention.currentText(),
                energy=self.energy.currentText(), emotion_intensity=self.intensity.currentText(),
                quality=self.quality.currentText(), review_status=self.status.currentText(),
                tts_usable=self.tts_usable.isChecked(), review_notes=self.notes.toPlainText(),
                personality_usable=self.personality_usable.isChecked(), personality_strength=self.personality_strength.currentText(),
                personality_reason=self.personality_reason.text(),
                personality_tags=[key for key, check in self.personality_checks.items() if check.isChecked()],
                conversation_use=[key for key, check in self.conversation_checks.items() if check.isChecked()],
            )
            self.statusBar().showMessage("Guardado atómico completado", 3000); self.refresh_list(); self.refresh_summaries()
        except Exception as exc: QMessageBox.critical(self, "No se ha guardado", str(exc))

    def accept_next(self) -> None:
        self.status.setCurrentText("accepted_with_notes" if self.notes.toPlainText().strip() else "accepted"); self.save_current(); self.next()

    def restore_normalized(self) -> None:
        if self.project: self.normalized_text.setPlainText(self.project.current.original_normalized_text)

    def previous(self) -> None:
        if self.project: self.project.navigate(self.project.current_index - 1); self.load_current(); self.refresh_list()

    def next(self) -> None:
        if self.project: self.project.navigate(self.project.current_index + 1); self.load_current(); self.refresh_list()

    def jump_to(self) -> None:
        if not self.project: return
        try: self.project.navigate(self.project.find_index(self.jump_edit.text().strip())); self.load_current(); self.refresh_list()
        except (KeyError, ValueError): QMessageBox.information(self, "Navegación", "Muestra no encontrada")

    def toggle_play(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlayingState: self.player.pause()
        else: self.player.play()

    def _position_changed(self, value: int) -> None:
        if not self.audio_slider.isSliderDown(): self.audio_slider.setValue(value)
        self.time_label.setText(f"{self._time(value)} / {self._time(self.player.duration())}")

    @staticmethod
    def _time(ms: int) -> str: return f"{ms // 60000:02d}:{(ms // 1000) % 60:02d}"

    def show_suggestion(self) -> None:
        if self.project:
            suggestion = HeuristicSuggestionProvider().suggest(self.project.current)
            QMessageBox.information(self, "Propuesta automática", json.dumps({"emotion": suggestion.emotion, "intention": suggestion.intention, "energy": suggestion.energy, "personality_tags": suggestion.personality_tags, "conversation_use": suggestion.conversation_use}, ensure_ascii=False, indent=2))

    def apply_suggestion(self) -> None:
        if not self.project: return
        suggestion = HeuristicSuggestionProvider().suggest(self.project.current)
        self.emotion_buttons[suggestion.emotion].setChecked(True); self.intention.setCurrentText(suggestion.intention); self.energy.setCurrentText(suggestion.energy)
        for key, check in self.personality_checks.items(): check.setChecked(key in suggestion.personality_tags)
        for key, check in self.conversation_checks.items(): check.setChecked(key in suggestion.conversation_use)
        self.statusBar().showMessage("Propuesta aplicada al formulario; confirma con Guardar", 5000)

    def validate(self) -> None:
        if not self.project: return
        result = validate_dataset(self.project.config, self.project.samples, full_hash=True)
        self.validation_browser.setPlainText(f"{result.status}\nArchivos comprobados: {result.checked_files}\nDuración: {result.total_duration:.3f} s\n\nERRORES\n" + "\n".join(result.errors or ["Ninguno"]) + "\n\nADVERTENCIAS\n" + "\n".join(result.warnings or ["Ninguna"]))

    def export(self) -> None:
        if not self.project: return
        directory = QFileDialog.getExistingDirectory(self, "Carpeta de exportación")
        if not directory: return
        result = export_dataset(self.project.config, self.project.samples, Path(directory), full_hash=True)
        QMessageBox.information(self, "Exportación", f"Exportación completada. Resultado: {result.status}")

    def refresh_summaries(self) -> None:
        if not self.project: return
        stats = self.project.statistics()
        self.stats_browser.setPlainText(json.dumps(stats, ensure_ascii=False, indent=2, default=dict))
        iconic = [s for s in self.project.samples if s.personality_strength == "iconica"]
        self.personality_browser.setPlainText("Frases icónicas\n\n" + "\n".join(f"{s.sample_id}: {s.text}" for s in iconic) if iconic else "Aún no hay frases marcadas como icónicas.")
        cfg = self.project.config
        self.config_browser.setPlainText(f"Preset: {cfg.preset}\nTipo: {cfg.dataset_type}\nAudio: {cfg.audio_root}\nMetadatos: {cfg.metadata_path}\nWorkspace local: {cfg.workspace_dir}\nBackups: {cfg.backup_count}\nModo: {'solo lectura' if self.project.read_only else 'lectura/escritura'}")
        self._update_progress()

    def _update_progress(self) -> None:
        if not self.project: return
        stats = self.project.statistics(); value = int(stats["completion_percent"] * 10); self.review_progress.setValue(value); self.progress_label.setText(f"{stats['completion_percent']:.1f} % · {stats['reviewed']} / {stats['total']} · sesión {stats['reviewed_this_session']}")

    def _check_external(self) -> None:
        if self.project and self.project.external_changes_detected(): self.statusBar().showMessage("Cambios externos detectados: guardado bloqueado", 5000)

    def show_shortcuts(self) -> None:
        keys = ["Space — reproducir/pausar", "Ctrl+Right — siguiente", "Ctrl+Left — anterior", "Ctrl+S — guardar", "Enter — aceptar y siguiente", "", "Expresiones: Alt+1…Alt+0 y F6…F10 en el orden del preset daxter_es"]
        QMessageBox.information(self, "Atajos", "\n".join(keys))

    def closeEvent(self, event: QCloseEvent) -> None:
        try:
            if self.project: self.project.close(); self.project = None
            event.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Cierre", str(exc)); event.ignore()
