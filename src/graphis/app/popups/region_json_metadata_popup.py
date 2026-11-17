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

from __future__ import annotations

import json

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QVBoxLayout


class RegionJsonMetadataPopup(QDialog):
    def __init__(self, parent, additional_data: dict, protected_keys: set[str], object_id=None):
        super().__init__(parent)
        self.additional_data = None
        self.protected_keys = set(protected_keys)
        self.setWindowTitle("Edit additional image region metadata")
        self.resize(720, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: rgb(40, 44, 52);
                color: rgb(210, 210, 210);
            }
            QLabel {
                color: rgb(220, 220, 220);
                font: 10pt "Segoe UI";
            }
            QPlainTextEdit {
                background-color: rgb(27, 29, 35);
                color: rgb(230, 230, 230);
                border: 1px solid rgb(95, 112, 116);
                border-radius: 3px;
                padding: 6px;
                font: 10pt "Consolas";
            }
            QPushButton {
                background-color: rgb(52, 59, 72);
                border: 1px solid rgb(70, 78, 92);
                border-radius: 4px;
                padding: 5px 10px;
                color: rgb(230, 230, 230);
                font: 9pt "Segoe UI";
            }
            QPushButton:hover {
                background-color: rgb(65, 74, 90);
            }
            QPushButton:pressed {
                background-color: rgb(35, 40, 49);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = "Additional metadata for this image region"
        if object_id is not None:
            title = f"{title} ({object_id})"
        layout.addWidget(QLabel(title, self))

        state_label = QLabel(
            "Only additional image region metadata keys can be edited here. No checks will be performed",
            self,
        )
        state_label.setWordWrap(True)
        layout.addWidget(state_label)

        self.text_edit = QPlainTextEdit(self)
        self.text_edit.setPlainText(json.dumps(additional_data or {}, indent=2, ensure_ascii=False))
        layout.addWidget(self.text_edit, 1)

        self.status_label = QLabel("", self)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        buttons.accepted.connect(self._accept_json)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept_json(self):
        try:
            data = json.loads(self.text_edit.toPlainText())
        except json.JSONDecodeError as exc:
            self.status_label.setText(f"Invalid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}.")
            return
        if not isinstance(data, dict):
            self.status_label.setText("Additional image region metadata must be a JSON object.")
            return
        protected = sorted(key for key in data if key in self.protected_keys)
        if protected:
            self.status_label.setText(f"Standard region keys cannot be edited here: {', '.join(protected)}")
            return
        self.additional_data = data
        self.accept()
