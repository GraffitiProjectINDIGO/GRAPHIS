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

from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QLayout


class DatabaseStatisticsPopup(QFrame):
    def __init__(self, parent, anchor_button, auto_hide_ms=5000):
        super().__init__(parent)
        self.anchor_button = anchor_button
        self._open = False

        self.setObjectName("databaseStatisticsPopup")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumWidth(260)
        self.setStyleSheet("""
            QFrame#databaseStatisticsPopup {
                background-color: rgb(48, 54, 65);
                border: 1px solid rgb(90, 98, 112);
                border-radius: 6px;
            }
            QLabel {
                color: rgb(220, 220, 220);
                font: 10pt "Segoe UI";
                background: transparent;
            }
            QLabel#statisticsTitle {
                color: rgb(235, 235, 235);
                font: 700 10pt "Segoe UI";
            }
            QLabel#statisticsCount {
                font: 700 13pt "Segoe UI";
            }
        """)

        layout = QGridLayout(self)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setHorizontalSpacing(18)
        layout.setVerticalSpacing(8)

        title = QLabel("Database statistics", self)
        title.setObjectName("statisticsTitle")
        layout.addWidget(title, 0, 0, 1, 2)

        self.name_labels = {}
        self.count_labels = {}
        self._add_row(layout, 1, "image", "Images", QColor("#d7191c"))
        self._add_separator(layout, 2)
        self._add_row(layout, 3, "point", "Points", QColor("lightgreen"))
        self._add_row(layout, 4, "multipoint", "Multipoints", QColor("lightgreen"))
        self._add_row(layout, 5, "circle", "Circles", QColor("lightblue"))
        self._add_row(layout, 6, "linestring", "Linestrings", QColor("#d02c8b"))
        self._add_row(layout, 7, "multilinestring", "Multilinestrings", QColor("#d02c8b"))
        self._add_row(layout, 8, "rectangle", "Rectangles", QColor("orange"))
        self._add_row(layout, 9, "polygon", "Polygons", QColor("purple"))
        self._add_row(layout, 10, "multipolygon", "Multipolygons", QColor("purple"))
        self._add_separator(layout, 11)
        self._add_row(layout, 12, "valid", "Valid", QColor("#26c281"))
        self._add_row(layout, 13, "warning", "Warnings", QColor("#f0b905"))
        self._add_row(layout, 14, "error", "Errors", QColor("#ed0909"))

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(auto_hide_ms)
        self.timer.timeout.connect(self.hide_popup)

        self.anchor_button.setCheckable(True)
        self._set_anchor_checked(False)

        self.parentWidget().installEventFilter(self)
        self.anchor_button.installEventFilter(self)
        self.hide()

    def _add_row(self, layout, row, key, text, color):
        name_label = QLabel(text, self)
        count_label = QLabel("0", self)
        count_label.setObjectName("statisticsCount")
        count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(name_label, row, 0)
        layout.addWidget(count_label, row, 1)

        self.name_labels[key] = name_label
        self.count_labels[key] = count_label
        self.set_color(key, color)

    def _add_separator(self, layout, row):
        line = QFrame(self)
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setStyleSheet("color: rgb(90, 98, 112);")
        layout.addWidget(line, row, 0, 1, 2)

    def set_counts(
        self,
        image=None,
        rectangle=None,
        polygon=None,
        circle=None,
        point=None,
        linestring=None,
        valid=None,
        warning=None,
        error=None,
        multipoint=None,
        multilinestring=None,
        multipolygon=None,
    ):
        counts = {
            "image": image,
            "rectangle": rectangle,
            "polygon": polygon,
            "circle": circle,
            "point": point,
            "linestring": linestring,
            "multipoint": multipoint,
            "multilinestring": multilinestring,
            "multipolygon": multipolygon,
            "valid": valid,
            "warning": warning,
            "error": error,
        }
        for key, count in counts.items():
            if count is not None:
                self.set_count(key, count)

    def set_count(self, key, count):
        label = self.count_labels.get(key)
        if label is None:
            return
        label.setText(str(count))

    def set_color(self, key, color):
        color = QColor(color)
        if not color.isValid():
            return

        color_name = color.name()
        multi_key = {"point": "multipoint", "linestring": "multilinestring", "polygon": "multipolygon"}.get(key)
        for row_key in (key, multi_key):
            for label in (self.name_labels.get(row_key), self.count_labels.get(row_key)):
                if label is not None:
                    label.setStyleSheet(f"color: {color_name};")

    def reposition(self):
        parent = self.parentWidget()
        point = self.anchor_button.mapTo(
            parent,
            QPoint(0, self.anchor_button.height()),
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

    def hide_popup(self):
        self.timer.stop()
        self.hide()
        self._set_anchor_checked(False)
        self._open = False

    def eventFilter(self, source, event):
        if self._open and event.type() in (QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show):
            QTimer.singleShot(0, self.reposition)
        return super().eventFilter(source, event)
