# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QSize, QThread, QTimer, Signal, Slot
from PySide6.QtMultimedia import QAudioSource, QMediaDevices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from graphis.app.gui.resources import icon as resource_icon
from graphis.app.ki.model_paths import speech_model_dir
from graphis.app.ki.speech import (
    DEFAULT_SPEECH_MODEL,
    SPEECH_LANGUAGE_CHOICES,
    LiveTranscriber,
    SpeechRecognizer,
    available_speech_models,
)
from graphis.interface.io_audio import pcm16_audio_level, pcm16_bytes_to_float32, whisper_pcm16_format

logger = logging.getLogger(__name__)

LIVE_STEP_INTERVAL_MS = 700


class SpeechWorker(QObject):
    """Owns the speech model in a background thread, so it is loaded once and reused."""

    modelReady = Signal(str)
    modelFailed = Signal(str)
    update = Signal(str, str, bool)
    failed = Signal(str, bool)

    def __init__(self, recognizer=None):
        super().__init__()
        self._recognizer = recognizer or SpeechRecognizer()
        self._session = None

    @Slot(str)
    def load_model(self, model_name):
        try:
            self._recognizer.load(model_name)
        except Exception as err:
            logger.warning("Speech model could not be loaded: %s", err)
            self.modelFailed.emit(str(err))
        else:
            self.modelReady.emit(model_name)

    @Slot(str, str)
    def start_session(self, model_name, language):
        self._session = None
        try:
            self._recognizer.load(model_name)
        except Exception as err:
            self.modelFailed.emit(str(err))
            return
        self.modelReady.emit(model_name)
        self._session = LiveTranscriber(self._recognizer, language)

    @Slot(object)
    def append_audio(self, data):
        if self._session is not None:
            self._session.append(pcm16_bytes_to_float32(data))

    @Slot(bool)
    def step(self, final):
        if self._session is None:
            self.failed.emit("No speech model is loaded.", final)
            return
        try:
            result = self._session.step(final)
        except Exception as err:
            logger.exception("Speech transcription failed")
            self.failed.emit(str(err), final)
        else:
            self.update.emit(result.committed, result.partial, final)
        if final:
            self._session = None


class SpeechTranscriptionPopup(QDialog):
    _loadRequested = Signal(str)
    _sessionRequested = Signal(str, str)
    _audioCaptured = Signal(object)
    _stepRequested = Signal(bool)
    downloadRequested = Signal()

    def __init__(self, parent=None, model_name=DEFAULT_SPEECH_MODEL, worker=None):
        super().__init__(parent)
        self.model_name = model_name
        self._audio_source = None
        self._audio_io = None
        self._recorded_any = False
        self._finishing = False
        self._step_pending = False
        self._loaded_model = None

        self._build_ui()

        self._thread = QThread(self)
        self._thread.setObjectName("GraphisSpeech")
        self._worker = worker or SpeechWorker()
        self._worker.moveToThread(self._thread)
        self._loadRequested.connect(self._worker.load_model)
        self._sessionRequested.connect(self._worker.start_session)
        self._audioCaptured.connect(self._worker.append_audio)
        self._stepRequested.connect(self._worker.step)
        self._worker.modelReady.connect(self._model_ready)
        self._worker.modelFailed.connect(self._model_failed)
        self._worker.update.connect(self._transcription_update)
        self._worker.failed.connect(self._transcription_failed)
        self._thread.start()
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)

        self._step_timer = QTimer(self)
        self._step_timer.setInterval(LIVE_STEP_INTERVAL_MS)
        self._step_timer.timeout.connect(self._request_live_step)

    def _build_ui(self):
        self.setWindowTitle("Speech transcription")
        self.setMinimumSize(520, 340)
        self.setStyleSheet("""
            QDialog {
                background-color: rgb(40, 44, 52);
                color: rgb(220, 220, 220);
            }
            QPlainTextEdit {
                background-color: rgb(27, 29, 35);
                color: rgb(230, 230, 230);
                border: 1px solid rgb(80, 88, 102);
                border-radius: 4px;
                padding: 6px;
                font: 10pt "Segoe UI";
            }
            QPushButton {
                background-color: rgb(52, 59, 72);
                border: 1px solid rgb(70, 78, 92);
                border-radius: 4px;
                padding: 5px 10px;
                color: rgb(230, 230, 230);
            }
            QPushButton:hover {
                background-color: rgb(65, 74, 90);
            }
            QPushButton:checked {
                background-color: rgb(117, 49, 49);
                border: 1px solid rgb(161, 72, 72);
            }
            QProgressBar {
                border: 1px solid rgb(80, 88, 102);
                border-radius: 3px;
                background-color: rgb(27, 29, 35);
                height: 12px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: rgb(65, 180, 130);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model", self))
        self.model_combo = QComboBox(self)
        self.model_combo.setEditable(True)
        self.model_combo.setToolTip(
            "faster-whisper models found in the speech model folder (AI configuration). They run on CPU; "
            "larger models are more accurate but slower."
        )
        self.model_combo.activated.connect(lambda _index: self._preload_model())
        self.model_combo.lineEdit().editingFinished.connect(self._preload_model)
        model_layout.addWidget(self.model_combo, 1)
        self.browse_model_button = QPushButton("Browse...", self)
        self.browse_model_button.clicked.connect(self.browse_model)
        model_layout.addWidget(self.browse_model_button)
        self.download_model_button = QPushButton("Download...", self)
        self.download_model_button.setToolTip("Download speech models")
        self.download_model_button.clicked.connect(lambda: self.downloadRequested.emit())
        model_layout.addWidget(self.download_model_button)
        layout.addLayout(model_layout)

        options_layout = QHBoxLayout()
        options_layout.addWidget(QLabel("Language", self))
        self.language_combo = QComboBox(self)
        self.language_combo.setEditable(True)
        self.language_combo.addItems(SPEECH_LANGUAGE_CHOICES)
        self.language_combo.setToolTip("Spoken language code. Auto detects it from the first sentence.")
        options_layout.addWidget(self.language_combo, 1)
        self.live_checkbox = QCheckBox("Live", self)
        self.live_checkbox.setChecked(True)
        self.live_checkbox.setToolTip("Show text while speaking. Each sentence is finalised at a pause.")
        options_layout.addWidget(self.live_checkbox)
        layout.addLayout(options_layout)

        top_layout = QHBoxLayout()
        self.status_label = QLabel("Ready", self)
        self.status_label.setWordWrap(True)
        top_layout.addWidget(self.status_label, 1)

        self.mic_button = QPushButton(self)
        self.mic_button.setCheckable(True)
        self.mic_button.setIcon(resource_icon("microphone.svg"))
        self.mic_button.setIconSize(QSize(22, 22))
        self.mic_button.setFixedSize(36, 32)
        self.mic_button.setToolTip("Start or stop recording")
        self.mic_button.clicked.connect(self.toggle_recording)
        top_layout.addWidget(self.mic_button)

        self.clear_button = QPushButton("Clear", self)
        self.clear_button.clicked.connect(self._clear_text)
        top_layout.addWidget(self.clear_button)

        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.close)
        top_layout.addWidget(self.close_button)
        layout.addLayout(top_layout)

        self.level_bar = QProgressBar(self)
        self.level_bar.setRange(0, 100)
        self.level_bar.setValue(0)
        layout.addWidget(self.level_bar)

        self.transcription_text = QPlainTextEdit(self)
        self.transcription_text.setPlaceholderText("Transcribed text will appear here.")
        layout.addWidget(self.transcription_text, 1)

        self.partial_label = QLabel("", self)
        self.partial_label.setWordWrap(True)
        self.partial_label.setStyleSheet("color: rgb(150, 156, 168); font-style: italic;")
        layout.addWidget(self.partial_label)
        self.refresh_models()

    # ------------------------------------------------------------------ model

    def showEvent(self, event):
        super().showEvent(event)
        self._preload_model()

    def refresh_models(self):
        """Fill the model list from the speech model folder, e.g. after the AI configuration changed."""
        current = self.model_combo.currentText().strip() or self.model_name
        models = available_speech_models()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self.model_combo.addItems(models)
        if current in models or (current and Path(current).is_absolute()):
            self.model_combo.setCurrentText(current)
        elif models:
            self.model_combo.setCurrentText(DEFAULT_SPEECH_MODEL if DEFAULT_SPEECH_MODEL in models else models[0])
        else:
            self.model_combo.setCurrentText("")
        self.model_combo.blockSignals(False)
        self._loaded_model = None
        if not models and not self._current_model_text():
            self._set_status("No speech models found. Click Download... to get one.")
        if self.isVisible():
            self._preload_model()

    def select_model(self, model_name):
        if self._audio_source is not None or self._finishing:
            return
        self.model_combo.setCurrentText(model_name)
        if self.isVisible():
            self._preload_model()

    def _current_model_text(self):
        return self.model_combo.currentText().strip()

    def _current_model(self):
        return self.model_combo.currentText().strip() or DEFAULT_SPEECH_MODEL

    @Slot()
    def _preload_model(self):
        if not self._current_model_text():
            self._set_status("No speech models found. Click Download... to get one.")
            return
        model_name = self._current_model()
        if model_name == self._loaded_model:
            return
        self._set_status(f"Loading speech model '{model_name}'...")
        self._loadRequested.emit(model_name)

    @Slot(str)
    def _model_ready(self, model_name):
        self._loaded_model = model_name
        self.model_name = model_name
        if self._audio_source is None and not self._finishing:
            self._set_status(f"Model '{model_name}' ready.")

    @Slot(str)
    def _model_failed(self, message):
        self._loaded_model = None
        self._set_status(f"Speech model failed: {message}")
        if self._audio_source is not None:
            self.stop_recording(transcribe=False)

    @Slot()
    def browse_model(self):
        folder = speech_model_dir()
        model_path = QFileDialog.getExistingDirectory(
            self, "Select faster-whisper model folder", "" if folder is None else str(folder)
        )
        if model_path:
            self.model_combo.setCurrentText(model_path)
            self._preload_model()

    # -------------------------------------------------------------- recording

    @Slot()
    def toggle_recording(self):
        if self._finishing:
            self.mic_button.setChecked(False)
            return
        if self._audio_source is None:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        if not self._current_model_text():
            self._set_status("No speech models found. Click Download... to get one.")
            self.mic_button.setChecked(False)
            return
        device = QMediaDevices.defaultAudioInput()
        if device.isNull():
            self._set_status("No microphone input is available.")
            self.mic_button.setChecked(False)
            return

        audio_format = self._recording_format(device)
        if audio_format is None:
            self._set_status("Microphone does not support 16-bit mono 16 kHz recording.")
            self.mic_button.setChecked(False)
            return

        self.level_bar.setValue(0)
        self._audio_source = QAudioSource(device, audio_format, self)
        self._audio_io = self._audio_source.start()
        if self._audio_io is None:
            self._audio_source.deleteLater()
            self._audio_source = None
            self._set_status("Could not start microphone input.")
            self.mic_button.setChecked(False)
            return
        self._recorded_any = False
        self._step_pending = False
        self.partial_label.clear()
        self._sessionRequested.emit(self._current_model(), self.language_combo.currentText())
        self._audio_io.readyRead.connect(self._read_audio)
        if self.live_checkbox.isChecked():
            self._step_timer.start()
        self._set_status("Recording... speak now.")
        self.mic_button.setChecked(True)

    def stop_recording(self, transcribe=True):
        if self._audio_source is None:
            return
        self._step_timer.stop()
        self._read_audio()
        self._audio_source.stop()
        self._audio_source.deleteLater()
        self._audio_source = None
        self._audio_io = None
        self.mic_button.setChecked(False)
        self.level_bar.setValue(0)

        if not transcribe:
            return
        if not self._recorded_any:
            self._set_status("No audio was recorded.")
            return
        self._finishing = True
        self.mic_button.setEnabled(False)
        self._set_status("Finishing transcription...")
        self._stepRequested.emit(True)

    def closeEvent(self, event):
        if self._audio_source is not None:
            self.stop_recording()
        super().closeEvent(event)

    @Slot()
    def shutdown(self):
        self._step_timer.stop()
        if self._thread.isRunning():
            self._thread.quit()
            self._thread.wait()

    def _recording_format(self, device):
        return whisper_pcm16_format(device)

    @Slot()
    def _read_audio(self):
        if self._audio_io is None:
            return
        data = bytes(self._audio_io.readAll())
        if not data:
            return
        self._recorded_any = True
        self._audioCaptured.emit(data)
        self.level_bar.setValue(pcm16_audio_level(data))

    @Slot()
    def _request_live_step(self):
        if self._step_pending or not self._recorded_any:
            return
        self._step_pending = True
        self._stepRequested.emit(False)

    # ---------------------------------------------------------- transcription

    @Slot(str, str, bool)
    def _transcription_update(self, committed, partial, final):
        if committed:
            self._append_text(committed)
        self.partial_label.setText(partial)
        if final:
            self._finish_session("Transcription finished.")
        else:
            self._step_pending = False

    @Slot(str, bool)
    def _transcription_failed(self, message, final):
        self._set_status(f"Transcription failed: {message}")
        if final:
            self._finish_session(None)
        else:
            self._step_pending = False

    def _finish_session(self, message):
        self._finishing = False
        self._step_pending = False
        self.partial_label.clear()
        self.mic_button.setEnabled(True)
        if message:
            self._set_status(message)

    def _append_text(self, text):
        cursor = self.transcription_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        existing = self.transcription_text.toPlainText()
        if existing and not existing[-1].isspace():
            text = " " + text
        cursor.insertText(text)
        self.transcription_text.setTextCursor(cursor)
        self.transcription_text.ensureCursorVisible()

    @Slot()
    def _clear_text(self):
        self.transcription_text.clear()
        self.partial_label.clear()

    def _set_status(self, text):
        self.status_label.setText(text)

