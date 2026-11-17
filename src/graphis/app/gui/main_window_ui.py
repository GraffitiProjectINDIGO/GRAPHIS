# Copyright (C) 2026 Martin Wieser

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from graphis.app.graphic.digitizerview import DIGITIZERView
from graphis.app.gui.thumbnail_preview_view import ThumbnailPreviewPanel


class MainWindowUiBuilder:
    def setup(self, window, path_to_css_main: Path):
        if not window.objectName():
            window.setObjectName("MainWindow")

        window.resize(1100, 950)
        window.setMinimumSize(QSize(640, 560))
        window.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        window.setWindowTitle("MainWindow")
        self._apply_palette(window)
        self._apply_font(window)
        self._apply_stylesheet(window, path_to_css_main)
        self._create_actions(window)
        self._create_central_widget(window)

    def _apply_palette(self, window):
        palette = window.palette()
        colors = {
            QPalette.ColorRole.WindowText: QColor(255, 255, 255),
            QPalette.ColorRole.Button: QColor(40, 44, 52),
            QPalette.ColorRole.Light: QColor(66, 73, 90),
            QPalette.ColorRole.Midlight: QColor(55, 61, 75),
            QPalette.ColorRole.Dark: QColor(22, 24, 30),
            QPalette.ColorRole.Mid: QColor(29, 32, 40),
            QPalette.ColorRole.Text: QColor(210, 210, 210),
            QPalette.ColorRole.BrightText: QColor(255, 255, 255),
            QPalette.ColorRole.ButtonText: QColor(255, 255, 255),
            QPalette.ColorRole.Base: QColor(40, 44, 52),
            QPalette.ColorRole.Window: QColor(40, 44, 52),
            QPalette.ColorRole.Shadow: QColor(0, 0, 0),
            QPalette.ColorRole.Highlight: QColor(85, 170, 255),
            QPalette.ColorRole.Link: QColor(85, 170, 255),
            QPalette.ColorRole.LinkVisited: QColor(255, 0, 127),
            QPalette.ColorRole.AlternateBase: QColor(22, 24, 30),
            QPalette.ColorRole.ToolTipBase: QColor(44, 49, 60),
            QPalette.ColorRole.ToolTipText: QColor(210, 210, 210),
        }
        for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
            for role, color in colors.items():
                palette.setColor(group, role, color)

        disabled_text = QColor(22, 24, 30)
        for role in (
            QPalette.ColorRole.WindowText,
            QPalette.ColorRole.Text,
            QPalette.ColorRole.ButtonText,
        ):
            palette.setColor(QPalette.ColorGroup.Disabled, role, disabled_text)
        for role, color in colors.items():
            if role not in (
                QPalette.ColorRole.WindowText,
                QPalette.ColorRole.Text,
                QPalette.ColorRole.ButtonText,
            ):
                palette.setColor(QPalette.ColorGroup.Disabled, role, color)

        window.setPalette(palette)

    def _apply_font(self, window):
        font = QFont()
        font.setFamilies(["Segoe UI"])
        font.setPointSize(10)
        window.setFont(font)

    def _apply_stylesheet(self, window, path_to_css_main: Path):
        window.setStyleSheet(path_to_css_main.read_text(encoding="utf-8"))

    def _create_actions(self, window):
        window.actionMenu = QAction(window)
        window.actionMenu.setObjectName("actionMenu")
        window.actionMenu.setText("Menu")
        window.actionMenu.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentOpen)))

        window.actionUser = QAction(window)
        window.actionUser.setObjectName("actionUser")
        window.actionUser.setText("User")
        window.actionUser.setToolTip("Change user information")
        window.actionUser.setIcon(QIcon(QIcon.fromTheme("user-available")))
        window.actionUser.setMenuRole(QAction.MenuRole.NoRole)

    def _create_central_widget(self, window):
        window.centralwidget = QWidget(window)
        window.centralwidget.setObjectName("centralwidget")
        window.centralwidget.setMinimumSize(QSize(280, 420))
        window.centralwidget.setStyleSheet("background: transparent; color: rgb(210, 210, 210);")

        window.verticalLayout_3 = QVBoxLayout(window.centralwidget)
        window.verticalLayout_3.setObjectName("verticalLayout_3")
        window.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        window.verticalLayout_3.setSpacing(0)

        window.verticalLayout_2 = QVBoxLayout()
        window.verticalLayout_2.setObjectName("verticalLayout_2")
        window.verticalLayout_2.setSpacing(0)

        window.frame = QFrame(window.centralwidget)
        window.frame.setObjectName("frame")
        window.frame.setFrameShape(QFrame.Shape.StyledPanel)
        window.frame.setFrameShadow(QFrame.Shadow.Raised)

        window.verticalLayout_5 = QVBoxLayout(window.frame)
        window.verticalLayout_5.setObjectName("verticalLayout_5")
        window.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        window.verticalLayout_5.setSpacing(0)

        window.lbl_image_name = QLabel(window.frame)
        window.lbl_image_name.setObjectName("lbl_image_name")
        image_name_font = QFont()
        image_name_font.setPointSize(12)
        image_name_font.setBold(True)
        window.lbl_image_name.setFont(image_name_font)
        window.lbl_image_name.clear()
        window.verticalLayout_5.addWidget(window.lbl_image_name)

        window.lbl_image_path = QLabel(window.frame)
        window.lbl_image_path.setObjectName("lbl_image_path")
        window.lbl_image_path.setMinimumSize(QSize(0, 30))
        window.lbl_image_path.setWordWrap(False)
        window.lbl_image_path.clear()
        window.verticalLayout_5.addWidget(window.lbl_image_path)

        window.splitter_images = QSplitter(window.frame)
        window.splitter_images.setObjectName("splitter_images")
        window.splitter_images.setOrientation(Qt.Orientation.Vertical)
        window.splitter_images.setChildrenCollapsible(False)

        window.view_digizizer = DIGITIZERView(window.splitter_images)
        window.view_digizizer.setObjectName("view_digizizer")
        window.view_digizizer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        window.view_digizizer.setMinimumSize(QSize(100, 0))
        window.view_digizizer.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        window.splitter_images.addWidget(window.view_digizizer)

        window.table_preview = ThumbnailPreviewPanel(window.splitter_images)
        window.table_preview.setObjectName("table_preview")
        window.table_preview.setStyleSheet("background-color: rgb(80, 80, 80);")
        window.splitter_images.addWidget(window.table_preview)

        window.verticalLayout_5.addWidget(window.splitter_images)
        window.verticalLayout_2.addWidget(window.frame)
        window.verticalLayout_3.addLayout(window.verticalLayout_2)
        window.setCentralWidget(window.centralwidget)
