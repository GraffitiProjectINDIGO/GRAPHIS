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

import logging
from datetime import datetime

from PySide6.QtCore import QDir, QEvent, QPoint, QSize, QTimer, Slot
from PySide6.QtGui import QColor, QTextCursor
from PySide6.QtWidgets import QFileDialog, QFrame, QHBoxLayout, QPushButton, QTextEdit, QVBoxLayout

from graphis.app.gui.resources import icon as resource_icon

logger = logging.getLogger(__name__)


class LogPopup(QFrame):
    def __init__(self, parent, anchor_button):
        super().__init__(parent)
        self.anchor_button = anchor_button
        self._open = False

        self.setObjectName("logPopup")
        self.setFixedSize(620, 220)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame#logPopup {
                background-color: transparent;
                border: none;
            }
            QFrame#logPopupPanel {
                background-color: rgba(47, 49, 65, 240);
                border: 1px solid rgb(90, 98, 112);
                border-radius: 6px;
            }
            QTextEdit {
                background-color: rgb(27, 29, 35);
                color: rgb(230, 230, 230);
                border: none;
                border-radius: 4px;
                padding: 8px;
                font: 9pt "Segoe UI";
            }
            QPushButton {
                background-color: transparent;
                border: none;
                color: rgb(230, 230, 230);
                font: 9pt "Segoe UI";
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 28);
            }
        """)

        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.frame_info = QFrame(self)
        self.frame_info.setObjectName("logPopupPanel")
        self.frame_info.setStyleSheet("background-color: rgba(34, 113, 150, 190);")
        outer_layout.addWidget(self.frame_info)

        layout = QVBoxLayout(self.frame_info)
        layout.setContentsMargins(10, 8, 10, 10)
        layout.setSpacing(6)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        self.btn_save = QPushButton(self.frame_info)
        self.btn_save.setToolTip("Save logs")
        self.btn_save.setIcon(resource_icon("save.svg"))
        self.btn_save.setIconSize(QSize(24, 24))
        self.btn_save.setFixedWidth(40)
        self.btn_save.setFixedHeight(28)
        self.btn_save.clicked.connect(self.save_logs)
        button_layout.addWidget(self.btn_save)
        layout.addLayout(button_layout)

        self.info_screen = QTextEdit(self.frame_info)
        self.info_screen.setReadOnly(True)
        self.info_screen.setUndoRedoEnabled(False)
        layout.addWidget(self.info_screen, 1)

        if self.parentWidget() is not None:
            self.parentWidget().installEventFilter(self)
        self.anchor_button.installEventFilter(self)
        self.hide()

    def reposition(self):
        parent = self.parentWidget()
        if parent is None:
            return
        point = self.anchor_button.mapTo(parent, QPoint(0, 0))
        x = max(8, min(point.x(), parent.width() - self.width() - 8))
        y = max(8, point.y() - self.height() - 6)
        self.move(x, y)
        self.raise_()

    def append_text(self, text, color):
        self.info_screen.moveCursor(QTextCursor.MoveOperation.End)
        self.info_screen.setTextColor(QColor(color))
        self.info_screen.insertPlainText(text)
        self.info_screen.setTextColor(QColor(255, 255, 255))
        scroll = self.info_screen.verticalScrollBar()
        scroll.setValue(scroll.maximum())

    def set_level_style(self, frame_style):
        self.frame_info.setStyleSheet(frame_style)

    @Slot()
    def toggle(self):
        if self._open:
            self.hide_popup()
            return
        self.show_popup()

    def show_popup(self):
        self.reposition()
        self.show()
        self.raise_()
        self.anchor_button.setChecked(True)
        self._open = True

    def hide_popup(self):
        self.hide()
        self.anchor_button.setChecked(False)
        self._open = False

    def save_logs(self):
        default_path = QDir.homePath() + "/" + datetime.now().strftime("%Y%m%d_%H%M%S_logs.txt")
        log_path, _ = QFileDialog.getSaveFileName(
            self,
            caption="Save Logs",
            dir=default_path,
            filter="Text File (*.txt)",
        )
        if log_path:
            with open(log_path, "a+", encoding="utf-8") as fid:
                fid.write(self.info_screen.toPlainText())
            logger.info("Saved logs to %s", log_path, extra={"finished": True})

    def eventFilter(self, source, event):
        if self._open and event.type() in (QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show):
            QTimer.singleShot(0, self.reposition)
        return super().eventFilter(source, event)
