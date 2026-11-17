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

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsScene, QMenu

from graphis.app.imgregion.region_graph_items import RegionArrowItem, RegionNodeItem
from graphis.app.imgregion.region_graph_model import region_shape
from graphis.interface.imgregion_adapter import valid_region_geometry_merge_modes
from graphis.interface.region_membership import MEMBERSHIP_KEYS

_MERGE_MODE_LABELS = {
    "multipoint": "Merge as multipoint",
    "multilinestring": "Merge as multilinestring",
    "multipolygon": "Merge as multipolygon",
    "inner_polygon": "Make inner polygon",
}


class RegionGraphScene(QGraphicsScene):
    regionSelected = Signal(str)
    geometryPartSelected = Signal(str, int, int)
    selectionCleared = Signal()
    activeValidationIssuesChanged = Signal(object)
    assignGeometryRequested = Signal(str, str)
    clearGeometryRequested = Signal(str)
    zoomToRegionRequested = Signal(str)
    deleteImageRegionRequested = Signal(str)
    restoreOriginalRequested = Signal(str)
    jsonMetadataRequested = Signal(str)
    mergeRegionsRequested = Signal(str, str, str)
    createContainerRequested = Signal(str)
    groupSelectedRequested = Signal(object, str)
    groupSelectedIntoRequested = Signal(object, str)
    assignParentRequested = Signal(str)
    mergeTargetRequested = Signal(str, str)
    detachGeometryPartRequested = Signal(str, int)
    detachParentRequested = Signal(str)
    groupSelectionChanged = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes = []
        self.node_items = {}
        self.arrow_items = []
        self.selected_object_id = None
        self.selected_object_ids = set()
        self._merge_drop_source_id = None
        self._merge_drop_target_id = None
        self.image_width = None
        self.image_height = None
        self.setBackgroundBrush(QColor("#15191f"))

    def clear_graph(self):
        self.clear()
        self.nodes = []
        self.node_items = {}
        self.arrow_items = []
        self.selected_object_id = None
        self.selected_object_ids = set()
        self._merge_drop_source_id = None
        self._merge_drop_target_id = None
        self.activeValidationIssuesChanged.emit([])
        self.groupSelectionChanged.emit([])

    def set_image_size(self, image_width, image_height):
        self.image_width = image_width
        self.image_height = image_height

    def set_nodes(self, nodes):
        self.clear_graph()
        self.nodes = nodes
        self._layout_nodes(nodes)

        for node in self._flatten(nodes):
            item = RegionNodeItem(node)
            item.setPos(node.graph_pos or QPointF(0, 0))
            item.selected.connect(self.request_select_region)
            item.moved.connect(self._node_moved)
            item.moveReleased.connect(self._node_move_released)
            self.addItem(item)
            self.node_items[node.object_id] = item

        for node in self._flatten(nodes):
            if not node.parent_id:
                continue
            source = self.node_items.get(node.parent_id)
            target = self.node_items.get(node.object_id)
            if source and target:
                arrow = RegionArrowItem(source, target)
                source.arrows.append(arrow)
                target.arrows.append(arrow)
                self.addItem(arrow)
                self.arrow_items.append(arrow)

        self.update_scene_rect()

    def auto_layout(self):
        self._layout_nodes(self.nodes, force=True)

        for node in self._flatten(self.nodes):
            item = self.node_items.get(node.object_id)
            if item and node.graph_pos is not None:
                item.setPos(node.graph_pos)
        for arrow in self.arrow_items:
            arrow.update_position()
        self.update_scene_rect()

    def update_scene_rect(self):
        if self.items():
            self.setSceneRect(self.itemsBoundingRect().adjusted(-180, -140, 180, 140))

    def expand_scene_rect_if_needed(self, _object_id=None):
        if not self.items():
            return
        item_bounds = self.itemsBoundingRect().adjusted(-180, -140, 180, 140)
        scene_rect = self.sceneRect()
        if scene_rect.isNull() or not scene_rect.contains(item_bounds):
            self.setSceneRect(scene_rect.united(item_bounds))

    def request_select_region(self, object_id):
        item = self.node_items.get(object_id)
        if item:
            if item.node.geometry_part_index is not None:
                self.geometryPartSelected.emit(
                    item.node.geometry_owner_id or object_id,
                    item.node.geometry_part_index,
                    item.node.geometry_ring_index or 0,
                )
            else:
                self.regionSelected.emit(object_id)

    def select_region(self, object_id):
        item = self.node_items.get(object_id)
        if not item:
            return
        self._clear_group_selection()
        self._set_active_region(object_id)
        # views = self.views()
        # if views:
        #    views[0].centerOn(item)

    def request_clear_region_selection(self):
        self.selectionCleared.emit()

    def clear_region_selection(self):
        self._set_active_region(None)
        self._clear_group_selection()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self._node_item_at(event.scenePos())
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                if item is not None:
                    if item.node.geometry_owner_id is not None:
                        event.accept()
                        return
                    self._toggle_group_selection(item.node.object_id)
                    event.accept()
                    return
            elif item is None:
                self._clear_group_selection()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            item = self._node_item_at(event.scenePos())
            if item is not None:
                self.request_select_region(item.node.object_id)
            else:
                self.request_clear_region_selection()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        item = self._node_item_at(event.scenePos())
        if item is None:
            self._show_empty_context_menu(event)
            return

        if item.node.geometry_owner_id is not None:
            menu = QMenu()
            select_action = menu.addAction("Select geometry part")
            select_owner_action = menu.addAction("Select whole image region")
            owner = self.node_items.get(item.node.geometry_owner_id)
            detach_action = None
            if (
                owner is not None and region_shape(owner.node.region) in {"multipoint", "multilinestring", "multipolygon"}
                and (item.node.geometry_ring_index or 0) == 0
            ):
                detach_action = menu.addAction("Detach as new image region")
            selected_action = menu.exec(event.screenPos())
            if selected_action == select_action:
                self.request_select_region(item.node.object_id)
            elif selected_action == select_owner_action:
                self.request_select_region(item.node.geometry_owner_id)
            elif detach_action is not None and selected_action == detach_action:
                self.detachGeometryPartRequested.emit(item.node.geometry_owner_id, item.node.geometry_part_index)
            event.accept()
            return

        object_id = item.node.object_id
        if not self.selected_object_ids and self.selected_object_id != object_id:
            self.request_select_region(object_id)
            if self.selected_object_id != object_id:
                event.accept()
                return

        menu = QMenu()
        dispatch = self.populate_region_context_menu(menu, item)
        dispatch(menu.exec(event.screenPos()))
        event.accept()

    def populate_region_context_menu(
        self, menu, item, *, include_geometry_assignment=True, include_group_selection=True
    ):
        """Add region actions shared by the graph and digitizer; return their dispatcher."""
        object_id = item.node.object_id
        selected_ids = self._effective_group_selection(object_id) if include_group_selection else [object_id]
        group_actions = self._add_group_actions(menu, selected_ids, object_id)
        if group_actions:
            menu.addSeparator()
        assign_parent_action = menu.addAction("Assign parent...")
        detach_parent_action = remove_membership_action = None
        if item.node.parent_id is not None:
            detach_parent_action = menu.addAction("Detach from parent")
        elif any(key in item.node.region for key in MEMBERSHIP_KEYS):
            remove_membership_action = menu.addAction("Remove rMemberOf")
            remove_membership_action.setToolTip("Remove the invalid region membership reference")
        merge_menu = menu.addMenu("Merge geometry into...")
        merge_actions = {}
        shape = region_shape(item.node.region)
        if shape in {"rectangle", "polygon"}:
            merge_actions[merge_menu.addAction("As inner polygon")] = "inner_polygon"
        if shape in {"rectangle", "polygon", "multipolygon", "point", "multipoint", "linestring", "multilinestring"}:
            merge_actions[merge_menu.addAction("As multigeometry")] = "multigeometry"
        merge_menu.setEnabled(bool(merge_actions))
        menu.addSeparator()
        assign_rectangle_action = assign_polygon_action = assign_circle_action = None
        assign_point_action = assign_line_action = None
        if include_geometry_assignment and not shape:
            assign_rectangle_action = menu.addAction("Assign rectangle geometry")
            assign_polygon_action = menu.addAction("Assign polygon geometry")
            assign_circle_action = menu.addAction("Assign circle geometry")
            assign_point_action = menu.addAction("Assign point geometry")
            assign_line_action = menu.addAction("Assign linestring geometry")
            menu.addSeparator()
        clear_geometry_action = menu.addAction("Clear geometry")
        clear_geometry_action.setEnabled(bool(region_shape(item.node.region)))
        zoom_to_action = menu.addAction("Zoom to")
        zoom_to_action.setEnabled(bool(region_shape(item.node.region)))
        edit_json_metadata_action = menu.addAction("Edit additional image region metadata...")
        menu.addSeparator()
        delete_region_action = menu.addAction("Delete image region")
        restore_original_action = menu.addAction("Restore original image region")

        def dispatch(selected_action):
            if selected_action is None:
                return
            if selected_action in group_actions:
                action_kind, action_value = group_actions[selected_action]
                if action_kind == "new_container":
                    self.groupSelectedRequested.emit(list(selected_ids), action_value)
                elif action_kind == "existing_container":
                    child_ids = [selected_id for selected_id in selected_ids if selected_id != action_value]
                    self.groupSelectedIntoRequested.emit(child_ids, action_value)
                elif action_kind == "linked_parts":
                    child_ids, container_id = action_value
                    self.groupSelectedIntoRequested.emit(child_ids, container_id)
            elif selected_action == assign_parent_action:
                self.assignParentRequested.emit(object_id)
            elif selected_action in (detach_parent_action, remove_membership_action):
                self.detachParentRequested.emit(object_id)
            elif selected_action in merge_actions:
                self.mergeTargetRequested.emit(object_id, merge_actions[selected_action])
            elif selected_action == assign_rectangle_action:
                self.assignGeometryRequested.emit(object_id, "rectangle")
            elif selected_action == assign_polygon_action:
                self.assignGeometryRequested.emit(object_id, "polygon")
            elif selected_action == assign_circle_action:
                self.assignGeometryRequested.emit(object_id, "circle")
            elif selected_action == assign_point_action:
                self.assignGeometryRequested.emit(object_id, "point")
            elif selected_action == assign_line_action:
                self.assignGeometryRequested.emit(object_id, "linestring")
            elif selected_action == clear_geometry_action:
                self.clearGeometryRequested.emit(object_id)
            elif selected_action == zoom_to_action:
                self.zoomToRegionRequested.emit(object_id)
            elif selected_action == edit_json_metadata_action:
                self.jsonMetadataRequested.emit(object_id)
            elif selected_action == delete_region_action:
                self.deleteImageRegionRequested.emit(object_id)
            elif selected_action == restore_original_action:
                self.restoreOriginalRequested.emit(object_id)

        return dispatch

    def _show_empty_context_menu(self, event):
        menu = QMenu()
        self._add_create_container_actions(menu)
        selected_ids = self._effective_group_selection()
        group_actions = self._add_group_actions(menu, selected_ids, None)

        selected_action = menu.exec(event.screenPos())
        if selected_action in group_actions:
            _action_kind, action_value = group_actions[selected_action]
            self.groupSelectedRequested.emit(list(selected_ids), action_value)
        elif selected_action is not None:
            object_type = selected_action.data()
            if object_type:
                self.createContainerRequested.emit(object_type)
        event.accept()

    def _set_active_region(self, object_id):
        if self.selected_object_id == object_id:
            return
        for item in self.node_items.values():
            item.set_active(item.node.object_id == object_id)
        self.selected_object_id = object_id
        item = self.node_items.get(object_id)
        self.activeValidationIssuesChanged.emit(item.node.validation_issues if item is not None else [])

    def _toggle_group_selection(self, object_id):
        if object_id in self.selected_object_ids:
            self.selected_object_ids.remove(object_id)
        else:
            self.selected_object_ids.add(object_id)
        self._sync_group_selection_items()

    def toggle_group_selection(self, object_id):
        item = self.node_items.get(str(object_id))
        if item is not None and item.node.geometry_owner_id is None:
            self._toggle_group_selection(str(object_id))

    def set_group_selection(self, object_ids):
        self.selected_object_ids = {
            str(object_id) for object_id in object_ids
            if str(object_id) in self.node_items and self.node_items[str(object_id)].node.geometry_owner_id is None
        }
        self._sync_group_selection_items()

    def clear_group_selection(self):
        self._clear_group_selection()

    def _clear_group_selection(self):
        if not self.selected_object_ids:
            return
        self.selected_object_ids.clear()
        self._sync_group_selection_items()

    def _sync_group_selection_items(self):
        for object_id, item in self.node_items.items():
            item.set_multi_selected(object_id in self.selected_object_ids)
        self.groupSelectionChanged.emit(list(self.selected_object_ids))

    def _effective_group_selection(self, context_object_id=None):
        selected_ids = set(self.selected_object_ids)
        if context_object_id is not None and selected_ids:
            selected_ids.add(context_object_id)
        return tuple(object_id for object_id in self.node_items if object_id in selected_ids)

    def _add_create_container_actions(self, menu):
        container_menu = menu.addMenu("Create empty multi-geometry")
        for object_type, label in (
            ("multipoint", "Multipoint"),
            ("multilinestring", "Multilinestring"),
            ("multipolygon", "Multipolygon"),
        ):
            action = container_menu.addAction(label)
            action.setData(object_type)

    def _add_group_actions(self, menu, selected_ids, context_object_id):
        group_actions = {}
        container = self._node_by_id(context_object_id) if context_object_id is not None else None
        if container is not None:
            child_ids = [child.object_id for child in container.children if child.geometry_owner_id is None]
            boundary = container.region.get("regionBoundary", {})
            if (
                child_ids
                and boundary.get("rbCoordinates") in (None, [], "[]")
                and self._group_into_modes([context_object_id, *child_ids], context_object_id)
            ):
                action = menu.addAction("Build multigeometry from linked regions")
                group_actions[action] = ("linked_parts", (child_ids, context_object_id))
        if len(selected_ids) < 2:
            return group_actions

        modes = self._group_modes(selected_ids)
        if modes:
            group_menu = menu.addMenu("Group selected as")
            for mode in modes:
                action = group_menu.addAction(self._group_mode_label(mode))
                group_actions[action] = ("new_container", mode)

        if context_object_id is not None and context_object_id in selected_ids:
            existing_modes = self._group_into_modes(selected_ids, context_object_id)
            if existing_modes:
                action = menu.addAction(f"Add selected children to {self._group_mode_label(existing_modes[0])}")
                group_actions[action] = ("existing_container", context_object_id)
        return group_actions

    def _group_modes(self, object_ids):
        shapes = {self._normalized_shape_for_grouping(object_id) for object_id in object_ids}
        shapes.discard("")
        if shapes == {"point"}:
            return ("multipoint",)
        if shapes == {"linestring"}:
            return ("multilinestring",)
        if shapes == {"polygon"}:
            return ("multipolygon",)
        return ()

    def _group_into_modes(self, object_ids, container_id):
        container = self._node_by_id(container_id)
        if container is None:
            return ()
        container_shape = region_shape(container.region)
        if container_shape not in {"multipoint", "multilinestring", "multipolygon"}:
            return ()
        child_ids = [object_id for object_id in object_ids if object_id != container_id]
        if not child_ids:
            return ()
        return (container_shape,) if container_shape in self._group_modes(child_ids) else ()

    def _normalized_shape_for_grouping(self, object_id):
        node = self._node_by_id(object_id)
        if node is None:
            return ""
        shape = region_shape(node.region)
        if shape == "multipoint":
            return "point"
        if shape == "multilinestring":
            return "linestring"
        if shape == "multipolygon":
            return "polygon"
        if shape == "rectangle":
            return "polygon"
        return shape

    def _group_mode_label(self, mode):
        if mode == "multipoint":
            return "multipoint"
        if mode == "multilinestring":
            return "multilinestring"
        if mode == "multipolygon":
            return "multipolygon"
        return mode

    def _node_item_at(self, pos):
        for item in self.items(pos):
            current = item
            while current is not None:
                if isinstance(current, RegionNodeItem):
                    return current
                current = current.parentItem()
        return None

    def _node_moved(self, object_id):
        self._set_merge_drop_target(object_id, self._merge_drop_target_for(object_id))

    def _node_move_released(self, object_id, screen_pos):
        target_id = self._merge_drop_target_id if self._merge_drop_source_id == object_id else None
        self._clear_merge_drop_target()
        self.expand_scene_rect_if_needed(object_id)
        if target_id is not None:
            modes = self._merge_modes(object_id, target_id)
            if len(modes) == 1:
                self.mergeRegionsRequested.emit(object_id, target_id, modes[0])
            elif modes:
                self._show_drop_merge_menu(object_id, target_id, modes, screen_pos)

    def _merge_drop_target_for(self, object_id):
        source = self.node_items.get(object_id)
        if source is None:
            return None

        source_rect = source.sceneBoundingRect()
        candidates = []
        for raw_item in self.collidingItems(source):
            item = self._node_item_parent(raw_item)
            if item is None or item is source:
                continue
            candidate_id = item.node.object_id
            if not self._merge_modes(object_id, candidate_id):
                continue
            overlap = source_rect.intersected(item.sceneBoundingRect())
            candidates.append((overlap.width() * overlap.height(), candidate_id))

        if not candidates:
            return None
        candidates.sort(reverse=True)
        return candidates[0][1]

    def _node_item_parent(self, item):
        current = item
        while current is not None:
            if isinstance(current, RegionNodeItem):
                return current
            current = current.parentItem()
        return None

    def _set_merge_drop_target(self, source_id, target_id):
        if self._merge_drop_source_id == source_id and self._merge_drop_target_id == target_id:
            return
        self._clear_merge_drop_target()
        self._merge_drop_source_id = source_id
        self._merge_drop_target_id = target_id
        item = self.node_items.get(target_id)
        if item is not None:
            item.set_merge_target(True)

    def _clear_merge_drop_target(self):
        item = self.node_items.get(self._merge_drop_target_id)
        if item is not None:
            item.set_merge_target(False)
        self._merge_drop_source_id = None
        self._merge_drop_target_id = None

    def _show_drop_merge_menu(self, source_id, target_id, modes, screen_pos):
        menu = QMenu()
        actions = {}
        for mode in modes:
            action = menu.addAction(_MERGE_MODE_LABELS.get(mode, mode))
            actions[action] = mode
        selected_action = menu.exec(screen_pos)
        if selected_action in actions:
            self.mergeRegionsRequested.emit(source_id, target_id, actions[selected_action])

    def _merge_geometry_candidates(self, source_id):
        candidates = []
        for node in self._flatten(self.nodes):
            modes = self._merge_modes(source_id, node.object_id)
            if modes:
                candidates.append((node, modes))
        return candidates

    def _merge_modes(self, source_id, target_id):
        if source_id == target_id:
            return ()
        source = self._node_by_id(source_id)
        target = self._node_by_id(target_id)
        if (
            source is None
            or target is None
            or source.geometry_owner_id is not None
            or target.geometry_owner_id is not None
        ):
            return ()
        return tuple(
            valid_region_geometry_merge_modes(
                source.region,
                target.region,
                img_width=self.image_width,
                img_height=self.image_height,
            )
        )

    def _node_by_id(self, object_id):
        return next((node for node in self._flatten(self.nodes) if node.object_id == object_id), None)

    def _layout_nodes(self, roots, force=False):
        nodes = self._flatten(roots)
        if not nodes:
            return
        if not force and all(node.graph_pos is not None for node in nodes):
            return

        has_edges = any(node.children for node in nodes)
        if has_edges:
            self._layout_tree(roots, force)
        else:
            self._layout_radial(nodes, force)

    def _layout_radial(self, nodes, force):
        count = len(nodes)
        if count == 1:
            if force or nodes[0].graph_pos is None:
                nodes[0].graph_pos = QPointF(0, 0)
            return

        radius_x = max(280.0, count * 58.0)
        radius_y = max(190.0, count * 42.0)
        start_angle = -math.pi / 2

        for index, node in enumerate(nodes):
            if not force and node.graph_pos is not None:
                continue
            angle = start_angle + (2 * math.pi * index / count)
            wobble = 1.0 + ((index % 3) - 1) * 0.08
            node.graph_pos = QPointF(
                math.cos(angle) * radius_x * wobble,
                math.sin(angle) * radius_y * wobble,
            )

    def _layout_tree(self, roots, force):
        x_spacing = 320.0
        y_spacing = 145.0
        y_cursor = 0.0
        computed = []

        def place(node, depth):
            nonlocal y_cursor
            node.depth = depth
            if node.children:
                child_ys = []
                has_deeper_groups = any(child.children for child in node.children)
                for index, child in enumerate(node.children):
                    child_ys.append(place(child, depth + 1))
                    if index < len(node.children) - 1:
                        y_cursor += 95.0 if has_deeper_groups else 28.0
                y = sum(child_ys) / len(child_ys)
            else:
                y = y_cursor
                y_cursor += y_spacing

            sibling_offset = 34.0 if depth % 2 else 0.0
            computed.append((node, QPointF(depth * x_spacing + sibling_offset, y)))
            return y

        for index, root in enumerate(roots):
            before = y_cursor
            place(root, 0)
            if before == y_cursor:
                y_cursor += y_spacing
            if index < len(roots) - 1:
                y_cursor += 170.0

        if computed:
            min_y = min(point.y() for _node, point in computed)
            max_y = max(point.y() for _node, point in computed)
            y_center = (min_y + max_y) / 2
        else:
            y_center = 0

        for node, point in computed:
            if force or node.graph_pos is None:
                centered_y = point.y() - y_center
                node.graph_pos = QPointF(
                    point.x() + self._layout_noise(node.object_id, "x") * 42.0 + abs(centered_y) * 0.08,
                    centered_y + self._layout_noise(node.object_id, "y") * 28.0,
                )

    def _layout_noise(self, text, salt):
        seed = f"{text}:{salt}"
        value = sum((index + 1) * ord(char) for index, char in enumerate(seed))
        return math.sin(value * 12.9898) * 0.5 + math.sin(value * 78.233) * 0.5

    def _flatten(self, nodes):
        result = []
        for node in nodes:
            result.append(node)
            result.extend(self._flatten(node.children))
        return result
