# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from PySide6.QtCore import QEvent, QPoint, QTimer, Signal, Slot
from PySide6.QtWidgets import QFileDialog, QFrame, QGridLayout, QLabel, QLineEdit, QPushButton

SEGMENTATION_MODEL_LABELS = {
    "ultralytics_sam3": "SAM3",
    "ultralytics_sam2": "SAM2",
    "ultralytics_mobile_sam": "MobileSAM",
    "texturesam": "TextureSAM",
}


def segmentation_status_text(found):
    available = [label for key, label in SEGMENTATION_MODEL_LABELS.items() if found.get(key)]
    missing = [label for key, label in SEGMENTATION_MODEL_LABELS.items() if not found.get(key)]
    if not available:
        return "No segmentation models found."
    text = "Found: " + ", ".join(available)
    if missing:
        text += ". Missing: " + ", ".join(missing)
    return text + "."


def speech_status_text(models):
    return "Found: " + ", ".join(models) + "." if models else "No speech models found."


class AIConfigPopup(QFrame):
    """Select the folders that contain user-downloaded segmentation and speech models."""

    settingsSaveRequested = Signal(str, str)
    speechDownloadRequested = Signal()
    segmentationDownloadRequested = Signal()

    def __init__(self, parent, anchor_button):
        super().__init__(parent)
        self.anchor_button = anchor_button
        self._open = False

        self.setObjectName("aiConfigPopup")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedSize(560, 215)
        self.setStyleSheet("""
            QFrame#aiConfigPopup {
                background-color: rgb(48, 54, 65);
                border: 1px solid rgb(90, 98, 112);
                border-radius: 6px;
            }
            QLabel {
                color: rgb(220, 220, 220);
                font: 10pt "Segoe UI";
            }
            QLabel#aiConfigStatus {
                color: rgb(170, 178, 190);
                font: 9pt "Segoe UI";
            }
            QLineEdit {
                background-color: rgb(52, 70, 72);
                color: rgb(230, 230, 230);
                border: 1px solid rgb(95, 112, 116);
                border-radius: 3px;
                padding: 4px;
                font: 10pt "Segoe UI";
            }
            QPushButton {
                background-color: rgb(150, 150, 150);
                border: 1px solid rgb(70, 78, 92);
                border-radius: 4px;
                padding: 5px 10px;
                color: rgb(25, 25, 25);
                font: 9pt "Segoe UI";
            }
            QPushButton:hover {
                background-color: rgb(180, 180, 180);
            }
        """)

        layout = QGridLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(6)

        self.segmentation_edit = QLineEdit(self)
        self.segmentation_edit.setPlaceholderText("Folder with mobile_sam.pt, sam2.1_l.pt, sam3.pt ...")
        self.segmentation_browse_button = QPushButton("Browse...", self)
        self.segmentation_status = self._status_label()
        self.segmentation_download_button = QPushButton("Download...", self)
        self.segmentation_download_button.setToolTip("Download MobileSAM and SAM2 into a folder of your choice")

        self.speech_edit = QLineEdit(self)
        self.speech_edit.setPlaceholderText("Folder with faster-whisper model folders, e.g. base, small")
        self.speech_browse_button = QPushButton("Browse...", self)
        self.speech_status = self._status_label()
        self.speech_download_button = QPushButton("Download...", self)
        self.speech_download_button.setToolTip("Download speech models into a folder of your choice")

        self.save_button = QPushButton("Save", self)
        self.result_label = QLabel("SAM3 and TextureSAM: see README, section AI models.", self)
        self.result_label.setWordWrap(True)

        layout.addWidget(QLabel("Segmentation", self), 0, 0)
        layout.addWidget(self.segmentation_edit, 0, 1)
        layout.addWidget(self.segmentation_browse_button, 0, 2)
        layout.addWidget(self.segmentation_status, 1, 1)
        layout.addWidget(self.segmentation_download_button, 1, 2)
        layout.addWidget(QLabel("Speech", self), 2, 0)
        layout.addWidget(self.speech_edit, 2, 1)
        layout.addWidget(self.speech_browse_button, 2, 2)
        layout.addWidget(self.speech_status, 3, 1)
        layout.addWidget(self.speech_download_button, 3, 2)
        layout.addWidget(self.result_label, 4, 0, 1, 2)
        layout.addWidget(self.save_button, 4, 2)
        layout.setRowStretch(5, 1)

        self.anchor_button.setCheckable(True)
        self._set_anchor_checked(False)

        self.segmentation_browse_button.clicked.connect(lambda: self._browse(self.segmentation_edit, "segmentation"))
        self.speech_browse_button.clicked.connect(lambda: self._browse(self.speech_edit, "speech"))
        self.save_button.clicked.connect(self._save)
        self.speech_download_button.clicked.connect(lambda: self.speechDownloadRequested.emit())
        self.segmentation_download_button.clicked.connect(lambda: self.segmentationDownloadRequested.emit())
        self.segmentation_edit.returnPressed.connect(self._save)
        self.speech_edit.returnPressed.connect(self._save)

        self.parentWidget().installEventFilter(self)
        self.anchor_button.installEventFilter(self)
        self.hide()

    def _status_label(self):
        label = QLabel("", self)
        label.setObjectName("aiConfigStatus")
        label.setWordWrap(True)
        return label

    def set_values(self, segmentation_dir, speech_dir):
        self.segmentation_edit.setText(segmentation_dir or "")
        self.speech_edit.setText(speech_dir or "")

    def set_status(self, segmentation_found, speech_models):
        self.segmentation_status.setText(segmentation_status_text(segmentation_found))
        self.speech_status.setText(speech_status_text(speech_models))

    def set_result_message(self, message):
        self.result_label.setText(message)

    def reposition(self):
        parent = self.parentWidget()
        point = self.anchor_button.mapTo(
            parent,
            QPoint(self.anchor_button.width() - self.width(), self.anchor_button.height()),
        )
        x = max(8, min(point.x(), parent.width() - self.width() - 8))
        y = max(8, point.y() + 4)
        self.move(x, y)
        self.raise_()

    @Slot()
    def toggle(self, checked=False):
        if self._open:
            self.hide_popup()
            return
        self.show_popup()

    def show_popup(self):
        self.reposition()
        self.show()
        self.raise_()
        self._set_anchor_checked(True)
        self._open = True
        self.segmentation_edit.setFocus()

    def hide_popup(self):
        self.hide()
        self._set_anchor_checked(False)
        self._open = False

    def eventFilter(self, source, event):
        if self._open and event.type() in (QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show):
            QTimer.singleShot(0, self.reposition)
        return super().eventFilter(source, event)

    def _set_anchor_checked(self, checked):
        action = self.anchor_button.defaultAction()
        if action is not None and action.isCheckable():
            action.setChecked(checked)
        self.anchor_button.setChecked(checked)

    def _browse(self, edit, kind):
        folder = QFileDialog.getExistingDirectory(self, f"Select {kind} model folder", edit.text().strip())
        if folder:
            edit.setText(folder)
            self._save()

    def _save(self):
        self.result_label.setText("Saving settings...")
        self.settingsSaveRequested.emit(self.segmentation_edit.text().strip(), self.speech_edit.text().strip())
