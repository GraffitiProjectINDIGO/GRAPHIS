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

from PySide6 import QtWidgets
from PySide6.QtCore import Signal, QPointF, SignalInstance, Qt
from PySide6.QtGui import QPolygonF
from PySide6 import QtGui

from app.db_handler import DBHandler
from app.image_loader import image_loader
from app.var_classes import Instructions
from app.itemsGrahpicScene import RectangleAnnotation, PointAnnotation, PolygonAnnotation, OctoLines
from app.var_classes import create_region_boundary

point_size = 20


class DIGITIZERScene(QtWidgets.QGraphicsScene):
    object_att: SignalInstance = Signal(int)
    object_add: SignalInstance = Signal(int)
    change_object: SignalInstance = Signal(int)
    message_no_valid: SignalInstance = Signal()

    def __init__(self, parent=None):
        super(DIGITIZERScene, self).__init__(parent)

        self.current_instruction = Instructions.No_Instruction
        self.instruction_active = False
        self.hoover_over = True
        self.image_item = QtWidgets.QGraphicsPixmapItem()
        self.image_id_db = 0
        self.image_width = 0
        self.image_height = 0
        self.db = DBHandler()
        self.color_rectangle = None
        self.color_polygon = None
        self.color_circle = None
        self.change_point_index = -1
        self.old_cords = None
        self.active_item = None
        self.rectangle_item = None
        self.polygon_item = None
        self.circle_item = None
        self.p1_poly = None

    def delete_object(self, item_id):
        for item in self.items():
            if hasattr(item, 'obj_id'):
                if item.obj_id == item_id:
                    self.removeItem(item)

    def clear_image(self):

        if self.items():
            self.clear()
            self.instruction_active = False

        self.image_width = 0
        self.image_height = 0

    def open_image(self, filename):

        if self.items():
            self.clear()
            self.instruction_active = False

        self.image_item = QtWidgets.QGraphicsPixmapItem()
        self.image_item.setCursor(QtGui.QCursor(Qt.CrossCursor))
        self.addItem(self.image_item)

        pix_map = image_loader(filename)
        self.image_width = pix_map.width()
        self.image_height = pix_map.height()
        self.image_item.setPixmap(pix_map)
        self.setSceneRect(self.image_item.boundingRect())

    def change_image(self, pix_map: QtGui.QPixmap):

        if self.items():
            self.clear()
            self.instruction_active = False

        self.image_item = QtWidgets.QGraphicsPixmapItem()
        self.image_item.setCursor(QtGui.QCursor(Qt.CrossCursor))
        self.addItem(self.image_item)

        self.image_width = pix_map.width()
        self.image_height = pix_map.height()
        self.image_item.setPixmap(pix_map)
        self.setSceneRect(self.image_item.boundingRect())

    def hide_item(self, object_type=None):
        scene_items = self.items()

        for item in scene_items:
            if hasattr(item, 'object_type'):
                value = getattr(item, 'object_type')
                if value == object_type:
                    item.setVisible(not item.isVisible())

    def change_color(self, object_type=None, color=None):
        if color is not None:
            scene_items = self.items()

            for item in scene_items:
                if hasattr(item, 'object_type'):
                    value = getattr(item, 'object_type')
                    if value == object_type:
                        item.set_color(color)

    def change_color_id(self, object_id=None, color=None):
        if color is not None:
            scene_items = self.items()

            for item in scene_items:
                if hasattr(item, 'obj_id'):
                    value = getattr(item, 'obj_id')
                    if value == object_id:
                        item.set_color(color)

    def set_tooltip(self, object_id, text):
        scene_items = self.items()
        for item in scene_items:
            if hasattr(item, 'obj_id'):
                value = getattr(item, 'obj_id')
                if value == object_id:
                    item.setToolTip(text)

    def store_sightings(self, object_type, coordinates: list):

        if object_type == "rectangle":
            data = {'attributes': {}, 'coords': coordinates}
        elif object_type == "polygon":
            data = {'attributes': {}, 'coords': coordinates}
        elif object_type == "circle":
            data = {'attributes': {}, 'coords': coordinates}

        else:
            data = {}

        bound = create_region_boundary(self.image_width, self.image_height, object_type, coordinates)
        data['attributes']["RegionBoundary"] = bound
        object_id = self.db.db_store_object(self.image_id_db, object_type, data)

        tooltip = 'empty'
        self.object_add.emit(object_id)
        # self.current_instruction = Instructions.No_Instruction
        self.change_color(object_type='rectangle', color=self.color_rectangle)
        self.change_color(object_type='polygon', color=self.color_polygon)
        self.change_color(object_type='circle', color=self.color_circle)

        return object_id, tooltip

    def add_object(self, obj_type, data, obj_id, c1):

        region_id = data["attributes"].get("RId", '')

        if obj_type == "circle":
            circle_coordinates = data['coords']

            new_item = PointAnnotation(color=c1, obj_id=obj_id, object_type=obj_type)
            radius = circle_coordinates[2]
            new_item.setRect(circle_coordinates[0] - radius, circle_coordinates[1] - radius, radius * 2, radius * 2)
            new_item.setToolTip('RId:' + region_id)

        else:
            poly = data['coords']
            poly_image = QPolygonF()
            for p in poly:
                poly_image.append(QPointF(*p))
            new_item = PolygonAnnotation(color=c1, obj_id=obj_id, object_type=obj_type)
            new_item.setPolygon(QPolygonF(poly_image))

            new_item.setToolTip('RId:' + region_id)

        self.addItem(new_item)

    def mouseDoubleClickEvent(self, event):
        if not self.instruction_active and event.button() == Qt.LeftButton:
            current_item = self.items(event.scenePos())
            if self.image_item in current_item:
                current_item.remove(self.image_item)
                if current_item:
                    self.object_att.emit(current_item[0].obj_id)
                    self.change_color(object_type='rectangle', color=self.color_rectangle)
                    self.change_color(object_type='polygon', color=self.color_polygon)
                    self.change_color(object_type='circle', color=self.color_circle)
                    current_item[0].set_color(QtGui.QColor.fromRgbF(1.0, 1.00, 0.3, 0.588235))

    def mousePressEvent(self, event):

        current_item = self.items(event.scenePos())
        if self.image_item in current_item:

            # Remove image form items. Only geometries are left in current items
            current_item.remove(self.image_item)

            # -----------------------------------------------------------------------------------------------
            # STACK CHANGE
            if len(current_item) > 1 and not self.instruction_active and event.button() == Qt.MiddleButton:
                current_item[0].stackBefore(current_item[-1])

            # Move Instruction
            if self.current_instruction == Instructions.Move_Instruction and event.button() == Qt.RightButton:

                # start move instruction
                if len(current_item) >= 1:
                    if not self.instruction_active:
                        pos_scene = event.scenePos()
                        self.active_item = current_item[0]
                        self.old_cords = pos_scene
                        self.instruction_active = True
                    # finish move instruction
                    else:
                        coordinates, valid = self.active_item.get_coords(self.image_width, self.image_height)
                        if valid:
                            self.db.update_object(self.active_item.obj_id, coordinates)
                            self.change_object.emit(self.active_item.obj_id)
                            self.instruction_active = False

            # Add vertex
            if self.current_instruction == Instructions.Add_Vertex and event.button() == Qt.RightButton:
                if not self.instruction_active:

                    # create a octagon as to check intersection

                    pick_radius = (self.image_width + self.image_height) / 2.0 / 100
                    x, y = event.scenePos().x(), event.scenePos().y()
                    octo = OctoLines(x, y, pick_radius)
                    #for item_octo in octo.items():
                    #    self.addItem(QtWidgets.QGraphicsLineItem(item_octo))

                    for item in self.items():

                        if hasattr(item, 'object_type'):
                            if item.object_type == 'polygon':

                                found_near, id_item, inter_p = item.close_octo(octo)
                                if found_near:

                                    p: list = item.polygon().toList()
                                    p.insert(id_item+1, inter_p)
                                    item.setPolygon(QPolygonF(p))
                                    self.change_point_index = id_item+1
                                    self.active_item = item
                                    self.instruction_active = True
                                    break

                else:

                    if self.active_item.is_valid:
                        coordinates, valid = self.active_item.get_coords(self.image_width, self.image_height)
                        if valid:
                            self.db.update_object(self.active_item.obj_id, coordinates)
                            self.change_object.emit(self.active_item.obj_id)
                            self.instruction_active = False

            # Remove Vertex

            if self.current_instruction == Instructions.Remove_Vertex and event.button() == Qt.RightButton:
                if not self.instruction_active:

                    pick_radius = (self.image_width + self.image_height) / 2.0 / 100
                    for item in self.items():

                        if hasattr(item, 'object_type'):
                            if item.object_type == 'polygon':

                                found_near_geometry, idx_point = item.close_point(event.scenePos(), pick_radius)
                                if found_near_geometry:

                                    if item.polygon().length() > 3:

                                        p_del: QPolygonF = item.polygon()
                                        p_del.removeAt(idx_point)
                                        if item.is_valid():

                                            item.setPolygon(p_del)
                                            coordinates, valid = item.get_coords(self.image_width,
                                                                                 self.image_height)
                                            if valid:
                                                self.db.update_object(item.obj_id, coordinates)
                                                self.change_object.emit(item.obj_id)
                                            else:
                                                self.message_no_valid.emit()
                                        else:
                                            self.message_no_valid.emit()
                                    else:
                                        self.message_no_valid.emit()

                                    break

            if self.current_instruction == Instructions.Change_Instruction and event.button() == Qt.RightButton:

                if not self.instruction_active:

                    for item in self.items():
                        if hasattr(item, 'object_type'):

                            pick_radius = (self.image_width + self.image_height) / 2.0 / 100
                            found_near_geometry, idx_point = item.close_point(event.scenePos(), pick_radius)
                            if found_near_geometry:
                                self.change_point_index = idx_point
                                self.active_item = item
                                self.instruction_active = True
                                break

                else:

                    if self.active_item.is_valid:
                        coordinates, valid = self.active_item.get_coords(self.image_width, self.image_height)
                        if valid:
                            self.db.update_object(self.active_item.obj_id, coordinates)
                            self.change_object.emit(self.active_item.obj_id)
                            self.instruction_active = False

            # -----------------------------------------------------------------------------------------------
            # Drawing instructions

            # -----------------------------------------------------------------------------------------------
            # Rectangular, Polygon Picking starting - Circle Middle
            if not self.instruction_active:

                # Polygon
                if self.current_instruction == Instructions.Polygon_Instruction:
                    if event.button() == Qt.RightButton:
                        # starting point of polygon will be show
                        self.p1_poly = PointAnnotation(color=self.color_polygon, object_type='polygon')
                        self.addItem(self.p1_poly)
                        self.p1_poly.setRect(event.scenePos().x() - point_size / 2.0,
                                             event.scenePos().y() - point_size / 2.0,
                                             point_size, point_size)

                        self.polygon_item = PolygonAnnotation(color=self.color_polygon, object_type="polygon")
                        self.addItem(self.polygon_item)
                        self.instruction_active = True
                        self.polygon_item.setPolygon(QPolygonF())
                        poly = self.polygon_item.polygon()
                        poly.append(event.scenePos())
                        self.polygon_item.setPolygon(poly)

                # Rectangle
                if self.current_instruction == Instructions.Rectangle_Instruction:
                    if event.button() == Qt.RightButton:
                        self.rectangle_item = RectangleAnnotation(color=self.color_rectangle, object_type='rectangle')
                        self.addItem(self.rectangle_item)
                        self.rectangle_item.start_rectangle(event.scenePos())
                        self.instruction_active = True

                # Circle
                if self.current_instruction == Instructions.Circle_Instruction:
                    if event.button() == Qt.RightButton:
                        self.circle_item = PointAnnotation(color=self.color_circle, object_type='circle')
                        self.addItem(self.circle_item)
                        self.circle_item.setRect(event.scenePos().x(), event.scenePos().y(), 10, 10)
                        self.instruction_active = True

            # Continue with Polygon objects
            else:
                if self.current_instruction == Instructions.Polygon_Instruction:

                    # Finish polygon objects
                    if event.button() == Qt.LeftButton:

                        if self.polygon_item.polygon().length() > 2:

                            if self.polygon_item.is_valid():
                                self.instruction_active = False

                                coordinates, valid = self.polygon_item.get_coords(self.image_width, self.image_height)
                                # Check if last vertices are equal due to right and left click on same point
                                # If so delete last point from coordinates list submitted
                                diff_last2: QPointF = self.polygon_item.polygon()[-2] - self.polygon_item.polygon()[-1]
                                if diff_last2.manhattanLength() < 0.1:
                                    coordinates.pop()
                                self.polygon_item.obj_id, tooltip = self.store_sightings('polygon', coordinates)
                                self.polygon_item.setToolTip(tooltip)
                                self.change_color_id(self.polygon_item.obj_id,
                                                     QtGui.QColor.fromRgbF(1.0, 1.00, 0.3, 0.588235))
                            else:
                                self.removeItem(self.polygon_item)
                                self.message_no_valid.emit()
                            self.removeItem(self.p1_poly)
                        else:
                            self.message_no_valid.emit()
                            self.instruction_active = False
                            self.removeItem(self.p1_poly)
                            self.removeItem(self.polygon_item)

                    # Continue Polygon
                    elif event.button() == Qt.RightButton:
                        poly = self.polygon_item.polygon()

                        # Check if no vertic points are equal
                        if poly.length() < 3:
                            diff_to_last = poly[-1] - event.scenePos()
                        else:
                            diff_to_last = poly[-2] - event.scenePos()
                        if diff_to_last.manhattanLength() > 1.0:
                            poly.append(event.scenePos())
                            self.polygon_item.setPolygon(poly)

                # Finish Rectangle
                if self.current_instruction == Instructions.Rectangle_Instruction:
                    # Finish Rectangle
                    if event.button() == Qt.RightButton:

                        # rect = self.rectangle_item.rect().toRect()
                        coordinates, valid = self.rectangle_item.get_coords(self.image_width, self.image_height)

                        # Check if no rectangle with size 0 is created
                        if not self.rectangle_item.rect().isNull():
                            self.instruction_active = False
                            self.rectangle_item.obj_id, tooltip = self.store_sightings('rectangle', coordinates)
                            self.rectangle_item.setToolTip(tooltip)
                            self.change_color_id(self.rectangle_item.obj_id,
                                                 QtGui.QColor.fromRgbF(1.0, 1.00, 0.3, 0.588235))

                # Finish Circle
                elif self.current_instruction == Instructions.Circle_Instruction:
                    # Finish Rectangle
                    if event.button() == Qt.RightButton:

                        ellipse_rect = self.circle_item.rect()

                        x = ellipse_rect.x()
                        y = ellipse_rect.y()

                        if x > 0 and y > 0 and (x + ellipse_rect.width() < self.image_width) and \
                                (y + ellipse_rect.height()) < self.image_height:
                            self.instruction_active = False

                            # rect = self.rectangle_item.rect().toRect()
                            ellipse_rect = self.circle_item.rect()
                            x = ellipse_rect.x() + ellipse_rect.width() / 2.0
                            y = ellipse_rect.y() + ellipse_rect.height() / 2.0
                            radius = ellipse_rect.width() / 2.0
                            coordinates = [x, y, radius]
                            self.circle_item.obj_id, tooltip = self.store_sightings('circle', coordinates)
                            self.circle_item.setToolTip(tooltip)
                            self.change_color_id(self.circle_item.obj_id,
                                                 QtGui.QColor.fromRgbF(1.0, 1.00, 0.3, 0.588235))

        # -----------------------------------------------------------------------------------------------
        # Pass Event
        super(DIGITIZERScene, self).mousePressEvent(event)

    # -----------------------------------------------------------------------------------------------
    # If drawing is active for polygon or rectangle visually show the dynamic outlines
    def mouseMoveEvent(self, event):

        if self.current_instruction == Instructions.Change_Instruction and self.instruction_active:
            # poly = self.polygon_item.polygon()
            # if poly.length() > 2:
            #     poly.replace(self.change_point_index, event.scenePos())
            #	  self.polygon_item.setPolygon(poly)
            self.active_item.change_geometry(event.scenePos(), self.change_point_index)

        if self.current_instruction == Instructions.Add_Vertex and self.instruction_active:
            # poly = self.polygon_item.polygon()
            # if poly.length() > 2:
            #     poly.replace(self.change_point_index, event.scenePos())
            #	  self.polygon_item.setPolygon(poly)
            self.active_item.change_geometry(event.scenePos(), self.change_point_index)

        if self.current_instruction == Instructions.Move_Instruction and self.instruction_active:
            change_vector = event.scenePos() - self.old_cords
            self.active_item.move([change_vector.x(), change_vector.y()])
            self.old_cords = event.scenePos()

        current_item = self.items(event.scenePos())
        if self.image_item in current_item:
            if self.instruction_active:

                if self.current_instruction == Instructions.Polygon_Instruction:
                    poly = self.polygon_item.polygon()
                    if poly.length() > 2:
                        poly[poly.length() - 1] = event.scenePos()
                        self.polygon_item.setPolygon(poly)

                if self.current_instruction == Instructions.Rectangle_Instruction:
                    self.rectangle_item.resize_rectangle(event.scenePos())

                if self.current_instruction == Instructions.Circle_Instruction:
                    self.circle_item.set_radius_from_position(event.scenePos())
        super(DIGITIZERScene, self).mouseMoveEvent(event)
