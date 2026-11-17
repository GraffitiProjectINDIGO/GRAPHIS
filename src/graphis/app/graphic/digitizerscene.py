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
import logging
import math

import numpy as np
from PySide6 import QtGui, QtWidgets
from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QPolygonF

from graphis.app.graphic.geometry_smoothing import reduce_vertices, smooth_vertices
from graphis.app.graphic.itemsGrahpicScene import (
    CircleAnnotation,
    LineStringAnnotation,
    OctoLines,
    PointAnnotation,
    PolygonAnnotation,
    RectangleAnnotation,
)
from graphis.app.graphic.polygon_brush import brush_polygon_boundary
from graphis.app.ki import AISegmentationController
from graphis.app.var_classes import Instructions
from graphis.db.db_handler import DBHandler
from graphis.interface.image_loader import image_loader
from graphis.interface.imgregion_adapter import (
    base_object_type,
    create_region_boundary,
    pixel_coordinates_from_region,
    update_multigeometry_part_from_pixels,
)

logger = logging.getLogger(__name__)

point_size = 20
GeometryItem = RectangleAnnotation | CircleAnnotation | PolygonAnnotation | PointAnnotation | LineStringAnnotation


def _geometry_item(item) -> GeometryItem | None:
    if isinstance(
        item,
        (RectangleAnnotation, CircleAnnotation, PolygonAnnotation, PointAnnotation, LineStringAnnotation),
    ):
        return item
    return None


# Z order: image 0, AI pre-classification and mask directly above it, region geometries 10,
# AI prompt markers 40 and above so clicks and strokes stay visible.
AI_PRE_MASK_Z = 1
AI_MASK_Z = 2


class DIGITIZERScene(QtWidgets.QGraphicsScene):
    object_att = Signal(int)
    geometry_part_selected = Signal(int, int, int)
    object_deselected = Signal()
    object_add = Signal(int)
    change_object = Signal(int)
    message_no_valid = Signal(str)
    operationStateChanged = Signal(bool)
    selection_changed = Signal()
    aiBackgroundRequested = Signal(object)
    polygonBrushEnabledChanged = Signal(bool)
    smoothGeometryRequested = Signal()
    reduceVerticesRequested = Signal()
    populateContextMenuRequested = Signal(object, object)
    groupSelectionToggled = Signal(int)
    groupSelectionCleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_instruction = Instructions.No_Instruction
        self.instruction_active = False
        self.hoover_over = True
        self.image_item = QtWidgets.QGraphicsPixmapItem()
        self.image_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.image_id_db = 0
        self.image_width = 0
        self.image_height = 0
        self.db = DBHandler()
        self.color_rectangle = None
        self.color_polygon = None
        self.color_circle = None
        self.color_point = None
        self.color_linestring = None
        self.change_point_index = -1
        self.old_cords = None
        self.active_item = None
        self.group_selection_ids = set()
        self._suppress_context_menu = False
        self.rectangle_item = None
        self.polygon_item = None
        self.circle_item = None
        self.point_item = None
        self.line_item = None
        self.p1_poly = None
        self._operation_snapshot = None
        self._geometry_update_error = None
        self._geometry_assignment_target_id = None
        self.ai_controller = AISegmentationController()
        self.ai_mode_enabled = False
        self.ai_tool = "positive_point"
        self.ai_show_preclassification = False
        self._ai_prompt_items = []
        self._ai_mask_item = None
        self._ai_mask_color = QtGui.QColor(0, 120, 255)
        self._ai_mask_alpha = 130
        self._ai_current_mask = None
        self._ai_accumulated_mask = None
        self._ai_background_points = []
        self._ai_background_item = None
        self.ai_background_busy = False
        self._ai_pre_mask_item = None
        self._ai_keep_single_component = True
        self._ai_destructive_min_retention_ratio = 0.02
        self._ai_destructive_min_pixels = 32
        self._ai_rectangle_start = None
        self._ai_rectangle_item = None
        self.polygon_brush_enabled = False
        self.polygon_brush_mode = "expand"
        self.polygon_brush_size = 16
        self._polygon_brush_item = None
        self._polygon_brush_data = None
        self._polygon_brush_last_pos = None
        self._polygon_brush_changed = False

    def clear(self):
        self.set_polygon_brush_enabled(False)
        self.group_selection_ids.clear()
        super().clear()

    def polygon_brush_target(self):
        item = self.active_polygon_item()
        return item if item is not None and getattr(item, "geometry_ring_index", 0) == 0 else None

    def set_polygon_brush_enabled(self, enabled):
        enabled = bool(enabled and self.polygon_brush_target() is not None and not self.ai_mode_enabled)
        if not enabled and self._polygon_brush_item is not None:
            self.cancel_active_operation()
        if self.polygon_brush_enabled != enabled:
            self.polygon_brush_enabled = enabled
            self.polygonBrushEnabledChanged.emit(enabled)

    def set_polygon_brush_mode(self, mode):
        if mode in {"expand", "shrink"} and self._polygon_brush_item is None:
            self.polygon_brush_mode = mode

    def set_polygon_brush_size(self, size):
        if self._polygon_brush_item is None:
            self.polygon_brush_size = max(4, min(200, int(size)))

    def _apply_polygon_brush(self, pos):
        item = self._polygon_brush_item
        radius = self.polygon_brush_size / 2
        previous = self._polygon_brush_last_pos if self._polygon_brush_last_pos is not None else pos
        distance = math.hypot(pos.x() - previous.x(), pos.y() - previous.y())
        steps = min(128, max(1, math.ceil(distance / max(radius / 2, 1))))
        for step in range(1, steps + 1):
            center = previous + (pos - previous) * (step / steps)
            coordinates = brush_polygon_boundary(
                [[p.x(), p.y()] for p in item.polygon()], (center.x(), center.y()), radius,
                self.polygon_brush_mode, self.image_width, self.image_height,
            )
            if coordinates is None:
                continue
            part_index = getattr(item, "geometry_part_index", None)
            if part_index is not None:
                try:
                    # Validate against untouched holes and other parts before showing a preview.
                    update_multigeometry_part_from_pixels(
                        self._polygon_brush_data, self.image_width, self.image_height, part_index, coordinates
                    )
                except (IndexError, KeyError, TypeError, ValueError):
                    continue
            item.setPolygon(QPolygonF([QPointF(*point) for point in coordinates]))
            self._polygon_brush_changed = True
        self._polygon_brush_last_pos = QPointF(pos)

    def _handle_polygon_brush_press(self, event):
        if not self.polygon_brush_enabled:
            return False
        if event.button() == Qt.MouseButton.RightButton:
            self.set_polygon_brush_enabled(False)
        elif event.button() == Qt.MouseButton.LeftButton:
            item = self.polygon_brush_target()
            if item is None:
                return False
            row = self.db.db_load_object(item.obj_id)
            if row is None:
                return False
            self._polygon_brush_item = item
            self._polygon_brush_data = json.loads(row["data"])
            self._polygon_brush_last_pos = QPointF(event.scenePos())
            self._polygon_brush_changed = False
            self._begin_operation(item)
            self._apply_polygon_brush(event.scenePos())
        else:
            return False
        event.accept()
        return True

    def _handle_polygon_brush_release(self, event):
        if self._polygon_brush_item is None or event.button() != Qt.MouseButton.LeftButton:
            return False
        self._apply_polygon_brush(event.scenePos())
        item = self._polygon_brush_item
        original = QPolygonF(self._operation_snapshot[2])
        changed = self._polygon_brush_changed and item.polygon() != original
        coordinates, valid = item.get_coords(self.image_width, self.image_height)
        self._polygon_brush_item = None
        self._polygon_brush_data = None
        self._polygon_brush_last_pos = None
        self._finish_operation()
        if changed:
            label = f"{'Expand' if self.polygon_brush_mode == 'expand' else 'Shrink'} polygon border"
            if not valid or not self._commit_geometry_update(item, coordinates, label):
                item.setPolygon(original)
                self._emit_no_valid(item)
            self.set_polygon_brush_enabled(True)
        event.accept()
        return True

    def delete_object(self, item_id):
        for item in self.items():
            geometry_item = _geometry_item(item)
            if geometry_item is not None and geometry_item.obj_id == item_id:
                if geometry_item is self.active_item:
                    self.active_item = None
                self.removeItem(geometry_item)
                self.selection_changed.emit()

    def clear_image(self):

        if self.items():
            self.clear()
            self._operation_snapshot = None
            self._set_instruction_active(False)
            self.active_item = None
            self.selection_changed.emit()
            self._clear_ai_overlay_references()

        self.image_width = 0
        self.image_height = 0
        self.reset_ai_segmentation(reload_backend=False)

    def open_image(self, filename):

        if self.items():
            self.clear()
            self._operation_snapshot = None
            self._set_instruction_active(False)
            self.active_item = None
            self.selection_changed.emit()
            self._clear_ai_overlay_references()

        self.image_item = self._create_image_item()
        self.image_item.setCursor(QtGui.QCursor(Qt.CursorShape.CrossCursor))
        self.addItem(self.image_item)

        image = image_loader(filename)
        self.image_width = image.width()
        self.image_height = image.height()
        self.image_item.setPixmap(QtGui.QPixmap.fromImage(image))
        self.setSceneRect(self.image_item.boundingRect())
        self.ai_controller.set_image(image)

    def change_image(self, image: QtGui.QImage):

        if self.items():
            self.clear()
            self._operation_snapshot = None
            self._set_instruction_active(False)
            self.active_item = None
            self.selection_changed.emit()
            self._clear_ai_overlay_references()

        self.image_item = self._create_image_item()
        self.image_item.setCursor(QtGui.QCursor(Qt.CursorShape.CrossCursor))
        self.addItem(self.image_item)

        self.image_width = image.width()
        self.image_height = image.height()
        self.image_item.setPixmap(QtGui.QPixmap.fromImage(image))
        self.setSceneRect(self.image_item.boundingRect())
        self.ai_controller.set_image(image)

    def _create_image_item(self):
        item = QtWidgets.QGraphicsPixmapItem()
        item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        return item

    def hide_item(self, object_type=None):
        object_type = base_object_type(object_type)
        for item in self.items():
            geometry_item = _geometry_item(item)
            if geometry_item is not None and base_object_type(geometry_item.object_type) == object_type:
                geometry_item.setVisible(not geometry_item.isVisible())

    def set_item_visibility(self, object_type=None, visible=True):
        scene_items = self.items()
        object_type = base_object_type(object_type)

        for item in scene_items:
            geometry_item = _geometry_item(item)
            if geometry_item is not None and base_object_type(geometry_item.object_type) == object_type:
                geometry_item.setVisible(visible)

    def change_color(self, object_type=None, color=None):
        if color is not None:
            scene_items = self.items()
            object_type = base_object_type(object_type)

            for item in scene_items:
                geometry_item = _geometry_item(item)
                if geometry_item is not None and base_object_type(geometry_item.object_type) == object_type:
                    geometry_item.set_color(color)

    def change_color_id(self, object_id=None, color=None):
        if color is not None:
            scene_items = self.items()

            for item in scene_items:
                geometry_item = _geometry_item(item)
                if geometry_item is not None and geometry_item.obj_id == object_id:
                    geometry_item.set_color(color)

    def activate_object(self, object_id):
        self.clear_active_object()
        found = False
        for item in self.items():
            geometry_item = _geometry_item(item)
            if geometry_item is not None and geometry_item.obj_id == object_id:
                found = True
                geometry_item.show_vertices = True
                geometry_item.set_color(QtGui.QColor.fromRgbF(1.0, 1.00, 0.3, 0.588235))
                if getattr(geometry_item, "geometry_part_index", None) is not None:
                    continue
                self.active_item = geometry_item
                self.set_group_selection(self.group_selection_ids)
                self.update()
                self.selection_changed.emit()
                return True

        self.active_item = None
        self.set_group_selection(self.group_selection_ids)
        self.update()
        self.selection_changed.emit()
        return found

    def active_object_center(self):
        if self.active_item is None:
            return None
        return self.active_item.sceneBoundingRect().center()

    def activate_geometry_part(self, object_id, part_index, ring_index=0):
        self.clear_active_object()
        for item in self.items():
            if (
                getattr(item, "obj_id", None) == object_id
                and getattr(item, "geometry_part_index", None) == part_index
                and getattr(item, "geometry_ring_index", 0) == ring_index
            ):
                self.active_item = item
                item.show_vertices = True
                item.set_color(QtGui.QColor.fromRgbF(1.0, 1.00, 0.3, 0.588235))
                self.set_group_selection(self.group_selection_ids)
                self.update()
                self.selection_changed.emit()
                return True
        return False

    def active_geometry_item(self):
        if self.active_item is None:
            return None
        if self.active_item.scene() is not self:
            self.active_item = None
            return None
        if not hasattr(self.active_item, "object_type"):
            return None
        return self.active_item

    def active_polygon_item(self):
        item = self.active_geometry_item()
        if item is None:
            return None
        if getattr(item, "object_type", None) != "polygon":
            return None
        return item

    def active_point_edit_item(self):
        item = self.active_geometry_item()
        if item is None:
            return None
        if getattr(item, "object_type", None) not in {"polygon", "linestring"}:
            return None
        return item

    def clear_current_operation(self):
        if self._polygon_brush_item is not None:
            self._restore_operation_snapshot()
            self._polygon_brush_item = None
            self._polygon_brush_data = None
            self._polygon_brush_last_pos = None
        self.set_polygon_brush_enabled(False)
        self._operation_snapshot = None
        self._geometry_update_error = None
        self.change_point_index = -1
        self.old_cords = None
        self.current_instruction = Instructions.No_Instruction
        self.clear_geometry_assignment_target()
        self._set_instruction_active(False)

    def cancel_active_operation(self):
        if not self.instruction_active:
            return False

        self._restore_operation_snapshot()
        self._remove_temporary_create_items()
        self.clear_current_operation()
        return True

    def _set_instruction_active(self, active):
        if self.instruction_active == active:
            return
        self.instruction_active = active
        self.operationStateChanged.emit(active)

    def _begin_operation(self, item=None):
        self._geometry_update_error = None
        self._operation_snapshot = self._snapshot_item_geometry(item)
        self._set_instruction_active(True)

    def _finish_operation(self):
        self._operation_snapshot = None
        self.change_point_index = -1
        self.old_cords = None
        self._set_instruction_active(False)

    def _snapshot_item_geometry(self, item):
        if item is None:
            return None
        if isinstance(item, LineStringAnnotation):
            return item, "linestring", QPolygonF(item.points())
        if hasattr(item, "polygon"):
            return item, "polygon", QPolygonF(item.polygon())
        if hasattr(item, "rect"):
            return item, "rect", QRectF(item.rect())
        return None

    def _restore_operation_snapshot(self):
        if self._operation_snapshot is None:
            return
        item, geometry_type, geometry_value = self._operation_snapshot
        if item.scene() is not self:
            return
        if geometry_type == "polygon":
            item.setPolygon(QPolygonF(geometry_value))
        elif geometry_type == "linestring":
            item.set_points(QPolygonF(geometry_value))
        elif geometry_type == "rect":
            item.setRect(QRectF(geometry_value))

    def _remove_temporary_create_items(self):
        for item in (
            self.p1_poly,
            self.polygon_item,
            self.rectangle_item,
            self.circle_item,
            self.point_item,
            self.line_item,
        ):
            if item is not None and item.scene() is self and getattr(item, "obj_id", 0) == 0:
                self.removeItem(item)
        self.p1_poly = None
        self.polygon_item = None
        self.rectangle_item = None
        self.circle_item = None
        self.point_item = None
        self.line_item = None

    def clear_active_object(self):
        self.set_polygon_brush_enabled(False)
        for item in self.items():
            if getattr(item, "show_vertices", False):
                item.show_vertices = False
        self.change_color(object_type="rectangle", color=self.color_rectangle)
        self.change_color(object_type="polygon", color=self.color_polygon)
        self.change_color(object_type="circle", color=self.color_circle)
        self.change_color(object_type="point", color=self.color_point)
        self.change_color(object_type="linestring", color=self.color_linestring)
        self.active_item = None
        self.set_group_selection(self.group_selection_ids)
        self.update()
        self.selection_changed.emit()

    def set_group_selection(self, object_ids):
        self.group_selection_ids = {int(object_id) for object_id in object_ids}
        for item in self.items():
            geometry_item = _geometry_item(item)
            if geometry_item is None:
                continue
            was_selected = getattr(geometry_item, "group_selected", False)
            selected = geometry_item.obj_id in self.group_selection_ids
            geometry_item.group_selected = selected
            if selected:
                geometry_item.set_color(QtGui.QColor("#66e5ff"))
            elif was_selected:
                color = (
                    QtGui.QColor.fromRgbF(1.0, 1.00, 0.3, 0.588235)
                    if getattr(geometry_item, "show_vertices", False)
                    else getattr(self, f"color_{geometry_item.object_type}", None)
                )
                if color is not None:
                    geometry_item.set_color(color)
        self.update()

    def selected_vertex_points(self):
        """Scene positions of visible vertices, including selected multi-geometry parts."""
        for item in self.items():
            if (
                not (getattr(item, "show_vertices", False) or getattr(item, "group_selected", False))
                or not item.isVisible()
                or getattr(item, "object_type", None) not in {"polygon", "linestring"}
            ):
                continue
            points = list(item.polygon())
            if len(points) > 1 and points[0] == points[-1]:
                points.pop()
            for point in points:
                yield item.mapToScene(point)

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        # Draw in viewport coordinates so crosses stay small at every zoom level.
        transform = painter.worldTransform()
        lines = []
        for point in self.selected_vertex_points():
            if not rect.contains(point):
                continue
            center = transform.map(point)
            lines.extend([
                QLineF(center + QPointF(-3, -3), center + QPointF(3, 3)),
                QLineF(center + QPointF(-3, 3), center + QPointF(3, -3)),
            ])
        if not lines:
            return
        painter.save()
        painter.resetTransform()
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        for color, width in (("#202832", 3), ("#ffff4d", 1)):
            pen = QtGui.QPen(QtGui.QColor(color), width)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.drawLines(lines)
        painter.restore()

    def set_tooltip(self, object_id, text):
        scene_items = self.items()
        for item in scene_items:
            geometry_item = _geometry_item(item)
            if geometry_item is not None and geometry_item.obj_id == object_id:
                geometry_item.setToolTip(text)

    def set_geometry_assignment_target(self, object_id):
        self._geometry_assignment_target_id = object_id

    def clear_geometry_assignment_target(self):
        self._geometry_assignment_target_id = None

    def store_sightings(self, object_type, coordinates: list):
        bound = create_region_boundary(self.image_width, self.image_height, object_type, coordinates)
        target_object_id = self._geometry_assignment_target_id
        if target_object_id is not None:
            target_object_id = int(target_object_id)
            obj = self.db.db_load_object(target_object_id)
            if obj is not None:
                try:
                    data = json.loads(obj["data"])
                except (TypeError, json.JSONDecodeError):
                    data = {}

                replacing = "regionBoundary" in data
                data["regionBoundary"] = bound
                label = f"{'Replace' if replacing else 'Assign'} {object_type} geometry"
                self.db.begin_undo_group(label)
                try:
                    self.delete_object(target_object_id)
                    self.db.update_object(
                        target_object_id,
                        data=data,
                        object_type=object_type,
                        log_validation=False,
                        action_label=label,
                    )
                    tooltip = "empty"
                    self.change_object.emit(target_object_id)
                finally:
                    self.db.end_undo_group()
                    self.clear_geometry_assignment_target()

                self.change_color(object_type="rectangle", color=self.color_rectangle)
                self.change_color(object_type="polygon", color=self.color_polygon)
                self.change_color(object_type="circle", color=self.color_circle)
                self.change_color(object_type="point", color=self.color_point)
                self.change_color(object_type="linestring", color=self.color_linestring)
                return target_object_id, tooltip

            self.clear_geometry_assignment_target()

        data = {"regionBoundary": bound}
        self.db.begin_undo_group(f"Create {object_type}")
        try:
            object_id = self.db.db_store_object(self.image_id_db, object_type, data)

            tooltip = "empty"
            self.object_add.emit(object_id)
        finally:
            self.db.end_undo_group()
        # self.current_instruction = Instructions.No_Instruction
        self.change_color(object_type="rectangle", color=self.color_rectangle)
        self.change_color(object_type="polygon", color=self.color_polygon)
        self.change_color(object_type="circle", color=self.color_circle)
        self.change_color(object_type="point", color=self.color_point)
        self.change_color(object_type="linestring", color=self.color_linestring)

        return object_id, tooltip

    def _commit_geometry_update(self, item, coordinates, label):
        self._geometry_update_error = None
        self.db.begin_undo_group(label)
        try:
            part_index = getattr(item, "geometry_part_index", None)
            if part_index is None:
                self.db.update_object(item.obj_id, coordinates)
            else:
                row = self.db.db_load_object(item.obj_id)
                data = update_multigeometry_part_from_pixels(
                    json.loads(row["data"]),
                    self.image_width,
                    self.image_height,
                    part_index,
                    coordinates,
                    ring_index=getattr(item, "geometry_ring_index", 0),
                    move_polygon=label == "Move geometry",
                )
                self.db.update_object(item.obj_id, data=data, action_label=label)
            self.change_object.emit(item.obj_id)
            return True
        except (IndexError, KeyError, TypeError, ValueError) as err:
            self._geometry_update_error = f"Cannot update geometry: {err}"
            logger.warning("Cannot update geometry: %s", err)
            return False
        finally:
            self.db.end_undo_group()

    def smooth_geometry_target(self):
        item = self.active_geometry_item()
        if (
            item is None or item.object_type not in {"polygon", "linestring"}
            or not item.isVisible() or self.instruction_active or self.ai_mode_enabled
            or self.current_instruction != Instructions.No_Instruction
            or len(self.group_selection_ids) > 1
        ):
            return None
        return item

    def contextMenuEvent(self, event):
        if (
            self._suppress_context_menu or self.instruction_active or self.ai_mode_enabled
            or self.polygon_brush_enabled or self.current_instruction != Instructions.No_Instruction
        ):
            self._suppress_context_menu = False
            event.accept()
            return
        item = next((_geometry_item(hit) for hit in self.items(event.scenePos()) if _geometry_item(hit)), None)
        if item is None:
            item = self.active_geometry_item()
        if item is None:
            item = next((hit for hit in self.items() if (
                getattr(hit, "show_vertices", False) or getattr(hit, "group_selected", False)
            )), None)
        if item is None:
            super().contextMenuEvent(event)
            return
        menu = QtWidgets.QMenu(event.widget())
        self.populateContextMenuRequested.emit(menu, item)
        action = reduce_action = None
        if self.smooth_geometry_target() is item:
            if menu.actions():
                menu.addSeparator()
            action = menu.addAction("Smooth")
            action.setToolTip("Round corners of the selected geometry; keep line endpoints fixed")
            reduce_action = menu.addAction("Reduce vertices (10%)")
            reduce_action.setToolTip("Remove approximately 10% of vertices; keep line endpoints fixed")
        if not menu.actions():
            event.accept()
            return
        selected = menu.exec(event.screenPos())
        if action is not None and selected == action:
            self.smoothGeometryRequested.emit()
        elif reduce_action is not None and selected == reduce_action:
            self.reduceVerticesRequested.emit()
        event.accept()

    def smooth_selected_geometry(self):
        return self._modify_selected_vertices(smooth_vertices, "Smooth geometry")

    def reduce_selected_vertices(self):
        return self._modify_selected_vertices(reduce_vertices, "Reduce vertices (10%)")

    def _modify_selected_vertices(self, operation, label):
        item = self.smooth_geometry_target()
        if item is None:
            return False
        original = QPolygonF(item.polygon())
        try:
            coordinates = operation([[p.x(), p.y()] for p in original], item.object_type == "polygon")
        except ValueError as err:
            logger.warning("%s failed: %s", label, err)
            return False
        polygon = QPolygonF([QPointF(*point) for point in coordinates])
        if polygon == original:
            return False
        item.setPolygon(polygon)
        if not self._commit_geometry_update(item, coordinates, label):
            item.setPolygon(original)
            logger.warning("%s was not applied: %s", label, self._geometry_update_error)
            return False
        self.update()
        return True

    def _invalid_geometry_message(self, item=None):
        if item is None and self._operation_snapshot is not None:
            item = self._operation_snapshot[0]
        if item is None:
            item = self.active_geometry_item()

        object_type = getattr(item, "object_type", None)
        if object_type is None and self.current_instruction == Instructions.Linestring_Instruction:
            object_type = "linestring"
        elif object_type is None and self.current_instruction == Instructions.Polygon_Instruction:
            object_type = "polygon"

        if object_type == "linestring":
            return "That was or will not be a valid linestring. It needs at least two distinct points inside the image."
        if object_type == "polygon":
            return "That was or will not be a valid polygon. Either not enough points (min 3) or self intersecting."
        return "That was or will not be a valid geometry."

    def _emit_no_valid(self, item=None, message=None):
        message = message or self._geometry_update_error or self._invalid_geometry_message(item)
        self._geometry_update_error = None
        self.message_no_valid.emit(message)

    def _reject_active_geometry_operation(self):
        item = self._operation_snapshot[0] if self._operation_snapshot is not None else None
        message = self._geometry_update_error
        self._restore_operation_snapshot()
        self.clear_current_operation()
        self._emit_no_valid(item, message=message)

    def add_object(self, obj_type, data, obj_id, c1, geometry=None):
        """Draw a region. ``geometry`` is the already parsed ``(shape, pixel coordinates)``, if available."""
        if geometry is not None:
            obj_type, coordinates = geometry
        else:
            try:
                obj_type, coordinates = pixel_coordinates_from_region(data, self.image_width, self.image_height)
            except (KeyError, TypeError, ValueError) as err:
                logger.warning("Cannot draw malformed Image Region object %s: %s", obj_id, err)
                return

        region_id = data.get("rId", "")

        if obj_type == "circle":
            circle_coordinates = coordinates

            new_item = CircleAnnotation(color=c1, obj_id=obj_id, object_type=obj_type)
            radius = circle_coordinates[2]
            new_item.setRect(circle_coordinates[0] - radius, circle_coordinates[1] - radius, radius * 2, radius * 2)
            new_item.setToolTip("RId:" + region_id)
            self.addItem(new_item)

        elif obj_type == "point":
            new_item = PointAnnotation(color=c1, obj_id=obj_id, object_type=obj_type)
            new_item.set_point(coordinates[0], coordinates[1])
            new_item.setToolTip("RId:" + region_id)
            self.addItem(new_item)

        elif obj_type == "multipoint":
            for index, point in enumerate(coordinates):
                new_item = PointAnnotation(color=c1, obj_id=obj_id, object_type="point")
                new_item.geometry_part_index = index
                new_item.set_point(point[0], point[1])
                new_item.setToolTip("RId:" + region_id)
                self.addItem(new_item)

        elif obj_type == "linestring":
            new_item = LineStringAnnotation(color=c1, obj_id=obj_id, object_type=obj_type)
            new_item.set_points(coordinates)
            new_item.setToolTip("RId:" + region_id)
            self.addItem(new_item)

        elif obj_type == "multilinestring":
            for index, line in enumerate(coordinates):
                new_item = LineStringAnnotation(color=c1, obj_id=obj_id, object_type="linestring")
                new_item.geometry_part_index = index
                new_item.set_points(line)
                new_item.setToolTip("RId:" + region_id)
                self.addItem(new_item)

        elif obj_type == "multipolygon":
            for index, polygon in enumerate(coordinates):
                self._add_polygon_rings(polygon, obj_id, "polygon", c1, region_id, part_index=index)

        else:
            rings = coordinates if coordinates and isinstance(coordinates[0][0], list) else [coordinates]
            self._add_polygon_rings(rings, obj_id, obj_type, c1, region_id, part_index=0 if len(rings) > 1 else None)

    def _add_polygon_rings(self, rings, obj_id, obj_type, color, region_id, part_index=None):
        for ring_index, ring in enumerate(rings):
            if part_index is not None and len(ring) > 1 and ring[0] == ring[-1]:
                ring = ring[:-1]
            poly_image = QPolygonF()
            for p in ring:
                poly_image.append(QPointF(*p))
            new_item = PolygonAnnotation(color=color, obj_id=obj_id, object_type=obj_type)
            if part_index is not None:
                new_item.geometry_part_index = part_index
                new_item.geometry_ring_index = ring_index
                new_item.setPen(new_item.pen())
            new_item.setPolygon(QPolygonF(poly_image))
            new_item.setToolTip("RId:" + region_id)
            self.addItem(new_item)

    def set_ai_mode_enabled(self, enabled):
        if enabled:
            self.set_polygon_brush_enabled(False)
        self._clear_ai_background()
        self.ai_mode_enabled = bool(enabled)
        if self.ai_mode_enabled:
            self.clear_current_operation()
            self.clear_active_object()

    def set_ai_tool(self, tool):
        if tool in {"positive_point", "negative_point", "rectangle", "background"}:
            self.ai_tool = tool
        self._clear_ai_background()
        self._clear_ai_rectangle_prompt()

    def set_ai_preclassification_visible(self, visible):
        self.ai_show_preclassification = bool(visible)
        if self.ai_show_preclassification:
            self._update_ai_pre_masks()
        else:
            self._remove_ai_pre_mask()

    def set_ai_mask_color(self, color):
        if not isinstance(color, QtGui.QColor) or not color.isValid():
            return
        self._ai_mask_color = QtGui.QColor(color)
        if self._ai_current_mask is not None:
            self._set_ai_display_mask(self._ai_current_mask)

    def _clear_ai_overlay_references(self):
        self._ai_background_item = None
        self._ai_background_points = []
        self._ai_prompt_items.clear()
        self._ai_mask_item = None
        self._ai_current_mask = None
        self._ai_accumulated_mask = None
        self._ai_pre_mask_item = None
        self._clear_ai_rectangle_prompt()

    def reset_ai_segmentation(self, reload_backend=True):
        self._clear_ai_background()
        self.ai_controller.reset(reload_image=reload_backend)
        self._clear_ai_rectangle_prompt()
        for item in list(self._ai_prompt_items):
            try:
                in_scene = item.scene() is self
            except RuntimeError:
                in_scene = False
            if in_scene:
                self.removeItem(item)
        self._ai_prompt_items.clear()
        if self._ai_mask_item is not None:
            try:
                if self._ai_mask_item.scene() is self:
                    self.removeItem(self._ai_mask_item)
            except RuntimeError:
                pass
        self._ai_mask_item = None
        self._ai_current_mask = None
        self._ai_accumulated_mask = None
        self._remove_ai_pre_mask()

    def _handle_ai_mouse_press(self, event):
        if self.ai_background_busy:
            event.accept()
            return True
        if not self.ai_mode_enabled or not self._event_on_image(event):
            return False

        if self.ai_tool == "background":
            if event.button() == Qt.MouseButton.LeftButton:
                if self._ai_current_mask is None:
                    self.message_no_valid.emit("Create an AI mask before painting background.")
                    event.accept()
                    return True
                self._clear_ai_background()
                self._ai_background_points = [event.scenePos()]
                pen = QtGui.QPen(QtGui.QColor(240, 65, 65, 180), 12)
                pen.setCosmetic(True)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                self._ai_background_item = self.addPath(QtGui.QPainterPath(event.scenePos()), pen)
                self._ai_background_item.setZValue(41)
            elif event.button() == Qt.MouseButton.RightButton:
                self._clear_ai_background()
            event.accept()
            return True

        if self.ai_tool == "rectangle":
            if event.button() != Qt.MouseButton.LeftButton:
                return False
            self._start_ai_rectangle_prompt(event.scenePos())
            event.accept()
            return True

        if event.button() == Qt.MouseButton.LeftButton:
            label = 0 if self.ai_tool == "negative_point" else 1
        elif event.button() == Qt.MouseButton.RightButton:
            label = 0
        else:
            return False

        self._add_ai_prompt(event.scenePos(), label)
        event.accept()
        return True

    def _handle_ai_mouse_move(self, event):
        if self.ai_background_busy:
            event.accept()
            return True
        if self.ai_mode_enabled and self.ai_tool == "background" and self._ai_background_item is not None:
            self._extend_ai_background(event.scenePos())
            event.accept()
            return True
        if self.ai_mode_enabled and self.ai_tool == "rectangle" and self._ai_rectangle_item is not None:
            self._update_ai_rectangle_prompt(event.scenePos())
            event.accept()
            return True

        return False

    def _handle_ai_mouse_release(self, event):
        if self.ai_background_busy:
            event.accept()
            return True
        if self.ai_mode_enabled and self.ai_tool == "background" and self._ai_background_item is not None:
            self._extend_ai_background(event.scenePos())
            coordinates = [[p.x(), p.y()] for p in self._ai_background_points]
            self._clear_ai_background()
            if coordinates:
                self.aiBackgroundRequested.emit(coordinates)
            event.accept()
            return True
        if self.ai_mode_enabled and self.ai_tool == "rectangle" and self._ai_rectangle_item is not None:
            self._finish_ai_rectangle_prompt(event.scenePos())
            event.accept()
            return True

        return False

    def _event_on_image(self, event):
        if self.image_width <= 0 or self.image_height <= 0:
            return False
        pos = event.scenePos()
        return 0 <= pos.x() < self.image_width and 0 <= pos.y() < self.image_height

    def _clear_ai_background(self):
        if self._ai_background_item is not None and self._ai_background_item.scene() is self:
            self.removeItem(self._ai_background_item)
        self._ai_background_item = None
        self._ai_background_points = []

    def _extend_ai_background(self, pos):
        point = QPointF(
            max(0.0, min(pos.x(), self.image_width - 1.0)),
            max(0.0, min(pos.y(), self.image_height - 1.0)),
        )
        # Sample in display pixels so drawing stays responsive at any image resolution.
        last = self._ai_background_points[-1]
        views = self.views()
        scale = abs(views[0].transform().m11()) if views else 1.0
        delta = point - last
        if (delta.x() ** 2 + delta.y() ** 2) * scale**2 < 9:
            return
        self._ai_background_points.append(point)
        path = self._ai_background_item.path()
        # Qt can discard the initial move-only path when storing an empty graphics item.
        if path.isEmpty():
            path.moveTo(last)
        path.lineTo(point)
        self._ai_background_item.setPath(path)

    def _add_ai_prompt(self, pos, label):
        prompt_state = self.ai_controller.prompt_state()
        try:
            mask = self.ai_controller.add_point(pos.x(), pos.y(), label)
        except Exception as err:
            logger.exception("KI segmentation failed: %s", err)
            return
        if label == 0 and mask is not None and not self._accept_ai_mask_update(mask, destructive=True):
            self.ai_controller.restore_prompt_state(prompt_state)
            return
        self._draw_ai_prompt_marker(pos, label)
        if mask is not None:
            self._draw_ai_mask(mask)


    def _start_ai_rectangle_prompt(self, pos):
        self._clear_ai_rectangle_prompt()
        self._ai_rectangle_start = pos
        pen = QtGui.QPen(QtGui.QColor(70, 190, 255), 2)
        pen.setCosmetic(True)
        self._ai_rectangle_item = self.addRect(QRectF(pos, pos), pen)
        self._ai_rectangle_item.setZValue(41)

    def _update_ai_rectangle_prompt(self, pos):
        if self._ai_rectangle_item is None or self._ai_rectangle_start is None:
            return
        self._ai_rectangle_item.setRect(QRectF(self._ai_rectangle_start, pos).normalized())

    def _finish_ai_rectangle_prompt(self, pos):
        if self._ai_rectangle_start is None:
            self._clear_ai_rectangle_prompt()
            return
        end_pos = QPointF(
            max(0.0, min(pos.x(), float(self.image_width - 1))),
            max(0.0, min(pos.y(), float(self.image_height - 1))),
        )
        rect = QRectF(self._ai_rectangle_start, end_pos).normalized()
        self._clear_ai_rectangle_prompt()
        if rect.width() < 2 or rect.height() < 2:
            return
        try:
            mask = self.ai_controller.predict_box(
                (
                    rect.left(),
                    rect.top(),
                    rect.right(),
                    rect.bottom(),
                )
            )
        except Exception as err:
            logger.exception("KI rectangle segmentation failed: %s", err)
            return
        if mask is not None:
            # Freeze the displayed selection; subsequent point prompts refine only this new box.
            self._ai_accumulated_mask = None if self._ai_current_mask is None else self._ai_current_mask.copy()
            self._remove_ai_prompt_items_from(0)
            self._draw_ai_mask(mask)

    def _clear_ai_rectangle_prompt(self):
        self._ai_rectangle_start = None
        if self._ai_rectangle_item is not None:
            try:
                if self._ai_rectangle_item.scene() is self:
                    self.removeItem(self._ai_rectangle_item)
            except RuntimeError:
                pass
        self._ai_rectangle_item = None

    def _draw_ai_prompt_marker(self, pos, label):
        color = QtGui.QColor(45, 220, 120) if label == 1 else QtGui.QColor(235, 80, 70)
        pen = QtGui.QPen(color, 2)
        pen.setCosmetic(True)
        marker = self.addEllipse(pos.x() - 4, pos.y() - 4, 8, 8, pen, color)
        marker.setZValue(40)
        self._ai_prompt_items.append(marker)

    def _remove_ai_prompt_items_from(self, start_index):
        for item in self._ai_prompt_items[start_index:]:
            try:
                if item.scene() is self:
                    self.removeItem(item)
            except RuntimeError:
                pass
        del self._ai_prompt_items[start_index:]

    def _accept_ai_mask_update(self, mask, destructive):
        if not destructive or self._ai_current_mask is None:
            return True

        new_mask = np.asarray(mask, dtype=bool)
        if self._ai_accumulated_mask is not None and self._ai_accumulated_mask.shape == new_mask.shape:
            new_mask = new_mask | self._ai_accumulated_mask
        old_mask = np.asarray(self._ai_current_mask, dtype=bool)
        old_pixels = int(np.count_nonzero(old_mask))
        if old_pixels <= 0:
            return True

        new_pixels = int(np.count_nonzero(new_mask))
        minimum_pixels = max(
            self._ai_destructive_min_pixels,
            int(old_pixels * self._ai_destructive_min_retention_ratio),
        )
        if new_pixels >= minimum_pixels:
            return True

        logger.warning(
            "Rejected AI correction because it reduced the mask from %s pixels to %s pixels.",
            old_pixels,
            new_pixels,
        )
        return False




    def _draw_ai_mask(self, mask):
        mask = np.asarray(mask, dtype=bool)
        if mask.ndim != 2:
            logger.warning("AI segmenter returned a non-2D mask.")
            return

        mask = self._clean_ai_mask(mask)
        if self._ai_accumulated_mask is not None and self._ai_accumulated_mask.shape == mask.shape:
            mask = mask | self._ai_accumulated_mask
        self._set_ai_display_mask(mask)

    def _clean_ai_mask(self, mask):
        mask = np.asarray(mask, dtype=bool)
        if not self._ai_keep_single_component or not np.any(mask):
            return mask

        try:
            import cv2
        except ImportError:
            logger.warning("OpenCV is not available; AI mask component cleanup was skipped.")
            return mask

        component_count, labels, stats, _centroids = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
        if component_count <= 2:
            return mask

        areas = stats[1:, cv2.CC_STAT_AREA]
        largest_label = int(np.argmax(areas)) + 1
        return labels == largest_label

    def _set_ai_display_mask(self, mask):
        mask = np.asarray(mask, dtype=bool)
        self._ai_current_mask = mask.copy()
        height, width = mask.shape
        rgba = np.zeros((height, width, 4), dtype=np.uint8)
        rgba[mask] = [
            self._ai_mask_color.red(),
            self._ai_mask_color.green(),
            self._ai_mask_color.blue(),
            self._ai_mask_alpha,
        ]
        image = QtGui.QImage(rgba.data, width, height, width * 4, QtGui.QImage.Format.Format_RGBA8888).copy()
        if self._ai_mask_item is not None and self._ai_mask_item.scene() is self:
            self.removeItem(self._ai_mask_item)
        self._ai_mask_item = self.addPixmap(QtGui.QPixmap.fromImage(image))
        self._ai_mask_item.setZValue(AI_MASK_Z)

    def _update_ai_pre_masks(self):
        try:
            masks = self.ai_controller.predict_pre_masks()
        except Exception as err:
            logger.exception("KI pre-mask generation failed: %s", err)
            return
        if masks is None:
            return
        self._draw_ai_pre_masks(masks)

    def _draw_ai_pre_masks(self, masks):
        masks = np.asarray(masks, dtype=bool)
        if masks.ndim != 3:
            logger.warning("AI segmenter returned non-3D pre-masks.")
            return

        count, height, width = masks.shape
        rgba = np.zeros((height, width, 4), dtype=np.uint8)
        if count:
            colors = np.array(
                [
                    [0, 160, 255, 75],
                    [255, 170, 0, 70],
                    [110, 220, 90, 70],
                    [220, 90, 190, 70],
                    [255, 90, 80, 70],
                    [130, 110, 255, 70],
                ],
                dtype=np.uint8,
            )
            for index, mask in enumerate(masks):
                rgba[mask] = colors[index % len(colors)]

        image = QtGui.QImage(rgba.data, width, height, width * 4, QtGui.QImage.Format.Format_RGBA8888).copy()
        self._remove_ai_pre_mask()
        self._ai_pre_mask_item = self.addPixmap(QtGui.QPixmap.fromImage(image))
        self._ai_pre_mask_item.setZValue(AI_PRE_MASK_Z)

    def _remove_ai_pre_mask(self):
        if self._ai_pre_mask_item is not None:
            try:
                if self._ai_pre_mask_item.scene() is self:
                    self.removeItem(self._ai_pre_mask_item)
            except RuntimeError:
                pass
        self._ai_pre_mask_item = None

    def mouseDoubleClickEvent(self, event):
        if self.current_instruction != Instructions.No_Instruction:
            self.mousePressEvent(event)
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            event.accept()
            return
        if self.polygon_brush_enabled:
            event.accept()
            return
        if not self.instruction_active and event.button() == Qt.MouseButton.LeftButton:
            current_item = self.items(event.scenePos())
            if self.image_item in current_item:
                current_item.remove(self.image_item)
                if current_item:
                    _geom = _geometry_item(current_item[0])
                    if _geom is None:
                        event.accept()
                        return
                    object_id = _geom.obj_id
                    part_index = getattr(_geom, "geometry_part_index", None)
                    if part_index is None:
                        self.object_att.emit(object_id)
                    else:
                        self.geometry_part_selected.emit(
                            object_id, part_index, getattr(_geom, "geometry_ring_index", 0)
                        )
                else:
                    self.object_deselected.emit()
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.cancel_active_operation():
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape and self.polygon_brush_enabled:
            self.set_polygon_brush_enabled(False)
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape and self.group_selection_ids:
            self.groupSelectionCleared.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            # Windows sends the context event on release, after finishing a tool
            # can already have cleared current_instruction through a callback.
            self._suppress_context_menu = bool(
                self.instruction_active or self.ai_mode_enabled or self.polygon_brush_enabled
                or self.current_instruction != Instructions.No_Instruction
            )
        if (
            not self.instruction_active and not self.ai_mode_enabled and not self.polygon_brush_enabled
            and self.current_instruction == Instructions.No_Instruction and event.button() == Qt.MouseButton.LeftButton
        ):
            item = next((_geometry_item(hit) for hit in self.items(event.scenePos()) if _geometry_item(hit)), None)
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                if item is not None:
                    self.groupSelectionToggled.emit(item.obj_id)
                event.accept()
                return
            if item is None:
                self.groupSelectionCleared.emit()
        if self._handle_polygon_brush_press(event):
            return
        if self._handle_ai_mouse_press(event):
            return

        if (
            self.instruction_active
            and event.button() == Qt.MouseButton.RightButton
            and self.current_instruction not in {Instructions.Polygon_Instruction, Instructions.Linestring_Instruction}
            and self.cancel_active_operation()
        ):
            event.accept()
            return

        current_item = self.items(event.scenePos())
        if self.image_item in current_item:
            # Remove image form items. Only geometries are left in current items
            current_item.remove(self.image_item)

            # -----------------------------------------------------------------------------------------------
            # STACK CHANGE
            if len(current_item) > 1 and not self.instruction_active and event.button() == Qt.MouseButton.MiddleButton:
                current_item[0].stackBefore(current_item[-1])

            # Move Instruction
            if self.current_instruction == Instructions.Move_Instruction and event.button() == Qt.MouseButton.LeftButton:
                # start move instruction
                item = self.active_geometry_item()
                if item is not None:
                    if not self.instruction_active:
                        if item not in current_item:
                            super().mousePressEvent(event)
                            return
                        pos_scene = event.scenePos()
                        self.old_cords = pos_scene
                        self._begin_operation(item)
                    # finish move instruction
                    else:
                        coordinates, valid = item.get_coords(self.image_width, self.image_height)
                        if valid:
                            if self._commit_geometry_update(item, coordinates, "Move geometry"):
                                self._finish_operation()
                            else:
                                self._reject_active_geometry_operation()

            # Add Point
            if self.current_instruction == Instructions.Add_Point and event.button() == Qt.MouseButton.LeftButton:
                if not self.instruction_active:
                    # create an octagon as to check intersection

                    pick_radius = (self.image_width + self.image_height) / 2.0 / 100
                    x, y = event.scenePos().x(), event.scenePos().y()
                    octo = OctoLines(x, y, pick_radius)
                    # for item_octo in octo.items():
                    #    self.addItem(QtWidgets.QGraphicsLineItem(item_octo))

                    item = self.active_point_edit_item()
                    if item is not None:
                        found_near, id_item, inter_p = item.close_octo(octo)
                        if found_near:
                            self._begin_operation(item)
                            p: list = item.polygon().toList()
                            p.insert(id_item + 1, inter_p)
                            item.setPolygon(QPolygonF(p))
                            self.change_point_index = id_item + 1

                else:
                    item = self.active_point_edit_item()
                    if item is not None and item.is_valid():
                        coordinates, valid = item.get_coords(self.image_width, self.image_height)
                        if valid:
                            if self._commit_geometry_update(item, coordinates, "Add point"):
                                self._finish_operation()
                            else:
                                self._reject_active_geometry_operation()

            # Remove Point
            if self.current_instruction == Instructions.Remove_Point and event.button() == Qt.MouseButton.LeftButton:
                if not self.instruction_active:
                    pick_radius = (self.image_width + self.image_height) / 2.0 / 100
                    item = self.active_point_edit_item()
                    if item is not None:
                        found_near_geometry, idx_point = item.close_point(event.scenePos(), pick_radius)
                        if found_near_geometry:
                            min_points = 3 if getattr(item, "object_type", None) == "polygon" else 2
                            if item.polygon().length() > min_points:
                                original_polygon = QPolygonF(item.polygon())
                                p_del: QPolygonF = QPolygonF(original_polygon)
                                p_del.removeAt(idx_point)
                                item.setPolygon(p_del)
                                if item.is_valid():
                                    coordinates, valid = item.get_coords(self.image_width, self.image_height)
                                    if valid:
                                        if not self._commit_geometry_update(item, coordinates, "Remove point"):
                                            item.setPolygon(original_polygon)
                                            self._emit_no_valid(item)
                                    else:
                                        item.setPolygon(original_polygon)
                                        self._emit_no_valid(item)
                                else:
                                    item.setPolygon(original_polygon)
                                    self._emit_no_valid(item)
                            else:
                                self._emit_no_valid(item)

            if (
                self.current_instruction == Instructions.Change_Instruction
                and event.button() == Qt.MouseButton.LeftButton
            ):
                if not self.instruction_active:
                    item = self.active_geometry_item()
                    if item is not None:
                        pick_radius = (self.image_width + self.image_height) / 2.0 / 100
                        found_near_geometry, idx_point = item.close_point(event.scenePos(), pick_radius)
                        if found_near_geometry:
                            self.change_point_index = idx_point
                            self._begin_operation(item)

                else:
                    item = self.active_geometry_item()
                    if item is not None and item.is_valid():
                        coordinates, valid = item.get_coords(self.image_width, self.image_height)
                        if valid:
                            if self._commit_geometry_update(item, coordinates, "Change geometry"):
                                self._finish_operation()
                            else:
                                self._reject_active_geometry_operation()

            # -----------------------------------------------------------------------------------------------
            # Drawing instructions

            # -----------------------------------------------------------------------------------------------
            # Rectangular, Polygon Picking starting - Circle Middle
            if not self.instruction_active:
                # Polygon
                if self.current_instruction == Instructions.Polygon_Instruction:
                    if event.button() == Qt.MouseButton.LeftButton:
                        # starting point of polygon will be show
                        self.p1_poly = CircleAnnotation(color=self.color_polygon, object_type="polygon")
                        self.addItem(self.p1_poly)
                        self.p1_poly.setRect(
                            event.scenePos().x() - point_size / 2.0,
                            event.scenePos().y() - point_size / 2.0,
                            point_size,
                            point_size,
                        )

                        self.polygon_item = PolygonAnnotation(color=self.color_polygon, object_type="polygon")
                        self.addItem(self.polygon_item)
                        self._begin_operation()
                        self.polygon_item.setPolygon(QPolygonF())
                        poly = self.polygon_item.polygon()
                        poly.append(event.scenePos())
                        poly.append(event.scenePos())
                        self.polygon_item.setPolygon(poly)

                # Rectangle
                if self.current_instruction == Instructions.Rectangle_Instruction:
                    if event.button() == Qt.MouseButton.LeftButton:
                        self.rectangle_item = RectangleAnnotation(color=self.color_rectangle, object_type="rectangle")
                        self.addItem(self.rectangle_item)
                        self.rectangle_item.start_rectangle(event.scenePos())
                        self._begin_operation()

                # Circle
                if self.current_instruction == Instructions.Circle_Instruction:
                    if event.button() == Qt.MouseButton.LeftButton:
                        self.circle_item = CircleAnnotation(color=self.color_circle, object_type="circle")
                        self.addItem(self.circle_item)
                        self.circle_item.setRect(event.scenePos().x(), event.scenePos().y(), 10, 10)
                        self._begin_operation()

                # Point
                if self.current_instruction == Instructions.Point_Instruction:
                    if event.button() == Qt.MouseButton.LeftButton:
                        self.point_item = PointAnnotation(color=self.color_point, object_type="point")
                        self.addItem(self.point_item)
                        self.point_item.set_point(event.scenePos().x(), event.scenePos().y())
                        self._begin_operation()
                        self._finish_operation()
                        coordinates = [event.scenePos().x(), event.scenePos().y()]
                        self.point_item.obj_id, tooltip = self.store_sightings("point", coordinates)
                        self.point_item.setToolTip(tooltip)
                        self.active_item = self.point_item
                        self.selection_changed.emit()
                        self.change_color_id(self.point_item.obj_id, QtGui.QColor.fromRgbF(1.0, 1.00, 0.3, 0.588235))

                # Line
                if self.current_instruction == Instructions.Linestring_Instruction:
                    if event.button() == Qt.MouseButton.LeftButton:
                        self.line_item = LineStringAnnotation(color=self.color_linestring, object_type="linestring")
                        self.addItem(self.line_item)
                        self.line_item.set_points([event.scenePos(), event.scenePos()])
                        self._begin_operation()

            # Continue with Polygon objects
            else:
                if self.current_instruction == Instructions.Polygon_Instruction:
                    # Finish polygon objects
                    if event.button() == Qt.MouseButton.RightButton:
                        poly = self.polygon_item.polygon()
                        poly[-1] = event.scenePos()
                        if len(poly) > 1 and (poly[-1] - poly[-2]).manhattanLength() < 0.1:
                            poly.removeLast()
                        self.polygon_item.setPolygon(poly)
                        if self.polygon_item.polygon().length() > 2:
                            if self.polygon_item.is_valid():
                                self._finish_operation()

                                coordinates, valid = self.polygon_item.get_coords(self.image_width, self.image_height)
                                self.polygon_item.obj_id, tooltip = self.store_sightings("polygon", coordinates)
                                self.polygon_item.setToolTip(tooltip)
                                self.active_item = self.polygon_item
                                self.selection_changed.emit()
                                self.change_color_id(
                                    self.polygon_item.obj_id, QtGui.QColor.fromRgbF(1.0, 1.00, 0.3, 0.588235)
                                )
                            else:
                                self._finish_operation()
                                if self.polygon_item is not None and self.polygon_item.scene() is self:
                                    self.removeItem(self.polygon_item)
                                if self.p1_poly is not None and self.p1_poly.scene() is self:
                                    self.removeItem(self.p1_poly)
                                self._emit_no_valid(self.polygon_item)
                            if self.p1_poly is not None and self.p1_poly.scene() is self:
                                self.removeItem(self.p1_poly)
                        else:
                            self._finish_operation()
                            if self.p1_poly is not None and self.p1_poly.scene() is self:
                                self.removeItem(self.p1_poly)
                            if self.polygon_item is not None and self.polygon_item.scene() is self:
                                self.removeItem(self.polygon_item)
                            self._emit_no_valid(self.polygon_item)

                    # Continue Polygon
                    elif event.button() == Qt.MouseButton.LeftButton:
                        poly = self.polygon_item.polygon()
                        if (poly[-2] - event.scenePos()).manhattanLength() > 1.0:
                            poly[-1] = event.scenePos()
                            poly.append(event.scenePos())
                            self.polygon_item.setPolygon(poly)

                # Continue with Line objects
                if self.current_instruction == Instructions.Linestring_Instruction:
                    if event.button() == Qt.MouseButton.RightButton:
                        points = self.line_item.points().toList()
                        if len(points) >= 2:
                            points[-1] = event.scenePos()
                            if (points[-1] - points[-2]).manhattanLength() < 0.1:
                                points.pop()
                        self.line_item.set_points(points)

                        if self.line_item.is_valid():
                            coordinates, valid = self.line_item.get_coords(self.image_width, self.image_height)
                            if valid:
                                self._finish_operation()
                                self.line_item.obj_id, tooltip = self.store_sightings("linestring", coordinates)
                                self.line_item.setToolTip(tooltip)
                                self.active_item = self.line_item
                                self.selection_changed.emit()
                                self.change_color_id(
                                    self.line_item.obj_id, QtGui.QColor.fromRgbF(1.0, 1.00, 0.3, 0.588235)
                                )
                            else:
                                self._finish_operation()
                                if self.line_item is not None and self.line_item.scene() is self:
                                    self.removeItem(self.line_item)
                                self._emit_no_valid(self.line_item)
                        else:
                            self._finish_operation()
                            if self.line_item is not None and self.line_item.scene() is self:
                                self.removeItem(self.line_item)
                            self._emit_no_valid(self.line_item)

                    elif event.button() == Qt.MouseButton.LeftButton:
                        points = self.line_item.points().toList()
                        if len(points) >= 2 and (points[-2] - event.scenePos()).manhattanLength() > 1.0:
                            points[-1] = event.scenePos()
                            points.append(event.scenePos())
                            self.line_item.set_points(points)

                # Finish Rectangle
                if self.current_instruction == Instructions.Rectangle_Instruction:
                    # Finish Rectangle
                    if event.button() == Qt.MouseButton.LeftButton:
                        self.rectangle_item.resize_rectangle(event.scenePos())
                        # rect = self.rectangle_item.rect().toRect()
                        coordinates, valid = self.rectangle_item.get_coords(self.image_width, self.image_height)

                        # Check if no rectangle with size 0 is created
                        if not self.rectangle_item.rect().isNull():
                            self._finish_operation()
                            self.rectangle_item.obj_id, tooltip = self.store_sightings("rectangle", coordinates)
                            self.rectangle_item.setToolTip(tooltip)
                            self.active_item = self.rectangle_item
                            self.selection_changed.emit()
                            self.change_color_id(
                                self.rectangle_item.obj_id, QtGui.QColor.fromRgbF(1.0, 1.00, 0.3, 0.588235)
                            )

                # Finish Circle
                elif self.current_instruction == Instructions.Circle_Instruction:
                    # Finish Rectangle
                    if event.button() == Qt.MouseButton.LeftButton:
                        self.circle_item.set_radius_from_position(event.scenePos())
                        ellipse_rect = self.circle_item.rect()

                        x = ellipse_rect.x()
                        y = ellipse_rect.y()

                        if (
                            x > 0
                            and y > 0
                            and (x + ellipse_rect.width() < self.image_width)
                            and (y + ellipse_rect.height()) < self.image_height
                        ):
                            self._finish_operation()

                            # rect = self.rectangle_item.rect().toRect()
                            ellipse_rect = self.circle_item.rect()
                            x = ellipse_rect.x() + ellipse_rect.width() / 2.0
                            y = ellipse_rect.y() + ellipse_rect.height() / 2.0
                            radius = ellipse_rect.width() / 2.0
                            coordinates = [x, y, radius]
                            self.circle_item.obj_id, tooltip = self.store_sightings("circle", coordinates)
                            self.circle_item.setToolTip(tooltip)
                            self.active_item = self.circle_item
                            self.selection_changed.emit()
                            self.change_color_id(self.circle_item.obj_id, QtGui.QColor.fromRgbF(1.0, 1.00, 0.3, 0.588235))

        # -----------------------------------------------------------------------------------------------
        # Pass Event
        super().mousePressEvent(event)

    # -----------------------------------------------------------------------------------------------
    # If drawing is active for polygon or rectangle visually show the dynamic outlines
    def mouseMoveEvent(self, event):
        if self._polygon_brush_item is not None:
            self._apply_polygon_brush(event.scenePos())
            event.accept()
            return
        if self._handle_ai_mouse_move(event):
            return

        if self.current_instruction == Instructions.Change_Instruction and self.instruction_active:
            # poly = self.polygon_item.polygon()
            # if poly.length() > 2:
            #     poly.replace(self.change_point_index, event.scenePos())
            # self.polygon_item.setPolygon(poly)
            item = self.active_geometry_item()
            if item is not None:
                item.change_geometry(event.scenePos(), self.change_point_index)

        if self.current_instruction == Instructions.Add_Point and self.instruction_active:
            # poly = self.polygon_item.polygon()
            # if poly.length() > 2:
            #     poly.replace(self.change_point_index, event.scenePos())
            # self.polygon_item.setPolygon(poly)
            item = self.active_point_edit_item()
            if item is not None:
                item.change_geometry(event.scenePos(), self.change_point_index)

        if self.current_instruction == Instructions.Move_Instruction and self.instruction_active:
            item = self.active_geometry_item()
            if item is not None:
                change_vector = event.scenePos() - self.old_cords
                item.move([change_vector.x(), change_vector.y()])
                self.old_cords = event.scenePos()

        current_item = self.items(event.scenePos())
        if self.image_item in current_item:
            if self.instruction_active:
                if self.current_instruction == Instructions.Polygon_Instruction:
                    poly = self.polygon_item.polygon()
                    if poly.length() >= 2:
                        poly[poly.length() - 1] = event.scenePos()
                        self.polygon_item.setPolygon(poly)

                if self.current_instruction == Instructions.Rectangle_Instruction:
                    self.rectangle_item.resize_rectangle(event.scenePos())

                if self.current_instruction == Instructions.Circle_Instruction:
                    self.circle_item.set_radius_from_position(event.scenePos())

                if self.current_instruction == Instructions.Linestring_Instruction:
                    points = self.line_item.points().toList()
                    if len(points) >= 2:
                        points[-1] = event.scenePos()
                        self.line_item.set_points(points)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._handle_polygon_brush_release(event):
            return
        if self._handle_ai_mouse_release(event):
            return
        super().mouseReleaseEvent(event)
