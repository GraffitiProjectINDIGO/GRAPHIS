# Copyright (C) 2023 Martin Wieser
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
from shapely import geometry

from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtCore import (QPointF, QRect)
from PySide2.QtGui import (QPolygonF)
from app.var_classes import color_on_image_hoover, list_of_points_to_list


class RectangleAnnotation(QtWidgets.QGraphicsRectItem):
    def __init__(self, parent=None, color=None, obj_id=0, image_id=0, object_type='', pen_width=12):
        super(RectangleAnnotation, self).__init__(parent)
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

        self.setPen(QtGui.QPen(self.color_no_Alpha, self.pen_width))
        self.setBrush(self.color)

    def set_color(self, color):
        self.color = QtGui.QColor(color)
        self.color.setAlpha(0)
        self.color_no_Alpha = QtGui.QColor(color)
        self.color_no_Alpha.setAlpha(255)
        self.setPen(QtGui.QPen(self.color_no_Alpha, self.pen_width))
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

        if (abs(pos.x() - rect_coords[0]) < distance or
            abs(pos.x() - rect_coords[2]) < distance) and \
                (abs(pos.y() - rect_coords[1]) < distance or
                 abs(pos.y() - rect_coords[3]) < distance):
            return True, 0
        return False, 0

    def is_valid(self):
        return True

    def hoverEnterEvent(self, event):
        self.mouse_hoover = True
        self.setBrush(color_on_image_hoover)
        self.setPen(QtGui.QPen(QtGui.QColor("green"), self.pen_width))
        super(RectangleAnnotation, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.mouse_hoover = False
        self.setBrush(self.color)
        self.setPen(QtGui.QPen(self.color_no_Alpha, self.pen_width))
        super(RectangleAnnotation, self).hoverLeaveEvent(event)


class PointAnnotation(QtWidgets.QGraphicsEllipseItem):
    def __init__(self, parent=None, color=None, obj_id=0, image_id=0, object_type='', pen_width=12):
        super(PointAnnotation, self).__init__(parent)
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

        self.setPen(QtGui.QPen(self.color_no_Alpha, self.pen_width))
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

        if ellipse_rect.x() < 0 or ellipse_rect.y() < 0 or (ellipse_rect.x() + ellipse_rect.width() > image_width) or (
                ellipse_rect.y() + ellipse_rect.height()) > image_height:
            valid = False

        return [x, y, ellipse_rect.width() / 2.0], valid

    def close_point(self, pos, distance):

        ellipse_rect = self.rect()
        x = ellipse_rect.x() + ellipse_rect.width() / 2.0
        y = ellipse_rect.y() + ellipse_rect.height() / 2.0
        x = pos.x() - x
        y = pos.y() - y
        diff = math.sqrt(x ** 2 + y ** 2)
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
        self.setPen(QtGui.QPen(self.color_no_Alpha, self.pen_width))
        self.setBrush(self.color)

    def hoverEnterEvent(self, event):
        self.setBrush(color_on_image_hoover)
        self.setPen(QtGui.QPen(QtGui.QColor("green"), self.pen_width))
        super(PointAnnotation, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(self.color)
        self.setPen(QtGui.QPen(self.color_no_Alpha, self.pen_width))
        super(PointAnnotation, self).hoverLeaveEvent(event)


class PolygonAnnotation(QtWidgets.QGraphicsPolygonItem):
    def __init__(self, parent=None, color=None, obj_id=0, image_id=0, object_type='', pen_width=12):
        super(PolygonAnnotation, self).__init__(parent)
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

        self.setPen(QtGui.QPen(self.color_no_Alpha, self.pen_width))
        self.setBrush(self.color)

    def set_color(self, color):
        self.color = QtGui.QColor(color)
        self.color.setAlpha(0)
        self.color_no_Alpha = QtGui.QColor(color)
        self.color_no_Alpha.setAlpha(255)
        self.setPen(QtGui.QPen(self.color_no_Alpha, self.pen_width))
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
            poly.replace(target_point, pos)
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
        for idx, pt in enumerate(poly):
            dist = pt - pos
            dist = math.sqrt(dist.x() ** 2 + dist.y() ** 2)
            if dist < distance:
                return True, idx

        return False, 0

    def is_valid(self):
        p = self.polygon().toList()
        o = [[x.x(), x.y()] for x in p]
        i = geometry.Polygon(o)
        if i.is_valid:
            return True
        return False

    def hoverEnterEvent(self, event):
        self.setBrush(color_on_image_hoover)
        self.setPen(QtGui.QPen(QtGui.QColor("green"), self.pen_width))
        super(PolygonAnnotation, self).hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(self.color)
        self.setPen(QtGui.QPen(self.color_no_Alpha, self.pen_width))
        super(PolygonAnnotation, self).hoverLeaveEvent(event)
