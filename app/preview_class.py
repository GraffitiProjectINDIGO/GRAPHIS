#Copyright (C) 2023 Martin Wieser
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

import math
from PySide6.QtCore import (
    Qt,
    QAbstractTableModel,
    QSize,
    QRectF)
from PySide6.QtGui import (
    QPainter,
    QFontMetricsF,
    QFont,
    QPainterPath,
    QColor)
from PySide6.QtWidgets import QStyledItemDelegate

from app.var_classes import TEXT_MARGIN, THUMBNAIL_FOOTER_PADDING, THUMBNAIL_MARGIN, NUMBER_OF_COLUMNS, CELL_PADDING

# Create a custom namedtuple class to hold our data.


class PreviewDelegate(QStyledItemDelegate):

    """
    Render thumbnail cells
    """
    def __init__(self,  parent=None) -> None:
        super().__init__(parent)

        self.emblemFont = QFont()
        self.emblemFont.setPointSize(self.emblemFont.pointSize() + 3)
        self.emblemFont.setBold(True)
        metrics = QFontMetricsF(self.emblemFont)

        self.rectangle_color = QColor("#000000")
        self.polygon_color = QColor("#000000")
        self.circle_color = QColor("#000000")
        self.width = 0
        self.height = 0

        # Determine the actual height of the font
        ext = "aaaa".upper()
        tbr = metrics.tightBoundingRect(ext)  # type:QRectF
        # height = tbr.height()
        self.emblem_height = tbr.height()*2

    def paint(self, painter, option, index):
        # data is our preview object
        data = index.model().data(index, Qt.DisplayRole)
        if data is None:
            return

        extension = data.title.split('.')[-1]
        polygon_number = data.polygon_number
        circle_number = data.circle_number
        rectangle_number = data.rectangle_number

        self.width = option.rect.width() - CELL_PADDING * 2
        self.height = option.rect.height() - CELL_PADDING * 2

        # Draw rectangle in which the individual items will be placed
        box_rect = QRectF(option.rect.x() + CELL_PADDING, option.rect.y() + CELL_PADDING, self.width , self.height)
        # shadowRect = QRectF(x + self.shadow_size, y + self.shadow_size, self.width, self.height)

        painter.setRenderHint(QPainter.Antialiasing, True)

        painter.fillRect(box_rect, QColor("#000000"))

        painter.drawRect(box_rect)
        painter.setRenderHint(QPainter.Antialiasing, False)

        # option.rect holds the area we are painting on the widget (our table cell)
        # scale our pixmap to fit
        scaled = data.image.scaled(
            self.width,
            self.height,
            aspectMode=Qt.KeepAspectRatio,
        )
        # Position in the middle of the area.
        x = CELL_PADDING + (self.width - scaled.width()) / 2.0
        y = CELL_PADDING + (self.height - scaled.height()) / 2.0
        painter.drawPixmap(option.rect.x() + x, option.rect.y() + y, scaled)

        x = option.rect.x() + CELL_PADDING
        y = option.rect.y() + CELL_PADDING

        # Draw a small coloured box containing the file extension in the
        # bottom right corner
        extension = extension.upper()
        # Calculate size of extension text
        painter.setFont(self.emblemFont)
        metrics = QFontMetricsF(self.emblemFont)
        tbr = metrics.tightBoundingRect(extension)  # type: QRectF
        emblem_width = tbr.width() + TEXT_MARGIN * 2
        emblem_rect_x = x + self.width - THUMBNAIL_MARGIN - emblem_width
        emblem_rect_y = y + self.height - THUMBNAIL_FOOTER_PADDING - self.emblem_height

        emblem_rect = QRectF(emblem_rect_x, emblem_rect_y, emblem_width, self.emblem_height)  # type: QRectF
        color = QColor("#5f6bfe")

        path = QPainterPath()
        path.addRoundedRect(emblem_rect, 5, 5)
        painter.fillPath(path, color)
        painter.setPen(QColor(Qt.white))
        painter.drawText(emblem_rect, Qt.AlignCenter, extension)

        def print_label_number(pos_x, pos_y, number, colour):
            # Assume the attribute is already upper case
            label_metrics = metrics.tightBoundingRect("%03i" % number)  # type: QRectF
            sec_width = label_metrics.width() + TEXT_MARGIN * 2
            rect_x = pos_x + THUMBNAIL_MARGIN
            rect_y = pos_y  # + self.emblem_height

            colour = colour
            sec_rect = QRectF(rect_x, rect_y, sec_width, self.emblem_height)
            painter_path = QPainterPath()
            painter_path.addRoundedRect(sec_rect, 5, 5)
            painter.fillPath(painter_path, colour)
            painter.drawText(sec_rect, Qt.AlignCenter, str(number))

        if circle_number:
            print_label_number(x + 3, y + 10, circle_number, self.circle_color)
        y = y + self.emblem_height + 10
        if rectangle_number:
            print_label_number(x + 3, y + 10, rectangle_number, self.rectangle_color)
        y = y + self.emblem_height + 10
        if polygon_number:
            print_label_number(x + 3, y + 10, polygon_number, self.polygon_color)

    def sizeHint(self, option, index):
        # All items the same size.
        return QSize(300, 200)


class PreviewModel(QAbstractTableModel):
    def __init__(self):
        super().__init__()
        # .data holds our data for display, as a list of Preview objects.
        self.previews = []

    def data(self, index, role):
        try:
            data = self.previews[index.row() * NUMBER_OF_COLUMNS + index.column()]
        except IndexError:
            # Incomplete last row.
            return

        if role == Qt.DisplayRole:
            return data   # Pass the data to our delegate to draw.

        if role == Qt.ToolTipRole:
            return data.title

        if role == Qt.UserRole:
            return data.path

        if role == Qt.UserRole+1:
            return data.id

    def add_number(self, img_id, object_type):
        self.layoutAboutToBeChanged.emit()
        if object_type == 'rectangle':
            self.previews[img_id].rectangle_number = self.previews[img_id].rectangle_number + 1
        elif object_type == 'polygon':
            self.previews[img_id].polygon_number = self.previews[img_id].polygon_number + 1
        elif object_type == 'circle':
            self.previews[img_id].circle_number = self.previews[img_id].circle_number + 1
        else:
            False
        self.layoutChanged.emit()
        return True

    def remove_number(self, img_id, object_type):
        self.layoutAboutToBeChanged.emit()
        if object_type == 'rectangle':
            self.previews[img_id].rectangle_number = self.previews[img_id].rectangle_number - 1
        elif object_type == 'polygon':
            self.previews[img_id].polygon_number = self.previews[img_id].polygon_number - 1
        elif object_type == 'circle':
            self.previews[img_id].circle_number = self.previews[img_id].circle_number - 1
        else:
            False
        self.layoutChanged.emit()
        return True

    def columnCount(self, index):
        return NUMBER_OF_COLUMNS

    def rowCount(self, index):
        n_items = len(self.previews)
        return math.ceil(n_items / NUMBER_OF_COLUMNS)
