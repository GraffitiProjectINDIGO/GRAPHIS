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

import json

from PySide6 import QtCore, QtGui, QtWidgets

from graphis.app.config_paths import app_config_file
from graphis.app.gui.resources import icon_url
from graphis.app.gui.resources import pixmap as resource_pixmap

USER_FILE_NAME = "users.json"
MAX_SAVED_USERS = 100
MAX_FIELD_LENGTH = 500
CHOOSE_USER_TEXT = "Choose existing User"
DEFAULT_USER_TEXT = "your name"
DEFAULT_URI_TEXT = "URI/ORCID"


class POPUPUser(QtWidgets.QWidget):
    got_user = QtCore.Signal(str, str)

    def __init__(self):
        super().__init__(parent=None)
        self.user_dict = {}

        self._build_ui()
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.save_user_button.clicked.connect(self.save_user)
        self.reset_user_button.clicked.connect(self.reset_saved_users)

        self.user_dict = self._load_saved_users()
        if self.user_dict:
            for user in self.user_dict:
                self.combo_user.addItem(user)
        else:
            self.combo_user.setVisible(False)

        self.combo_user.currentIndexChanged.connect(self.change_user)

    def _build_ui(self):
        self.setObjectName("popup_user")
        self.setWindowTitle("MainWindow")
        self.setFixedSize(400, 280)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

        font = QtGui.QFont("Segoe UI", 10)
        self.setFont(font)
        self.setStyleSheet(
            """
            QWidget#popup_user {
                background: transparent;
            }
            QToolTip {
                color: #ffffff;
                background-color: rgba(27, 29, 35, 160);
                border: 1px solid rgb(40, 40, 40);
                border-radius: 2px;
            }
            """
        )

        root_layout = QtWidgets.QVBoxLayout(self)
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(0, 0, 0, 0)

        frame_main = QtWidgets.QFrame(self)
        frame_main.setObjectName("frame_main1")
        frame_main.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        frame_main.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        frame_main.setStyleSheet(
            """
            QLineEdit, QComboBox {
                background-color: rgb(27, 29, 35);
                border-radius: 5px;
                border: 2px solid rgb(27, 29, 35);
                color: rgb(250, 250, 250);
                padding-left: 10px;
            }
            QLineEdit:hover, QComboBox:hover {
                border: 2px solid rgb(64, 71, 88);
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid rgb(91, 101, 124);
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 25px;
                border-left: 3px solid rgba(39, 44, 54, 150);
                border-top-right-radius: 3px;
                border-bottom-right-radius: 3px;
                background-image: url("""
            + icon_url("cil-arrow-bottom.png")
            + """);
                background-position: center;
                background-repeat: no-repeat;
            }
            QComboBox QAbstractItemView {
                color: rgb(85, 170, 255);
                background-color: rgb(27, 29, 35);
                padding: 10px;
                selection-background-color: rgb(39, 44, 54);
            }
            QPushButton {
                border: 2px solid rgb(52, 59, 72);
                border-radius: 5px;
                background-color: rgb(52, 59, 72);
                color: rgb(250, 250, 250);
            }
            QPushButton:hover {
                background-color: rgb(57, 65, 80);
                border: 2px solid rgb(61, 70, 86);
            }
            QPushButton:pressed {
                background-color: rgb(35, 40, 49);
                border: 2px solid rgb(43, 50, 61);
            }
            QPushButton#reset_users {
                background-color: transparent;
                color: rgb(160, 160, 160);
                border: 1px solid rgb(75, 80, 92);
                border-radius: 3px;
                font: 7pt "Segoe UI";
                padding: 1px 5px;
            }
            QPushButton#reset_users:hover {
                color: rgb(220, 220, 220);
                border: 1px solid rgb(95, 105, 122);
                background-color: rgb(45, 50, 60);
            }
            """
        )
        root_layout.addWidget(frame_main)

        main_layout = QtWidgets.QVBoxLayout(frame_main)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        top_frame = QtWidgets.QFrame(frame_main)
        top_frame.setObjectName("frame_top1")
        top_frame.setFixedHeight(40)
        top_frame.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        top_frame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        top_frame.setStyleSheet("background-color: rgb(85, 85, 85);")
        main_layout.addWidget(top_frame)

        top_layout = QtWidgets.QHBoxLayout(top_frame)
        top_layout.setContentsMargins(10, 8, 0, 8)

        self.label_title_bar_top1 = QtWidgets.QLabel(top_frame)
        self.label_title_bar_top1.setObjectName("label_title_bar_top1")
        self.label_title_bar_top1.setFixedSize(150, 23)
        self.label_title_bar_top1.setStyleSheet("background: transparent; color: rgb(250, 250, 250);")
        self.label_title_bar_top1.setPixmap(resource_pixmap("INDIGO_logoGRAPHIS_text.png"))
        self.label_title_bar_top1.setScaledContents(True)
        top_layout.addWidget(self.label_title_bar_top1)
        top_layout.addStretch()

        center_frame = QtWidgets.QFrame(frame_main)
        center_frame.setObjectName("frame_center1")
        center_frame.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        center_frame.setFrameShadow(QtWidgets.QFrame.Shadow.Raised)
        center_frame.setStyleSheet("background-color: rgb(40, 44, 52);")
        main_layout.addWidget(center_frame)

        center_layout = QtWidgets.QGridLayout(center_frame)
        center_layout.setContentsMargins(40, 10, 39, 9)
        center_layout.setHorizontalSpacing(10)
        center_layout.setVerticalSpacing(6)

        self.user_error = QtWidgets.QLabel(center_frame)
        self.user_error.setObjectName("user_error")
        error_font = QtGui.QFont()
        error_font.setPointSize(9)
        error_font.setBold(True)
        self.user_error.setFont(error_font)
        self.user_error.setStyleSheet("color: rgb(150, 30, 30);")
        center_layout.addWidget(self.user_error, 0, 0, 1, 3)

        self.label_credits1 = QtWidgets.QLabel("Welcome!\nPlease type info:", center_frame)
        self.label_credits1.setObjectName("label_credits1")
        welcome_font = QtGui.QFont("Segoe UI", 14)
        self.label_credits1.setFont(welcome_font)
        self.label_credits1.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
        self.label_credits1.setStyleSheet("color: rgb(250, 250, 250);")
        self.label_credits1.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignLeading
            | QtCore.Qt.AlignmentFlag.AlignLeft
            | QtCore.Qt.AlignmentFlag.AlignVCenter
        )
        center_layout.addWidget(self.label_credits1, 1, 0, 1, 2)

        self.reset_user_button = QtWidgets.QPushButton("Reset", center_frame)
        self.reset_user_button.setObjectName("reset_users")
        self.reset_user_button.setFixedSize(44, 18)
        self.reset_user_button.setToolTip("Delete saved users")
        center_layout.addWidget(
            self.reset_user_button,
            1,
            2,
            1,
            1,
            QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignTop,
        )

        input_font = QtGui.QFont()
        input_font.setPointSize(10)
        input_font.setBold(True)

        self.input_user = QtWidgets.QLineEdit(DEFAULT_USER_TEXT, center_frame)
        self.input_user.setObjectName("input_user")
        self.input_user.setFont(input_font)
        self.input_user.setFixedHeight(31)
        center_layout.addWidget(self.input_user, 2, 0, 1, 2)

        self.save_user_button = QtWidgets.QPushButton("START", center_frame)
        self.save_user_button.setObjectName("save_user")
        self.save_user_button.setFont(input_font)
        self.save_user_button.setFixedSize(82, 68)
        center_layout.addWidget(self.save_user_button, 2, 2, 2, 1)

        self.input_uri = QtWidgets.QLineEdit(DEFAULT_URI_TEXT, center_frame)
        self.input_uri.setObjectName("input_uri")
        self.input_uri.setFont(input_font)
        self.input_uri.setFixedHeight(31)
        center_layout.addWidget(self.input_uri, 3, 0, 1, 2)

        self.combo_user = QtWidgets.QComboBox(center_frame)
        self.combo_user.setObjectName("combo_user")
        self.combo_user.setFont(input_font)
        self.combo_user.setFixedHeight(31)
        self.combo_user.addItem(CHOOSE_USER_TEXT)
        center_layout.addWidget(self.combo_user, 4, 0, 1, 3)

    def change_user(self):
        user = self.combo_user.currentText()
        if user != CHOOSE_USER_TEXT and user in self.user_dict:
            self.input_user.setText(user)
            self.input_uri.setText(self.user_dict[user])

    def save_user(self):
        user = self.input_user.text().strip()
        if user and user.lower() != DEFAULT_USER_TEXT:
            uri = ""
            input_uri = self.input_uri.text().strip()
            if input_uri.lower() != DEFAULT_URI_TEXT.lower():
                uri = input_uri
            self.got_user.emit(user, uri)
            self.user_dict[user] = uri

            try:
                self._user_file().write_text(json.dumps(self.user_dict, indent=2), encoding="utf-8")
            except Exception:
                pass

            self.close()
        else:
            self.user_error.setText("Please enter your name")

    def reset_saved_users(self):
        self.user_dict = {}
        self.combo_user.clear()
        self.combo_user.addItem(CHOOSE_USER_TEXT)
        self.combo_user.setVisible(False)
        try:
            self._user_file().unlink(missing_ok=True)
            self.user_error.setText("Saved users reset")
        except OSError:
            self.user_error.setText("Could not reset saved users")

    @staticmethod
    def _user_file():
        return app_config_file(USER_FILE_NAME)

    @classmethod
    def _load_saved_users(cls):
        user_file = cls._user_file()
        if not user_file.exists():
            return {}
        try:
            data = json.loads(user_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if not isinstance(data, dict):
            return {}

        users = {}
        for user, uri in data.items():
            if len(users) >= MAX_SAVED_USERS:
                break
            user = str(user).strip()
            uri = str(uri).strip()
            if not user or len(user) > MAX_FIELD_LENGTH or len(uri) > MAX_FIELD_LENGTH:
                continue
            users[user] = uri
        return users
