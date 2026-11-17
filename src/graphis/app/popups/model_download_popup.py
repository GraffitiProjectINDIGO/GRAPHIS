# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import logging
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from graphis.app.ki.model_download import (
    SEGMENTATION_MODEL_CATALOG,
    SPEECH_MODEL_CATALOG,
    DownloadCancelled,
    download_segmentation_model,
    download_speech_model,
    is_downloaded,
    is_segmentation_model_downloaded,
    segmentation_model_info,
    speech_model_info,
)

logger = logging.getLogger(__name__)


class _DownloadSignals(QObject):
    progress = Signal(object, object)
    finished = Signal(str, str)
    failed = Signal(str)
    cancelled = Signal()


class _DownloadTask(QRunnable):
    def __init__(self, download, info, folder):
        super().__init__()
        self.download = download
        self.info = info
        self.folder = Path(folder)
        self.cancel_event = threading.Event()
        self.signals = _DownloadSignals()

    @Slot()
    def run(self):
        try:
            self.download(
                self.info, self.folder, lambda done, total: self.signals.progress.emit(done, total),
                self.cancel_event.is_set,
            )
        except DownloadCancelled:
            self.signals.cancelled.emit()
        except Exception as err:
            logger.warning("Model download failed: %s", err)
            self.signals.failed.emit(str(err))
        else:
            self.signals.finished.emit(str(self.folder), self.info.name)


class ModelDownloadPopup(QDialog):
    """Download models into one folder, which then becomes the model folder of that kind."""

    modelDownloaded = Signal(str, str)

    window_title = "Download models"
    folder_text = "Download folder."
    source_text = ""
    default_model = ""
    catalog = ()

    def model_info(self, name):
        raise NotImplementedError

    def is_model_downloaded(self, folder, name):
        raise NotImplementedError

    def download_model(self, info, folder, progress, cancelled):
        raise NotImplementedError

    def target_path(self, folder, info):
        raise NotImplementedError

    def finished_text(self, name):
        return f"Model '{name}' downloaded."

    def __init__(self, parent=None, default_folder=""):
        super().__init__(parent)
        self._task = None
        self.setWindowTitle(self.window_title)
        self.setMinimumSize(560, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: rgb(40, 44, 52);
                color: rgb(220, 220, 220);
            }
            QLabel {
                color: rgb(220, 220, 220);
            }
            QLineEdit, QListWidget {
                background-color: rgb(27, 29, 35);
                color: rgb(230, 230, 230);
                border: 1px solid rgb(80, 88, 102);
                border-radius: 4px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: rgb(58, 105, 118);
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
            QPushButton:disabled {
                color: rgb(130, 130, 130);
            }
            QProgressBar {
                border: 1px solid rgb(80, 88, 102);
                border-radius: 3px;
                background-color: rgb(27, 29, 35);
                text-align: center;
                color: rgb(230, 230, 230);
            }
            QProgressBar::chunk {
                background-color: rgb(65, 180, 130);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        layout.addWidget(QLabel(self.folder_text, self))
        folder_layout = QHBoxLayout()
        self.folder_edit = QLineEdit(default_folder, self)
        self.folder_edit.textChanged.connect(self._refresh_list)
        folder_layout.addWidget(self.folder_edit, 1)
        self.browse_button = QPushButton("Browse...", self)
        self.browse_button.clicked.connect(self._browse)
        folder_layout.addWidget(self.browse_button)
        layout.addLayout(folder_layout)

        self.model_list = QListWidget(self)
        for info in self.catalog:
            item = QListWidgetItem(self.model_list)
            item.setData(Qt.ItemDataRole.UserRole, info.name)
        self.model_list.currentItemChanged.connect(lambda *_: self._sync_buttons())
        layout.addWidget(self.model_list, 1)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel(self.source_text, self)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        self.download_button = QPushButton("Download", self)
        self.download_button.clicked.connect(self.start_download)
        self.cancel_button = QPushButton("Cancel download", self)
        self.cancel_button.clicked.connect(self.cancel_download)
        self.close_button = QPushButton("Close", self)
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.download_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.cancel_download)
        self._refresh_list()
        self._select(self.default_model)

    def set_folder(self, folder):
        if folder and not self.is_downloading:
            self.folder_edit.setText(folder)

    @property
    def is_downloading(self):
        return self._task is not None

    def _folder(self):
        text = self.folder_edit.text().strip()
        return Path(text).expanduser() if text else None

    def _select(self, name):
        for row in range(self.model_list.count()):
            if self.model_list.item(row).data(Qt.ItemDataRole.UserRole) == name:
                self.model_list.setCurrentRow(row)
                return

    def _selected_info(self):
        item = self.model_list.currentItem()
        return None if item is None else self.model_info(item.data(Qt.ItemDataRole.UserRole))

    @Slot()
    def _refresh_list(self):
        folder = self._folder()
        for row in range(self.model_list.count()):
            item = self.model_list.item(row)
            info = self.model_info(item.data(Qt.ItemDataRole.UserRole))
            size = f"{info.size_mb / 1000:.1f} GB" if info.size_mb >= 1000 else f"{info.size_mb} MB"
            state = "  [downloaded]" if self.is_model_downloaded(folder, info.name) else ""
            item.setText(f"{info.name}  ({size}){state}\n{info.description}")
        self._sync_buttons()

    def _sync_buttons(self):
        info = self._selected_info()
        downloading = self.is_downloading
        self.download_button.setEnabled(
            not downloading and info is not None and self._folder() is not None
            and not self.is_model_downloaded(self._folder(), info.name)
        )
        self.cancel_button.setEnabled(downloading)
        self.folder_edit.setEnabled(not downloading)
        self.browse_button.setEnabled(not downloading)

    @Slot()
    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select download folder", self.folder_edit.text().strip())
        if folder:
            self.folder_edit.setText(folder)

    @Slot()
    def start_download(self):
        info = self._selected_info()
        folder = self._folder()
        if info is None or folder is None or self.is_downloading:
            return
        self._task = _DownloadTask(self.download_model, info, folder)
        self._task.setAutoDelete(False)
        self._task.signals.progress.connect(self._progress)
        self._task.signals.finished.connect(self._finished)
        self._task.signals.failed.connect(self._failed)
        self._task.signals.cancelled.connect(self._cancelled)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Downloading {info.name} to {self.target_path(folder, info)} ...")
        self._sync_buttons()
        QThreadPool.globalInstance().start(self._task)

    @Slot()
    def cancel_download(self):
        if self._task is not None:
            self._task.cancel_event.set()
            self.status_label.setText("Cancelling download...")

    @Slot(object, object)
    def _progress(self, done, total):
        if total:
            self.progress_bar.setValue(int(done * 100 / total))
            self.status_label.setText(f"Downloading {self._task.info.name}: {done / 1e6:.0f} of {total / 1e6:.0f} MB")

    @Slot(str, str)
    def _finished(self, folder, name):
        self._task = None
        self.progress_bar.setValue(100)
        self.status_label.setText(self.finished_text(name))
        self._refresh_list()
        self.modelDownloaded.emit(folder, name)

    @Slot(str)
    def _failed(self, message):
        self._task = None
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Download failed: {message}")
        self._sync_buttons()

    @Slot()
    def _cancelled(self):
        self._task = None
        self.progress_bar.setValue(0)
        self.status_label.setText("Download cancelled.")
        self._sync_buttons()

    def closeEvent(self, event):
        self.cancel_download()
        super().closeEvent(event)


class SpeechModelDownloadPopup(ModelDownloadPopup):
    """Speech models are saved in subfolders of one folder, which becomes the speech model folder."""

    window_title = "Download speech models"
    folder_text = "Download folder. Each model is saved in its own subfolder."
    source_text = "Models are downloaded from Hugging Face (MIT license)."
    default_model = "small"
    catalog = SPEECH_MODEL_CATALOG

    def model_info(self, name):
        return speech_model_info(name)

    def is_model_downloaded(self, folder, name):
        return is_downloaded(folder, name)

    def download_model(self, info, folder, progress, cancelled):
        return download_speech_model(info, folder, progress, cancelled)

    def target_path(self, folder, info):
        return folder / info.name

    def finished_text(self, name):
        return f"Model '{name}' downloaded. It is now available in the speech window."


class SegmentationModelDownloadPopup(ModelDownloadPopup):
    """MobileSAM and SAM2 files are saved directly in the folder, which becomes the segmentation model folder."""

    window_title = "Download segmentation models"
    folder_text = "Download folder. Model files are saved directly in this folder."
    source_text = (
        "Models are downloaded from the Ultralytics GitHub releases. "
        "SAM3 and TextureSAM must be downloaded manually: see README, section AI models."
    )
    default_model = "MobileSAM"
    catalog = SEGMENTATION_MODEL_CATALOG

    def model_info(self, name):
        return segmentation_model_info(name)

    def is_model_downloaded(self, folder, name):
        return is_segmentation_model_downloaded(folder, name)

    def download_model(self, info, folder, progress, cancelled):
        return download_segmentation_model(info, folder, progress, cancelled)

    def target_path(self, folder, info):
        return folder / info.filename

    def finished_text(self, name):
        return f"Model '{name}' downloaded. Select it in the AI toolbox of the image view."
