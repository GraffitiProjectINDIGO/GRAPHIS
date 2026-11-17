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

import math

import numpy
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QLineF, QPointF
from PySide6.QtGui import QPolygonF
from shapely import geometry

from graphis.app.var_classes import color_on_image_hoover, list_of_points_to_list


class PointAnnotation(QtWidgets.QGraphicsItem):
    def __init__(self, parent=None, color=None, obj_id=0, image_id=0, object_type="", pen_width=3, display_mode="cross"):
        super().__init__(parent)
        self.setZValue(10)
        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)

        self.obj_id = obj_id
        self.image_id = image_id
        self.object_type = object_type
        self.pen_width = pen_width
        self.display_mode = display_mode
        self.marker_size = 40.0
        self.mouse_hoover = False
        self.color_no_Alpha = QtGui.QColor(color)
        self.color_no_Alpha.setAlpha(255)

    def boundingRect(self):
        margin = self.marker_size + self.pen_width + 2
        return QtCore.QRectF(-margin, -margin, margin * 2, margin * 2)

    def shape(self):
        path = QtGui.QPainterPath()
        path.addEllipse(self.boundingRect())
        return path

    def paint(self, painter, option, widget=None):
        del option, widget
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        pen_color = QtGui.QColor("green") if self.mouse_hoover else self.color_no_Alpha
        pen = QtGui.QPen(pen_color, self.pen_width)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        size = self.marker_size
        if self.display_mode == "circle":
            painter.drawEllipse(QtCore.QPointF(0, 0), size, size)
        else:
            painter.drawLine(QtCore.QPointF(-size, 0), QtCore.QPointF(size, 0))
            painter.drawLine(QtCore.QPointF(0, -size), QtCore.QPointF(0, size))

    def set_color(self, color):
        self.color_no_Alpha = QtGui.QColor(color)
        self.color_no_Alpha.setAlpha(255)
        self.update()

    def set_point(self, pos_x, pos_y):
        self.setPos(pos_x, pos_y)

    def move(self, vector):
        self.setPos(self.pos() + QPointF(vector[0], vector[1]))

    def change_geometry(self, pos, target_point=None):
        return

    def get_coords(self, image_width, image_height):
        pos = self.pos()
        valid = 0 <= pos.x() <= image_width and 0 <= pos.y() <= image_height
        return [pos.x(), pos.y()], valid

    def close_point(self, pos, distance):
        diff = pos - self.pos()
        return diff.x() ** 2 + diff.y() ** 2 < distance**2, 0

    def is_valid(self):
        return True

    def hoverEnterEvent(self, event):
        self.mouse_hoover = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.mouse_hoover = False
        self.update()
        super().hoverLeaveEvent(event)


class LineStringAnnotation(QtWidgets.QGraphicsPathItem):
    def __init__(self, parent=None, color=None, obj_id=0, image_id=0, object_type="", pen_width=3):
        super().__init__(parent)
        self._points = QPolygonF()
        self.setZValue(10)
        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)

        self.obj_id = obj_id
        self.image_id = image_id
        self.object_type = object_type
        self.pen_width = pen_width
        self.mouse_hoover = False

        self.color_no_Alpha = QtGui.QColor(color)
        self.color_no_Alpha.setAlpha(255)
        self._apply_pen(self.color_no_Alpha)

    def _apply_pen(self, color):
        pen = QtGui.QPen(color, self.pen_width)
        pen.setCosmetic(True)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)

    def _update_path(self):
        path = QtGui.QPainterPath()
        if len(self._points) > 0:
            path.moveTo(self._points[0])
            for index in range(1, len(self._points)):
                path.lineTo(self._points[index])
        self.setPath(path)

    def shape(self):
        stroker = QtGui.QPainterPathStroker()
        stroker.setWidth(max(self.pen_width + 8, 12))
        stroker.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        stroker.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        return stroker.createStroke(self.path())

    def set_color(self, color):
        self.color_no_Alpha = QtGui.QColor(color)
        self.color_no_Alpha.setAlpha(255)
        self._apply_pen(QtGui.QColor("green") if self.mouse_hoover else self.color_no_Alpha)

    def set_points(self, points):
        polygon = QPolygonF()
        for point in points:
            if isinstance(point, QPointF):
                polygon.append(QPointF(point))
            else:
                polygon.append(QPointF(point[0], point[1]))
        self._points = polygon
        self._update_path()

    def points(self):
        return QPolygonF(self._points)

    def polygon(self):
        return self.points()

    def setPolygon(self, polygon):
        self.set_points(polygon)

    def move(self, vector):
        moved = QPolygonF()
        for point in self._points:
            moved.append(QPointF(point.x() + vector[0], point.y() + vector[1]))
        self._points = moved
        self._update_path()

    def change_geometry(self, pos, target_point=None):
        if target_point is None or target_point < 0 or target_point >= len(self._points):
            return
        self._points[target_point] = pos
        self._update_path()

    def get_coords(self, image_width, image_height):
        valid = len(self._points) >= 2
        for point in self._points:
            if point.x() < 0 or point.y() < 0 or point.x() > image_width or point.y() > image_height:
                valid = False
        return list_of_points_to_list(self._points), valid

    def close_point(self, pos, distance):
        close_points = []
        for idx, point in enumerate(self._points):
            dist = point - pos
            dist_squared = dist.x() ** 2 + dist.y() ** 2
            if dist_squared < distance**2:
                close_points.append((dist_squared, idx))

        if not close_points:
            return False, 0

        return True, min(close_points)[1]

    def close_octo(
        self,
        octo: "OctoLines",
    ):
        inter_p: QPointF | None = None
        points = self._points.toList()
        if len(points) < 2:
            return False, 0, inter_p

        for idx in range(len(points) - 1):
            line = QLineF(points[idx], points[idx + 1])
            valid, inter_p = octo.intersect(line)
            if valid:
                return True, idx, inter_p

        return False, 0, inter_p

    def is_valid(self):
        if len(self._points) < 2:
            return False
        for index in range(len(self._points) - 1):
            if (self._points[index] - self._points[index + 1]).manhattanLength() > 0.1:
                return True
        return False

    def hoverEnterEvent(self, event):
        self.mouse_hoover = True
        self._apply_pen(QtGui.QColor("green"))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.mouse_hoover = False
        self._apply_pen(self.color_no_Alpha)
        super().hoverLeaveEvent(event)


class RectangleAnnotation(QtWidgets.QGraphicsRectItem):
    def __init__(self, parent=None, color=None, obj_id=0, image_id=0, object_type="", pen_width=3):
        super().__init__(parent)
        self.start_point_x = 0
        self.start_point_y = 0
        self.start = True
        self.mouse_hoover = False
        self.setZValue(10)

        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)

        self.obj_id = obj_id
        self.image_id = image_id
        self.object_type = object_type

        self.color = QtGui.QColor(color)
        self.color.setAlpha(0)
        self.color_no_Alpha = QtGui.QColor(color)
        self.color_no_Alpha.setAlpha(255)
        self.pen_width = pen_width
        p = QtGui.QPen(self.color_no_Alpha, self.pen_width)
        p.setCosmetic(True)
        self.setPen(p)
        self.setBrush(self.color)

    def set_color(self, color):
        self.color = QtGui.QColor(color)
        self.color.setAlpha(0)
        self.color_no_Alpha = QtGui.QColor(color)
        self.color_no_Alpha.setAlpha(255)
        p = QtGui.QPen(self.color_no_Alpha, self.pen_width)
        p.setCosmetic(True)
        self.setPen(p)
        self.setBrush(self.color)

    def start_rectangle(self, p):
        self.start_point_x = p.x()
        self.start_point_y = p.y()

    def resize_rectangle(self, pos):
        if self.start_point_x != 0:
            width = abs(self.start_point_x - pos.x())
            height = abs(self.start_point_y - pos.y())
            start_point_new_x = self.start_point_x
            start_point_new_y = self.start_point_y
            if self.start_point_x > pos.x():
                start_point_new_x = pos.x()
            if self.start_point_y > pos.y():
                start_point_new_y = pos.y()
            self.setRect(start_point_new_x, start_point_new_y, width, height)

    def move(self, vector):
        rect = self.rect()

        x = rect.x() + vector[0]
        y = rect.y() + vector[1]

        self.setRect(x, y, rect.width(), rect.height())

    def get_coords(self, image_width, image_height):

        valid = True
        rect = self.rect()

        x = rect.x()
        y = rect.y()

        if x < 0 or y < 0 or (x + rect.width() > image_width) or (y + rect.height()) > image_height:
            valid = False

        return list_of_points_to_list(QPolygonF(self.rect(), closed=True).toList()), valid

    def change_geometry(self, pos, target_point=None):

        rect = self.rect()

        middle_x = rect.x() + rect.width() / 2
        middle_y = rect.y() + rect.height() / 2

        if pos.x() < middle_x:
            rect.setX(pos.x())
        # pass
        else:
            rect.setWidth(pos.x() - rect.x())

        if pos.y() < middle_y:
            rect.setY(pos.y())
        else:
            rect.setHeight(pos.y() - rect.y())

        self.setRect(rect)

    def close_point(self, pos, distance):

        rect_coords = self.rect().getCoords()

        if (abs(pos.x() - rect_coords[0]) < distance or abs(pos.x() - rect_coords[2]) < distance) and (
            abs(pos.y() - rect_coords[1]) < distance or abs(pos.y() - rect_coords[3]) < distance
        ):
            return True, 0
        return False, 0

    def is_valid(self):
        return True

    def hoverEnterEvent(self, event):
        self.mouse_hoover = True
        self.setBrush(color_on_image_hoover)
        p = QtGui.QPen(QtGui.QColor("green"), self.pen_width)
        p.setCosmetic(True)
        self.setPen(p)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.mouse_hoover = False
        self.setBrush(self.color)
        p = QtGui.QPen(self.color_no_Alpha, self.pen_width)
        p.setCosmetic(True)
        self.setPen(p)
        super().hoverLeaveEvent(event)


class OctoLines:
    def __init__(self, x, y, pick_radius):
        self.line_list = [
            QLineF(QPointF(x, y + pick_radius), QPointF(x + pick_radius * 0.707, y + pick_radius * 0.707)),
            QLineF(QPointF(x + pick_radius * 0.707, y + pick_radius * 0.707), QPointF(x + pick_radius, y)),
            QLineF(QPointF(x + pick_radius, y), QPointF(x + pick_radius * 0.707, y - pick_radius * 0.707)),
            QLineF(QPointF(x + pick_radius * 0.707, y - pick_radius * 0.707), QPointF(x, y - pick_radius)),
            QLineF(QPointF(x, y - pick_radius), QPointF(x - pick_radius * 0.707, y - pick_radius * 0.707)),
            QLineF(QPointF(x - pick_radius * 0.707, y - pick_radius * 0.707), QPointF(x - pick_radius, y)),
            QLineF(QPointF(x - pick_radius, y), QPointF(x - pick_radius * 0.707, y + pick_radius * 0.707)),
            QLineF(QPointF(x - pick_radius * 0.707, y + pick_radius * 0.707), QPointF(x, y + pick_radius)),
        ]

    def intersect(self, line: QLineF):
        for octo_line in self.line_list:
            inter_type, inter_p = line.intersects(octo_line)
            if inter_type == QLineF.BoundedIntersection:
                return True, inter_p
        return False, None

    def items(self):
        return self.line_list


class CircleAnnotation(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, parent=None, color=None, obj_id=0, image_id=0, object_type="", pen_width=3):
        super().__init__(parent)
        self.setZValue(10)
        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)

        self.obj_id = obj_id
        self.image_id = image_id
        self.object_type = object_type

        self.color = QtGui.QColor(color)
        self.color.setAlpha(0)
        self.color_no_Alpha = QtGui.QColor(color)
        self.color_no_Alpha.setAlpha(255)
        self.pen_width = pen_width
        p = QtGui.QPen(self.color_no_Alpha, self.pen_width)
        p.setCosmetic(True)
        self.setPen(p)

        self.setBrush(self.color)

    def set_radius_from_position(self, position):
        # middle = self.rect.

        ellipse_rect = self.rect()
        x = ellipse_rect.x() + ellipse_rect.width() / 2.0
        y = ellipse_rect.y() + ellipse_rect.height() / 2.0

        radius = math.sqrt((x - position.x()) ** 2 + (y - position.y()) ** 2)

        self.setRect(x - radius, y - radius, radius * 2, radius * 2)

    def move(self, vector):
        ellipse_rect = self.rect()

        x = ellipse_rect.x() + vector[0]
        y = ellipse_rect.y() + vector[1]

        self.setRect(x, y, ellipse_rect.width(), ellipse_rect.height())

    def change_geometry(self, position, _dum):
        self.set_radius_from_position(position)

    def get_coords(self, image_width, image_height):
        ellipse_rect = self.rect()
        valid = True
        x = ellipse_rect.x() + ellipse_rect.width() / 2.0
        y = ellipse_rect.y() + ellipse_rect.height() / 2.0

        if (
            ellipse_rect.x() < 0
            or ellipse_rect.y() < 0
            or (ellipse_rect.x() + ellipse_rect.width() > image_width)
            or (ellipse_rect.y() + ellipse_rect.height()) > image_height
        ):
            valid = False

        return [x, y, ellipse_rect.width() / 2.0], valid

    def close_point(self, pos, distance):

        ellipse_rect = self.rect()
        x = ellipse_rect.x() + ellipse_rect.width() / 2.0
        y = ellipse_rect.y() + ellipse_rect.height() / 2.0
        x = pos.x() - x
        y = pos.y() - y
        diff = math.sqrt(x**2 + y**2)
        if abs(diff - ellipse_rect.width() / 2.0) < distance:
            return True, 0
        return False, 0

    def is_valid(self):
        # duck typing function needed by polygon and rectangle
        return True

    def set_color(self, color):
        self.color = QtGui.QColor(color)
        self.color.setAlpha(0)
        self.color_no_Alpha = QtGui.QColor(color)
        self.color_no_Alpha.setAlpha(255)
        p = QtGui.QPen(self.color_no_Alpha, self.pen_width)
        p.setCosmetic(True)
        self.setPen(p)
        self.setBrush(self.color)

    def hoverEnterEvent(self, event):
        self.setBrush(color_on_image_hoover)
        p = QtGui.QPen(QtGui.QColor("green"), self.pen_width)
        p.setCosmetic(True)
        self.setPen(p)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(self.color)
        p = QtGui.QPen(self.color_no_Alpha, self.pen_width)
        p.setCosmetic(True)
        self.setPen(p)
        super().hoverLeaveEvent(event)


class PolygonAnnotation(QtWidgets.QGraphicsPolygonItem):
    def setPen(self, pen):
        pen = QtGui.QPen(pen)
        if getattr(self, "geometry_ring_index", 0) > 0:
            pen.setStyle(QtCore.Qt.PenStyle.DotLine)
        super().setPen(pen)

    def __init__(self, parent=None, color=None, obj_id=0, image_id=0, object_type="", pen_width=3):
        super().__init__(parent)
        self.m_points = []
        self.setZValue(10)

        self.setAcceptHoverEvents(True)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QtWidgets.QGraphicsItem.ItemSendsGeometryChanges, True)

        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))

        self.obj_id = obj_id
        self.image_id = image_id
        self.object_type = object_type

        self.color = QtGui.QColor(color)
        self.color.setAlpha(0)
        self.color_no_Alpha = QtGui.QColor(color)
        self.color_no_Alpha.setAlpha(255)
        self.pen_width = pen_width
        p = QtGui.QPen(self.color_no_Alpha, self.pen_width)
        p.setCosmetic(True)
        self.setPen(p)
        self.setBrush(self.color)

    def set_color(self, color):
        self.color = QtGui.QColor(color)
        self.color.setAlpha(0)
        self.color_no_Alpha = QtGui.QColor(color)
        self.color_no_Alpha.setAlpha(255)
        p = QtGui.QPen(self.color_no_Alpha, self.pen_width)
        p.setCosmetic(True)
        self.setPen(p)
        self.setBrush(self.color)

    def move(self, vector):

        coords = self.polygon().toList()
        poly = QPolygonF()
        for p in coords:
            p = [p.x() + vector[0], p.y() + vector[1]]
            poly.append(QPointF(*p))
        self.setPolygon(poly)

    def change_geometry(self, pos, target_point=None):
        if self.object_type == "rectangle":
            brect = numpy.array(list_of_points_to_list(self.polygon().toList()))
            mini_coo = brect.min(axis=0)
            maxi_coo = brect.max(axis=0)

            x = mini_coo[0]
            y = mini_coo[1]
            x2 = maxi_coo[0]
            y2 = maxi_coo[1]

            middle_x = x + (x2 - x) / 2.0
            middle_y = y + (y2 - y) / 2.0

            if pos.x() < middle_x:
                x = pos.x()
            # pass
            else:
                x2 = pos.x()

            if pos.y() < middle_y:
                y = pos.y()
            else:
                y2 = pos.y()

            coords = [[x, y], [x2, y], [x2, y2], [x, y2], [x, y]]
            poly = QPolygonF()
            for p in coords:
                poly.append(QPointF(*p))
            self.setPolygon(poly)

        else:
            poly = self.polygon()
            poly[target_point] = pos
            p = poly.toList()
            o = [[x.x(), x.y()] for x in p]
            i = geometry.Polygon(o)
            # print(i.is_valid)
            if i.is_valid:
                # self.polygon_item.setPolygon(poly)
                self.setPolygon(poly)

    def get_coords(self, image_width, image_height):
        coords = self.polygon().toList()
        valid = True
        for p in coords:
            if p.x() < 0 or p.y() < 0 or p.x() > image_width or p.y() > image_height:
                valid = False
        return list_of_points_to_list(self.polygon().toList()), valid

    def close_point(self, pos, distance):

        poly = self.polygon()
        close_points = []
        for idx, pt in enumerate(poly):
            dist = pt - pos
            dist_squared = dist.x() ** 2 + dist.y() ** 2
            if dist_squared < distance**2:
                close_points.append((dist_squared, idx))

        if not close_points:
            return False, 0

        return True, min(close_points)[1]

    def close_octo(
        self,
        octo: OctoLines,
    ):

        inter_p: QPointF | None = None
        poly = self.polygon().toList()
        if len(poly) < 2:
            return False, 0, inter_p
        if not self.polygon().isClosed():
            poly.append(poly[0])

        for idx in range(len(poly) - 1):
            line = QLineF(poly[idx], poly[idx + 1])
            valid, inter_p = octo.intersect(line)
            if valid:
                return True, idx, inter_p

        return False, 0, inter_p

    def is_valid(self):
        p = self.polygon().toList()
        o = [[x.x(), x.y()] for x in p]
        i = geometry.Polygon(o)
        if i.is_valid:
            return True
        return False

    def hoverEnterEvent(self, event):
        self.setBrush(color_on_image_hoover)
        p = QtGui.QPen(QtGui.QColor("green"), self.pen_width)
        p.setCosmetic(True)
        self.setPen(p)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(self.color)
        p = QtGui.QPen(self.color_no_Alpha, self.pen_width)
        p.setCosmetic(True)
        self.setPen(p)
        super().hoverLeaveEvent(event)
