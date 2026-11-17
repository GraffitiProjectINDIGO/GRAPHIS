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

from PySide6.QtWidgets import QMessageBox

StandardButton = QMessageBox.StandardButton


MESSAGE_BOX_STYLE = """
QMessageBox {
    background-color: rgb(40, 44, 52);
    color: rgb(210, 210, 210);
}
QMessageBox QLabel {
    background: transparent;
    color: rgb(230, 230, 230);

}
QMessageBox QPushButton {
    padding: 5px 12px;
    background-color: rgb(52, 59, 72);
    color: rgb(230, 230, 230);
    border: 1px solid rgb(70, 78, 92);
    border-radius: 4px;
}
QMessageBox QPushButton:hover {
    background-color: rgb(65, 74, 90);
}
QMessageBox QPushButton:pressed {
    background-color: rgb(35, 40, 49);
}
"""


def warning(parent, title, text, buttons=QMessageBox.StandardButton.Ok, default_button=QMessageBox.StandardButton.Ok):
    box = _message_box(parent, QMessageBox.Icon.Warning, title, text, buttons, default_button)
    return box.exec()


def question(
    parent,
    title,
    text,
    buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    default_button=QMessageBox.StandardButton.No,
):
    box = _message_box(parent, QMessageBox.Icon.Question, title, text, buttons, default_button)
    return box.exec()


def _message_box(parent, icon, title, text, buttons, default_button):
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons)
    box.setDefaultButton(default_button)
    box.setStyleSheet(MESSAGE_BOX_STYLE)
    return box
