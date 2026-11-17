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

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject, QGraphicsPathItem, QGraphicsTextItem

from graphis.app.imgregion.region_graph_model import boundary_shape_icon_path, region_shape


class RegionArrowItem(QGraphicsPathItem):
    def __init__(self, source, target):
        super().__init__()
        self.source = source
        self.target = target
        self.setZValue(-10)
        self.setPen(QPen(QColor("#7f8da3"), 2))
        self.update_position()

    def update_position(self):
        start = self.source.sceneBoundingRect().center()
        end = self.target.sceneBoundingRect().center()
        dx = max(80.0, abs(end.x() - start.x()) * 0.45)

        path = QPainterPath(start)
        path.cubicTo(start.x() + dx, start.y(), end.x() - dx, end.y(), end.x(), end.y())
        self.setPath(path)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)

        path = self.path()
        if path.isEmpty():
            return

        end = path.pointAtPercent(1)
        before = path.pointAtPercent(0.96)
        line_dx = end.x() - before.x()
        line_dy = end.y() - before.y()
        length = max((line_dx * line_dx + line_dy * line_dy) ** 0.5, 1.0)
        ux = line_dx / length
        uy = line_dy / length

        size = 10
        left = QPointF(end.x() - ux * size - uy * size * 0.55, end.y() - uy * size + ux * size * 0.55)
        right = QPointF(end.x() - ux * size + uy * size * 0.55, end.y() - uy * size - ux * size * 0.55)

        painter.setBrush(QColor("#7f8da3"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygonF([end, left, right]))


class RegionNodeItem(QGraphicsObject):
    moved = Signal(str)
    moveReleased = Signal(str, object)
    selected = Signal(str)

    MIN_WIDTH = 220
    HEIGHT = 112
    LEFT_PADDING = 14
    RIGHT_PADDING = 14
    ICON_SLOT_WIDTH = 44

    def __init__(self, node):
        super().__init__()
        self.node = node
        self.arrows = []
        self._active = False
        self._multi_selected = False
        self._merge_target = False
        self._dragging = False
        self._width = self.MIN_WIDTH

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)

        self.title_item = QGraphicsTextItem(self)
        self.title_item.setDefaultTextColor(QColor("#f2f5f8"))
        self.title_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.title_item.setTextWidth(-1)
        self.title_item.setPos(self.LEFT_PADDING, 9)
        self.title_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        self.shape_icon_item = QGraphicsSvgItem(parentItem=self)
        self.shape_icon_item.setPos(self._width - 36, 12)
        self.shape_icon_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.shape_icon_renderer = None

        self.detail_item = QGraphicsTextItem(self)
        self.detail_item.setDefaultTextColor(QColor("#b7c0cc"))
        self.detail_item.setFont(QFont("Segoe UI", 8))
        self.detail_item.setTextWidth(-1)
        self.detail_item.setPos(self.LEFT_PADDING, 43)
        self.detail_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

        self.refresh_text()
        self.refresh_colors()

    def refresh_colors(self):
        color = QColor(self.node.background_color)
        channels = [color.redF(), color.greenF(), color.blueF()]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        luminance = 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]
        foreground = QColor("#111111") if luminance > 0.192 else QColor("#ffffff")
        self.title_item.setDefaultTextColor(foreground)
        self.detail_item.setDefaultTextColor(foreground)
        self.update()

    def boundingRect(self):
        return QRectF(0, 0, self._width, self.HEIGHT)

    def set_active(self, active):
        if self._active == active:
            return
        self._active = active
        self.update()

    def set_multi_selected(self, active):
        if self._multi_selected == active:
            return
        self._multi_selected = active
        self.update()

    def set_merge_target(self, active):
        if self._merge_target == active:
            return
        self._merge_target = active
        self.update()

    def refresh_text(self):
        self.title_item.setPlainText(self.node.title)
        details = self.node.detail_lines
        self.detail_item.setPlainText("\n".join(details))
        self._resize_to_text(details)
        self.setToolTip(
            "Select this part for geometry operations; stored in the containing region JSON."
            if self.node.geometry_owner_id is not None
            else self.node.validation_tooltip
        )
        self._refresh_shape_icon()
        self.update()

    def _resize_to_text(self, details):
        self.title_item.setTextWidth(-1)
        self.detail_item.setTextWidth(-1)

        title_metrics = QFontMetricsF(self.title_item.font())
        detail_metrics = QFontMetricsF(self.detail_item.font())
        title_width = title_metrics.horizontalAdvance(self.node.title) + self.LEFT_PADDING + self.ICON_SLOT_WIDTH
        detail_width = max(
            (detail_metrics.horizontalAdvance(line) + self.LEFT_PADDING + self.RIGHT_PADDING for line in details),
            default=0,
        )
        width = max(self.MIN_WIDTH, title_width, detail_width)
        if abs(width - self._width) < 0.5:
            return

        self.prepareGeometryChange()
        self._width = width
        for arrow in self.arrows:
            arrow.update_position()

    def _refresh_shape_icon(self):
        icon_path = boundary_shape_icon_path(region_shape(self.node.region))
        if not icon_path:
            self.shape_icon_item.setVisible(False)
            return

        self.shape_icon_item.setScale(1.0)
        self.shape_icon_renderer = QSvgRenderer(icon_path, self)
        self.shape_icon_item.setSharedRenderer(self.shape_icon_renderer)
        self.shape_icon_item.setPos(self._width - 36, 12)

        icon_rect = self.shape_icon_item.boundingRect()
        if icon_rect.isEmpty():
            self.shape_icon_item.setVisible(False)
            return

        scale = min(22 / icon_rect.width(), 22 / icon_rect.height())
        self.shape_icon_item.setScale(scale)
        self.shape_icon_item.setVisible(True)

    def paint(self, painter, option, widget=None):
        rect = self.boundingRect()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        severity = self.node.validation_severity
        fill = QColor(self.node.background_color)
        border = QColor(self.node.geometry_color)
        pen_width = 2
        if self._active or self._multi_selected or self._merge_target:
            border = QColor(self.title_item.defaultTextColor())
            pen_width = 4
        pen = QPen(border, pen_width)
        if self._multi_selected or self._merge_target or (self.node.geometry_ring_index or 0) > 0:
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(fill)
        inset = pen_width / 2
        painter.drawRoundedRect(rect.adjusted(inset, inset, -inset, -inset), 7, 7)

        status_color = {"error": "#e45b5b", "warning": "#d9a441"}.get(severity, "#24c768")
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(status_color))
        painter.drawRoundedRect(QRectF(0, 0, 7, rect.height()), 4, 4)

        if self.shape_icon_item.isVisible():
            painter.setBrush(QColor("#334050"))
            painter.drawRoundedRect(QRectF(self._width - 42, 8, 32, 32), 6, 6)

    # def mouseDoubleClickEvent(self, event):
    #    self.selected.emit(self.node.object_id)
    #    event.accept()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.node.graph_pos = self.pos()
            for arrow in self.arrows:
                arrow.update_position()
            if self._dragging:
                self.moved.emit(self.node.object_id)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.moveReleased.emit(self.node.object_id, event.screenPos())
            self._dragging = False
