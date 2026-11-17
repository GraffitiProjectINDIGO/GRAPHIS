# Copyright (C) 2026 Martin Wieser

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QToolButton, QWidget

from graphis.app.gui.resources import icon as resource_icon
from graphis.app.gui.resources import pixmap as resource_pixmap
from graphis.app.gui.spinningwaiter import SPINNINGWaiter


class GraphisStatusBar(QWidget):
    def __init__(self, version, parent=None):
        super().__init__(parent)

        self.setObjectName("graphisStatusBar")
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("""
            QWidget#graphisStatusBar {
                background-color: rgb(85, 85, 85);
            }
            QLabel {
                color: rgb(180, 185, 192);
                background: transparent;
                font-family: Segoe UI;
            }
            QLabel#statusText {
                color: rgb(180, 185, 192);
            }
            QLabel#credits {
                color: rgb(180, 185, 192);
            }
            
            QLabel#lbl_sqlite_name {
                color: rgb(180, 185, 192);
                background: transparent;
                font: 9pt "Segoe UI";
                padding: 0 8px;
            }
            QToolButton#btn_info_popup {
                background: transparent;
                border: none;
                padding: 2px;
            }
            QToolButton#btn_info_popup:hover,
            QToolButton#btn_info_popup:checked {
                background: rgb(65, 74, 90);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        # layout.setSpacing(10)

        self.btn_info_popup = QToolButton(self)
        self.btn_info_popup.setObjectName("btn_info_popup")
        self.btn_info_popup.setCheckable(True)
        self.btn_info_popup.setAutoRaise(True)
        self.btn_info_popup.setFixedSize(40, 40)
        self.btn_info_popup.setIcon(resource_icon("info-40.svg"))
        self.btn_info_popup.setIconSize(QSize(28, 28))
        self.btn_info_popup.setToolTip("Logs")
        layout.addWidget(self.btn_info_popup)

        self.spinner_holder = QWidget(self)
        self.spinner_holder.setFixedSize(28, 28)
        spinner_layout = QHBoxLayout(self.spinner_holder)
        spinner_layout.setContentsMargins(0, 0, 0, 0)
        spinner_layout.setSpacing(0)

        self.spinner = SPINNINGWaiter(self.spinner_holder, centerOnParent=False)
        self.spinner.setObjectName("statusWaitingSpinner")
        self.spinner.setInnerRadius(5)
        self.spinner.setLineLength(6)
        self.spinner.setLineWidth(2)
        self.spinner.setColor(Qt.GlobalColor.white)
        spinner_layout.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.spinner_holder)

        self.status_text = QLabel("Ready", self)
        self.status_text.setObjectName("statusText")
        self.status_text.setMinimumWidth(140)
        self.status_text.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(
            self.status_text,
        )

        self.lbl_sqlite_name = QLabel("", self)
        self.lbl_sqlite_name.setObjectName("lbl_sqlite_name")
        self.lbl_sqlite_name.setMinimumWidth(180)
        self.lbl_sqlite_name.setMaximumWidth(320)
        self.lbl_sqlite_name.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.lbl_sqlite_name, 1)

        layout.addStretch(1)

        self.logo_label = QLabel(self)
        self.logo_label.setObjectName("statusLogo")
        self.logo_label.setPixmap(resource_pixmap("INDIGO_logoGRAPHIS_text.png"))
        self.logo_label.setScaledContents(True)
        self.logo_label.setFixedSize(150, 23)
        layout.addWidget(self.logo_label)

        layout.addStretch(1)
        self.credits_label = QLabel(
            '<a style="color: rgb(180, 185, 192); text-decoration: none;" '
            'href="https://projectindigo.eu">GRAPHIS @ INDIGO - https://projectindigo.eu</a>',
            self,
        )
        self.credits_label.setObjectName("credits")
        self.credits_label.setTextFormat(Qt.TextFormat.RichText)
        self.credits_label.setOpenExternalLinks(True)
        self.credits_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.credits_label.setMinimumWidth(250)
        self.credits_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.credits_label, 1)

        self.version_label = QLabel(str(version), self)
        self.version_label.setObjectName("statusVersion")
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.version_label.setMinimumWidth(80)
        self.version_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.version_label)

        self.spinner.stop()

    def set_version(self, version):
        self.version_label.setText(str(version))

    def set_message(self, message):
        self.status_text.setText(message)

    def set_sqlite_name(self, sqlite_name):
        self.lbl_sqlite_name.setText(str(sqlite_name))

    def clear_sqlite_name(self):
        self.lbl_sqlite_name.clear()

    def set_info_popup_icon(self, icon):
        self.btn_info_popup.setIcon(QIcon(icon))

    def set_info_popup_checked(self, checked):
        self.btn_info_popup.setChecked(checked)

    def start_spinner(self):
        self.spinner.start()

    def stop_spinner(self):
        self.spinner.stop()
