# Copyright (C) 2024 Martin Wieser
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

import json
from pathlib import Path

from PySide6.QtWidgets import QWidget, QHeaderView

from PySide6 import QtCore
from PySide6.QtCore import Qt, Signal

from app.ui_about import Ui_popup_about
from app.json_model_viewer import JsonModel
from app.var_classes import software_version, license_version, build_year


class POPUPAbout(QWidget):
    config_send = Signal(object)

    def __init__(self, licence_folder: Path, parent=None):
        QWidget.__init__(self, parent)
        self.ui = Ui_popup_about()
        self.ui.setupUi(self)
        self.dragPos = QtCore.QPointF()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self.ui.btn_close.clicked.connect(self.close)

        self.ui.lbl_copyright.setText("Version: %s\nCopyright(c) %s - Martin Wieser & Geert Verhoeven\nLicense: %s"
                                      % (software_version, build_year, license_version))

        model_license = JsonModel()
        json_list = []

        with open(licence_folder / "ThirdPartyNotices.json", 'r') as fe:
            json_list += json.load(fe)
        model_license.load(json_list)

        self.ui.treeView_license.setAlternatingRowColors(True)
        self.ui.treeView_license.setModel(model_license)
        self.ui.treeView_license.setColumnWidth(0, 200)
        self.ui.treeView_license.setColumnWidth(1, 400)
        self.ui.treeView_license.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        def move_window(event):
            if event.buttons() == Qt.LeftButton and not self.isMaximized():
                self.move(self.pos() + event.globalPosition().toPoint() - self.dragPos.toPoint())
                self.dragPos = event.globalPosition()
                event.accept()

        # WIDGET TO MOVE
        self.ui.frame_top.mouseMoveEvent = move_window

    def mousePressEvent(self, event):
        self.dragPos = event.globalPosition()
