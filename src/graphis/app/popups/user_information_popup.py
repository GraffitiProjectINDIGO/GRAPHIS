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

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import QFormLayout, QFrame, QLabel, QPlainTextEdit


class UserInformationPopup(QFrame):
    userChanged = Signal(str, str)

    def __init__(self, parent, anchor_button, auto_hide_ms=5000):
        super().__init__(parent)
        self.anchor_button = anchor_button
        self._open = False

        self.setObjectName("userInformationPopup")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFixedSize(380, 122)
        self.setStyleSheet("""
            QFrame#userInformationPopup {
                background-color: rgb(48, 54, 65);
                border: 1px solid rgb(90, 98, 112);
                border-radius: 6px;
            }
            QLabel {
                color: rgb(220, 220, 220);
                font: 10pt;
            }
            QPlainTextEdit {
                background-color: rgb(52, 70, 72);
                color: rgb(230, 230, 230);
                border: 1px solid rgb(95, 112, 116);
                border-radius: 3px;
                padding: 4px;
                font: 10pt;
            }
        """)

        layout = QFormLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        self.txt_user_name = self._create_text_edit("txt_user_name")
        self.txt_user_indent = self._create_text_edit("txt_user_indent")

        layout.addRow(QLabel("Name", self), self.txt_user_name)
        layout.addRow(QLabel("Identifier", self), self.txt_user_indent)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(auto_hide_ms)
        self.timer.timeout.connect(self.hide_popup)

        self.anchor_button.setCheckable(True)
        self._set_anchor_checked(False)

        self.txt_user_name.textChanged.connect(self._emit_user_changed)
        self.txt_user_indent.textChanged.connect(self._emit_user_changed)

        self.parentWidget().installEventFilter(self)
        self.anchor_button.installEventFilter(self)
        self.hide()

    def _create_text_edit(self, object_name):
        text_edit = QPlainTextEdit(self)
        text_edit.setObjectName(object_name)
        text_edit.setFixedHeight(34)
        text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        text_edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        return text_edit

    def set_user(self, user, user_uri):
        blocked_name = self.txt_user_name.blockSignals(True)
        blocked_indent = self.txt_user_indent.blockSignals(True)
        try:
            self.txt_user_name.setPlainText(user)
            self.txt_user_indent.setPlainText(user_uri)
        finally:
            self.txt_user_name.blockSignals(blocked_name)
            self.txt_user_indent.blockSignals(blocked_indent)
        self.userChanged.emit(user.strip(), user_uri.strip())

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

    def _set_anchor_checked(self, checked):
        action = self.anchor_button.defaultAction()
        if action is not None and action.isCheckable():
            action.setChecked(checked)
        self.anchor_button.setChecked(checked)

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
        self.timer.start()
        self.txt_user_name.setFocus()

    def hide_popup(self):
        self.timer.stop()
        self.hide()
        self._set_anchor_checked(False)
        self._open = False

    def eventFilter(self, source, event):
        if self._open and event.type() in (QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show):
            QTimer.singleShot(0, self.reposition)
        return super().eventFilter(source, event)

    def _emit_user_changed(self):
        if self._open:
            self.timer.start()
        self.userChanged.emit(
            self.txt_user_name.toPlainText().strip(),
            self.txt_user_indent.toPlainText().strip(),
        )
