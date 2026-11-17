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
from pathlib import Path

from PySide6 import QtCore
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from graphis import software_version
from graphis.app.gui.resources import icon as resource_icon
from graphis.app.gui.resources import icon_url
from graphis.app.gui.resources import pixmap as resource_pixmap
from graphis.app.imgregion.json_model_viewer import JsonModel
from graphis.app.var_classes import build_year, license_version

ABOUT_HTML = """
<h2><span style="color:#b49629;">GRAPHIS</span></h2>
<p>
    <b>GRAPHIS</b> (Generate Regions and Annotations for Photos using the IPTC Standard)
    is an open-source Windows-based application to create, change, annotate, and visualise
    IPTC image regions.
</p>
<p>
    It is developed for the academic graffiti project INDIGO
    (<a href="https://projectindigo.eu">https://projectindigo.eu</a>) and available via
    GitHub (<a href="https://github.com/GraffitiProjectINDIGO/GRAPHIS">GRAPHIS repository</a>).
</p>
<p>
    GRAPHIS provides a graphical user interface to generate, visualise, and annotate image
    regions as enabled by the IPTC Photo Metadata Standard. These regions are shapes like
    rectangles, circles, or polygons that can be saved within an image or as sidecar XMP.
</p>
<p>
    GRAPHIS stores operations in an SQLite database, making it possible to quit the program
    at any point and continue later by reloading that database. Images and their metadata can
    be written back using ExifTool.
</p>
<p>
    For more information or questions please email <b>info@projectindigo.eu</b>.
</p>
<p>
    This program is free software: you can redistribute it and/or modify it under the terms
    of the GNU General Public License as published by the Free Software Foundation, either
    version 3 of the License, or any later version.
</p>
<p>
    This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
    without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
    See the GNU General Public License for more details.
</p>
"""

CITATION_HTML = """
<b>Cite:</b>
Verhoeven, G.J., Wieser, M., Carloni, M., 2024.
<i>GRAPHIS—Visualise, Draw, Annotate, and Save Image Regions in Graffiti Photos</i>,
in: <ins>disseminate | analyse | understand graffiti-scapes. Proceedings of the
goINDIGO2023 international graffiti symposium</ins>, Vienna, Austria. 14-16 June 2023.
Urban Creativity, Lisbon, pp. 72-103. DOI:
<a style="color:#b2ba57;" href="https://doi.org/10.48619/indigo.v0i0.977">10.48619/indigo.v0i0.977</a>.
"""

POPUP_STYLE = """
QWidget {
    background: transparent;
    color: rgb(210, 210, 210);
}
QToolTip {
    color: #ffffff;
    background-color: rgba(27, 29, 35, 160);
    border: 1px solid rgb(40, 40, 40);
    border-radius: 2px;
}
QLabel {
    color: rgb(150, 150, 150);
}
QTextBrowser {
    background-color: transparent;
    border: none;
    color: rgb(210, 210, 210);
}
QScrollBar:horizontal {
    border: none;
    background: rgb(52, 59, 72);
    height: 14px;
    margin: 0px 21px 0 21px;
}
QScrollBar::handle:horizontal {
    background: rgb(178, 186, 87);
    min-width: 25px;
    border-radius: 7px;
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    border: none;
    background: rgb(55, 63, 77);
    width: 20px;
}
QScrollBar::up-arrow:horizontal,
QScrollBar::down-arrow:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: none;
}
QScrollBar:vertical {
    border: none;
    background: rgb(52, 59, 72);
    width: 14px;
    margin: 21px 0 21px 0;
}
QScrollBar::handle:vertical {
    background: rgb(178, 186, 87);
    min-height: 25px;
    border-radius: 7px;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    border: none;
    background: rgb(55, 63, 77);
    height: 20px;
}
QScrollBar::up-arrow:vertical,
QScrollBar::down-arrow:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
}
"""


def license_tree_style():
    closed_icon = icon_url("cil-size-grip.png")
    open_icon = icon_url("circle.svg")
    return (
        """
QTreeView {
    alternate-background-color: rgb(38, 40, 56);
    background: transparent;
}
QTreeView::branch:has-children:!has-siblings:closed,
QTreeView::branch:closed:has-children:has-siblings {
    border-image: none;
    image: url("""
        + closed_icon
        + """);
}
QTreeView::branch:open:has-children:!has-siblings,
QTreeView::branch:open:has-children:has-siblings {
    border-image: none;
    image: url("""
        + open_icon
        + """);
}
"""
    )


CLOSE_BUTTON_STYLE = """
QPushButton {
    border: none;
    background-color: transparent;
}
QPushButton:hover {
    background-color: rgb(150, 40, 23);
}
QPushButton:pressed {
    background-color: rgb(250, 39, 10);
}
"""


class POPUPAbout(QWidget):
    def __init__(self, licence_folder: Path, parent=None):
        super().__init__(parent)
        self.dragPos = QtCore.QPointF()
        self.license_model = JsonModel()

        self._setup_window()
        self._build_ui()
        self._load_license_table(licence_folder)
        self._connect_events()

    def _setup_window(self):
        self.setObjectName("popup_about")
        self.resize(850, 761)
        self.setMinimumSize(QSize(850, 600))
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.setWindowTitle("About GRAPHIS")
        self.setPalette(self._popup_palette())
        self.setFont(self._font(10))
        self.setStyleSheet(POPUP_STYLE)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

    def _build_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.frame_top = self._create_top_frame()
        self.frame_center = self._create_center_frame()

        self.main_layout.addWidget(self.frame_top)
        self.main_layout.addWidget(self.frame_center, 1)

    def _create_top_frame(self):
        frame = QFrame(self)
        frame.setObjectName("frame_top")
        frame.setFixedHeight(40)
        frame.setStyleSheet("background-color: rgb(127, 84, 0); color: white;")
        frame.setFrameShape(QFrame.Shape.NoFrame)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(10)

        self.lbl_icon = QLabel(frame)
        self.lbl_icon.setObjectName("lbl_icon")
        self.lbl_icon.setFixedSize(30, 30)
        self.lbl_icon.setPixmap(resource_pixmap("INDIGO_logoGRAPHIS.png"))
        self.lbl_icon.setScaledContents(True)
        layout.addWidget(self.lbl_icon)

        self.label_title = QLabel("About GRAPHIS", frame)
        self.label_title.setObjectName("label_title")
        title_font = self._font(10, bold=True)
        self.label_title.setFont(title_font)
        self.label_title.setStyleSheet("background: transparent; color: white;")
        self.label_title.setToolTip("Move window")
        layout.addWidget(self.label_title, 1)

        self.btn_close = QPushButton(frame)
        self.btn_close.setObjectName("btn_close")
        self.btn_close.setToolTip("Close")
        self.btn_close.setFixedSize(40, 40)
        self.btn_close.setIconSize(QSize(16, 16))
        self.btn_close.setStyleSheet(CLOSE_BUTTON_STYLE)
        self.btn_close.setIcon(resource_icon("cil-x.png"))
        layout.addWidget(self.btn_close)

        return frame

    def _create_center_frame(self):
        frame = QFrame(self)
        frame.setObjectName("frame_center")
        frame.setStyleSheet("background-color: rgb(34, 36, 50);")
        frame.setFrameShape(QFrame.Shape.NoFrame)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        self.lbl_citation = QLabel(frame)
        self.lbl_citation.setObjectName("lbl_citation")
        self.lbl_citation.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_citation.setOpenExternalLinks(True)
        self.lbl_citation.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.lbl_citation.setWordWrap(True)
        self.lbl_citation.setText(CITATION_HTML)
        self.lbl_citation.setStyleSheet(
            "background-color: rgb(44, 49, 60);"
            "border: 1px solid rgba(178, 186, 87, 120);"
            "border-radius: 5px;"
            "padding: 8px;"
            "color: rgb(220, 220, 220);"
        )
        layout.addWidget(self.lbl_citation)

        intro_layout = QHBoxLayout()
        intro_layout.setSpacing(16)

        logo = QLabel(frame)
        logo.setObjectName("logo")
        logo.setFixedSize(140, 140)
        logo.setPixmap(resource_pixmap("INDIGO_logoGRAPHIS.png"))
        logo.setScaledContents(True)
        intro_layout.addWidget(logo, 0, Qt.AlignmentFlag.AlignTop)

        self.textEdit = QTextBrowser(frame)
        self.textEdit.setObjectName("textEdit")
        self.textEdit.setReadOnly(True)
        self.textEdit.setUndoRedoEnabled(False)
        self.textEdit.setFrameShape(QFrame.Shape.NoFrame)
        self.textEdit.setOpenExternalLinks(True)
        self.textEdit.document().setDefaultStyleSheet("a { color: #b2ba57; }")
        self.textEdit.setHtml(ABOUT_HTML)
        intro_layout.addWidget(self.textEdit, 1)
        layout.addLayout(intro_layout, 1)

        self.lbl_copyright = QLabel(frame)
        self.lbl_copyright.setObjectName("lbl_copyright")
        self.lbl_copyright.setFont(self._font(12, bold=True))
        self.lbl_copyright.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.lbl_copyright.setText(
            f"Version: {software_version} / Copyright(c) {build_year} - Martin Wieser & Geert Verhoeven\n"
            f"License: {license_version}"
        )
        layout.addWidget(self.lbl_copyright)

        qt_info = QLabel(frame)
        qt_info.setObjectName("qt_info")
        qt_info.setFont(self._font(10, bold=True))
        qt_info.setTextFormat(Qt.TextFormat.RichText)
        qt_info.setWordWrap(True)
        qt_info.setText(
            "<p>Graphis is using the <span style='color:#2cde85;'>Qt6 engine with "
            "PySide6/shiboken6</span> under GPLv3 and <span style='color:#016cb1;'>"
            "LibRAW</span> under LGPLv2.1. Instructions to obtain source code can "
            "be found at github.com/GraffitiProjectINDIGO/GRAPHIS."
            "GRAPHIS thankfully relies on open-source packages. The table below lists "
            "packages and libraries with their license information. Double click to expand "
            "license details.</p>"
        )
        layout.addWidget(qt_info)

        license_title = QLabel("License Table", frame)
        license_title.setObjectName("license_title")
        license_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        license_title.setFixedWidth(120)
        license_title.setStyleSheet("border: 1px solid rgba(170, 170, 255, 100); border-radius: 8px;")
        layout.addWidget(license_title, 0, Qt.AlignmentFlag.AlignHCenter)

        self.treeView_license = QTreeView(frame)
        self.treeView_license.setObjectName("treeView_license")
        self.treeView_license.setStyleSheet(license_tree_style())
        self.treeView_license.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.treeView_license.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        self.treeView_license.setAutoScroll(False)
        self.treeView_license.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.treeView_license.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.treeView_license.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.treeView_license.setHeaderHidden(True)
        self.treeView_license.setToolTip("Double click to expand")
        self.treeView_license.header().setMinimumSectionSize(220)
        self.treeView_license.header().setDefaultSectionSize(220)
        self.treeView_license.header().setStretchLastSection(True)
        layout.addWidget(self.treeView_license, 1)

        return frame

    def _load_license_table(self, licence_folder):
        with open(licence_folder / "ThirdPartyNotices.json", encoding="utf-8") as file:
            license_items = json.load(file)

        self.license_model.load(license_items)
        self.treeView_license.setAlternatingRowColors(True)
        self.treeView_license.setModel(self.license_model)
        self.treeView_license.setColumnWidth(0, 200)
        self.treeView_license.setColumnWidth(1, 400)
        self.treeView_license.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

    def _connect_events(self):
        self.btn_close.clicked.connect(self.close)
        self.frame_top.mouseMoveEvent = self._move_window

    def _move_window(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.isMaximized():
            self.move(self.pos() + event.globalPosition().toPoint() - self.dragPos.toPoint())
            self.dragPos = event.globalPosition()
            event.accept()

    def mousePressEvent(self, event):
        self.dragPos = event.globalPosition()

    @staticmethod
    def _font(point_size, bold=False):
        font = QFont()
        font.setFamilies(["Segoe UI"])
        font.setPointSize(point_size)
        font.setBold(bold)
        return font

    @staticmethod
    def _popup_palette():
        palette = QPalette()
        text = QColor(210, 210, 210)
        transparent = QColor(0, 0, 0, 0)
        for group in (
            QPalette.ColorGroup.Active,
            QPalette.ColorGroup.Inactive,
            QPalette.ColorGroup.Disabled,
        ):
            palette.setColor(group, QPalette.ColorRole.WindowText, text)
            palette.setColor(group, QPalette.ColorRole.Text, text)
            palette.setColor(group, QPalette.ColorRole.ButtonText, text)
            palette.setColor(group, QPalette.ColorRole.Button, transparent)
            palette.setColor(group, QPalette.ColorRole.Base, transparent)
            palette.setColor(group, QPalette.ColorRole.Window, transparent)
            palette.setColor(group, QPalette.ColorRole.ToolTipBase, QColor(44, 49, 60))
            palette.setColor(group, QPalette.ColorRole.ToolTipText, text)
            palette.setColor(group, QPalette.ColorRole.Highlight, QColor(85, 170, 255))
            palette.setColor(group, QPalette.ColorRole.Link, QColor(85, 170, 255))
        return palette
