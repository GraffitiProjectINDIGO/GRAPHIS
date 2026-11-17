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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout


class ImageMetadataPopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("imageMetadataPopup")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.table = QTableWidget(self)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Tag", "Value"])
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self.setStyleSheet("""
            QFrame#imageMetadataPopup {
                background-color: rgba(42, 47, 56, 235);
                border: 1px solid rgb(90, 98, 112);
                border-radius: 5px;
            }
            QTableWidget {
                background-color: rgb(31, 35, 42);
                alternate-background-color: rgb(37, 42, 50);
                color: rgb(225, 230, 238);
                border: 1px solid rgb(70, 78, 92);
                gridline-color: rgb(58, 65, 78);
                selection-background-color: rgb(76, 96, 125);
                font-size: 10pt;
            }
            QHeaderView::section {
                background-color: rgb(54, 61, 73);
                color: rgb(235, 238, 244);
                border: 0;
                border-right: 1px solid rgb(70, 78, 92);
                border-bottom: 1px solid rgb(70, 78, 92);
                padding: 4px;
                font-weight: bold;
            }
        """)

        self.hide()

    def set_metadata(self, metadata):
        rows = list(metadata.items()) if isinstance(metadata, dict) else []
        if not rows:
            rows = [("metadata", "{}")]

        self.table.setRowCount(len(rows))
        item_flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        for row, (key, value) in enumerate(rows):
            key_item = QTableWidgetItem(str(key))
            value_item = QTableWidgetItem(self._table_value(value))
            key_item.setFlags(item_flags)
            value_item.setFlags(item_flags)
            self.table.setItem(row, 0, key_item)
            self.table.setItem(row, 1, value_item)
        self.table.resizeRowsToContents()

    @staticmethod
    def _table_value(value):
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return "" if value is None else str(value)
