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

from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)

from graphis.interface.metadata_tools import EXIFTOOL, EXIV2, normalize_metadata_tool, test_metadata_tool


class MetadataToolPopup(QFrame):
    settingsChanged = Signal(str, str, str)
    settingsSaveRequested = Signal(str, str, str)

    def __init__(self, parent, anchor_button):
        super().__init__(parent)
        self.anchor_button = anchor_button
        self._open = False
        self._current_tool = EXIFTOOL
        self._exiftool_path = ""
        self._exiv2_path = ""

        self.setObjectName("metadataToolPopup")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedSize(520, 165)
        self.setStyleSheet("""
            QFrame#metadataToolPopup {
                background-color: rgb(48, 54, 65);
                border: 1px solid rgb(90, 98, 112);
                border-radius: 6px;
            }
            QLabel {
                color: rgb(220, 220, 220);
                font: 10pt "Segoe UI";
            }
            QComboBox,
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
        layout.setVerticalSpacing(8)

        self.tool_combo = QComboBox(self)
        self.tool_combo.addItem("ExifTool", EXIFTOOL)
        self.tool_combo.addItem("Exiv2", EXIV2)

        self.path_edit = QLineEdit(self)
        self.path_edit.setPlaceholderText("Leave empty to use the system PATH")

        self.browse_button = QPushButton("Browse...", self)
        self.test_button = QPushButton("Test", self)
        self.save_button = QPushButton("Save", self)
        self.result_label = QLabel("", self)
        self.result_label.setWordWrap(True)

        layout.addWidget(QLabel("Tool", self), 0, 0)
        layout.addWidget(self.tool_combo, 0, 1, 1, 3)
        layout.addWidget(QLabel("Path", self), 1, 0)
        layout.addWidget(self.path_edit, 1, 1)
        layout.addWidget(self.browse_button, 1, 2)
        layout.addWidget(self.test_button, 1, 3)
        layout.addWidget(self.result_label, 2, 1, 1, 3)
        layout.addWidget(self.save_button, 3, 3)

        self.anchor_button.setCheckable(True)
        self._set_anchor_checked(False)

        self.tool_combo.currentIndexChanged.connect(self._tool_changed)
        self.path_edit.textChanged.connect(self._path_changed)
        self.browse_button.clicked.connect(self._browse)
        self.test_button.clicked.connect(self._test_current_tool)
        self.save_button.clicked.connect(self._save)

        self.parentWidget().installEventFilter(self)
        self.anchor_button.installEventFilter(self)
        self.hide()

    def set_values(self, tool, exiftool_path, exiv2_path):
        loaded_tool = normalize_metadata_tool(tool)
        self._exiftool_path = exiftool_path or ""
        self._exiv2_path = exiv2_path or ""
        index = self.tool_combo.findData(loaded_tool)
        signals_blocked = self.tool_combo.blockSignals(True)
        try:
            self.tool_combo.setCurrentIndex(max(index, 0))
        finally:
            self.tool_combo.blockSignals(signals_blocked)
        self._current_tool = loaded_tool
        self.path_edit.setText(self._path_for_tool(self._current_tool))
        self._refresh_tool_warning()

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
        self.path_edit.setFocus()

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

    def _tool_changed(self):
        self._store_current_path()
        self._current_tool = normalize_metadata_tool(self.tool_combo.currentData())
        self.path_edit.setText(self._path_for_tool(self._current_tool))
        self._refresh_tool_warning()
        self._emit_settings_changed()

    def _path_changed(self):
        self._store_current_path()
        self._emit_settings_changed()

    def _store_current_path(self):
        path = self.path_edit.text().strip()
        if self._current_tool == EXIV2:
            self._exiv2_path = path
        else:
            self._exiftool_path = path

    def _path_for_tool(self, tool):
        return self._exiv2_path if tool == EXIV2 else self._exiftool_path

    def _browse(self):
        current_path = self.path_edit.text().strip()
        start_dir = str(Path(current_path).parent) if current_path else ""
        tool_path, _ = QFileDialog.getOpenFileName(self, "Select metadata tool", start_dir)
        if tool_path:
            self.path_edit.setText(tool_path)
            self._save()

    def _save(self):
        self._store_current_path()
        self.result_label.setText("Saving settings...")
        self.settingsSaveRequested.emit(self._current_tool, self._exiftool_path, self._exiv2_path)

    def set_result_message(self, message):
        self.result_label.setText(message)

    def _emit_settings_changed(self):
        self.settingsChanged.emit(self._current_tool, self._exiftool_path, self._exiv2_path)

    def _refresh_tool_warning(self):
        self.result_label.clear()

    def _test_current_tool(self):
        self._store_current_path()
        result = test_metadata_tool(
            self._current_tool,
            self._path_for_tool(self._current_tool),
        )
        message = result.message
        self.result_label.setText(message)
