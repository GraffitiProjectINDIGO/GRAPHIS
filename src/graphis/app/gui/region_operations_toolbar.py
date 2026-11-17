# Copyright (C) 2026 Martin Wieser

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon
from PySide6.QtWidgets import QColorDialog, QToolBar

from graphis.app.gui.resources import icon, icon_path_str


class RegionOperationsToolbar(QToolBar):
    CREATE_ACTIONS = {"create_circle", "create_point", "create_linestring", "create_rectangle", "create_polygon"}
    MOVE_ACTIONS = {"move_geometry"}
    CHANGE_ACTIONS = {"change_geometry"}
    POLYGON_EDIT_ACTIONS = {"add_point", "remove_point"}

    instructionSelected = Signal(str)
    instructionCleared = Signal()
    deleteRequested = Signal()
    deleteImageRegionRequested = Signal()
    visibilityToggled = Signal(str)
    colorChanged = Signal(str, QColor)

    def __init__(self, parent=None):
        super().__init__("Geometric Operations", parent)
        self.setObjectName("geom_operations")
        self.setMovable(True)
        self.setFloatable(False)
        self.setAllowedAreas(
            Qt.ToolBarArea.LeftToolBarArea | Qt.ToolBarArea.RightToolBarArea | Qt.ToolBarArea.TopToolBarArea
        )
        self.setIconSize(QSize(28, 28))
        self.setStyleSheet("""
            QToolBar {
                min-width: 40px;
                min-height: 40px;
                background: rgb(85, 85, 85);
                border: none;
            }
            QToolButton {
                background: rgb(52, 59, 72);
                border: 1px solid rgb(70, 78, 92);
                border-radius: 4px;
                padding: 3px;
            }
            QToolButton:hover {
                background: rgb(65, 74, 90);
            }
            QToolButton:checked {
                background: rgb(90, 110, 135);
            }
        """)

        self.operation_actions = {}
        self.visibility_actions = {}
        self.color_actions = {}
        self._colors = {}
        self.delete_action = None
        self.delete_image_region_action = None

        self._operation_group = QActionGroup(self)
        self._operation_group.setExclusive(False)
        self._operation_group.triggered.connect(self._operation_triggered)

        self._build_operations()
        self.addSeparator()
        self._build_appearance()
        self.layout().setSpacing(3)
        self.layout().setContentsMargins(3, 3, 3, 3)

    def _build_operations(self):
        self._add_operation("create_point", "Create point", "point.svg", "point_active.svg")
        self._add_operation("create_circle", "Create circle", "circle.svg", "circle_active.svg")
        self._add_operation("create_linestring", "Create linestring", "linestring.svg", "linestring_active.svg")
        self._add_operation("create_rectangle", "Create rectangle", "rectangle.svg", "rectangle_active.svg")
        self._add_operation("create_polygon", "Create polygon", "polygon.svg", "polygon_active.svg")
        self._add_operation("move_geometry", "Move geometry", "move.svg", "move_active.svg", "move_deac.svg")
        self._add_operation(
            "change_geometry", "Resize geometry/Move Node", "resize.svg", "resize_active.svg", "resize_deac.svg"
        )
        self._add_operation("add_point", "Add point/vertex", "add_node.svg", "add_node_active.svg", "add_node_deac.svg")
        self._add_operation(
            "remove_point", "Remove point/vertex", "remove_node.svg", "remove_node_active.svg", "remove_node_deac.svg"
        )

        self.delete_action = QAction(self._icon("Flat_cross_icon.svg"), "Delete geometry", self)
        self.delete_action.setToolTip("Delete geometry only")
        self.delete_action.triggered.connect(self.deleteRequested)
        self.addAction(self.delete_action)
        self.addSeparator()

        self.delete_image_region_action = QAction(self._icon("delete-image-region.svg"), "Delete image region", self)
        self.delete_image_region_action.setToolTip("Delete image region")
        self.delete_image_region_action.triggered.connect(self.deleteImageRegionRequested)
        self.addAction(self.delete_image_region_action)

    def _build_appearance(self):
        self._add_visibility("point", "Show/hide points", "point_show.svg", "point_hide.svg")
        self._add_visibility("circle", "Show/hide circles", "circle_show.svg", "circle_hide.svg")
        self._add_visibility("linestring", "Show/hide linestrings", "linestring_show.svg", "linestring_hide.svg")
        self._add_visibility("rectangle", "Show/hide rectangles", "rectangle_show.svg", "rectangle_hide.svg")
        self._add_visibility("polygon", "Show/hide polygons", "polygon_show.svg", "polygon_hide.svg")
        self._add_color("point", "Point color", "point_color.svg")
        self._add_color("circle", "Circle color", "circle_color.svg")
        self._add_color("linestring", "Linestring color", "linestring_color.svg")
        self._add_color("rectangle", "Rectangle color", "rectangle_color.svg")
        self._add_color("polygon", "Polygon color", "polygon_color.svg")

    def _add_operation(self, instruction, text, icon_name, active_icon_name, disabled_icon_name: str | None = None):
        action = QAction(self._state_icon(icon_name, active_icon_name, disabled_icon_name), text, self)
        action.setCheckable(True)
        action.setData(instruction)
        if instruction in {"create_polygon", "create_linestring"}:
            hint = "Left-click to add vertices; right-click to finish. Escape cancels."
        elif instruction == "create_point":
            hint = "Left-click to place a point."
        elif instruction in self.CREATE_ACTIONS:
            hint = "Left-click to start, then left-click to finish. Right-click or Escape cancels."
        elif instruction == "remove_point":
            hint = "Left-click a vertex to remove it."
        else:
            hint = "Left-click to start, then left-click to finish. Right-click or Escape cancels."
        action.setToolTip(f"{text}\n{hint}")
        self._operation_group.addAction(action)
        self.addAction(action)
        self.operation_actions[instruction] = action

    def _add_visibility(self, object_type, text, show_icon, hide_icon):
        action = QAction(self._icon(show_icon), text, self)
        action.setCheckable(True)
        action.setChecked(True)
        action.setData((show_icon, hide_icon))
        action.setToolTip(text)
        action.triggered.connect(lambda _checked=False, item_type=object_type: self.visibilityToggled.emit(item_type))
        self.addAction(action)
        self.visibility_actions[object_type] = action

    def _add_color(self, object_type, text, icon_name):
        action = QAction(self._icon(icon_name), text, self)
        action.setToolTip(text)
        action.triggered.connect(lambda _checked=False, item_type=object_type: self._pick_color(item_type))
        self.addAction(action)
        self.color_actions[object_type] = action

    def _operation_triggered(self, action):
        instruction = action.data()
        if not instruction:
            return

        if not action.isChecked():
            self.instructionCleared.emit()
            return

        was_blocked = self._operation_group.blockSignals(True)
        for other_action in self._operation_group.actions():
            if other_action is not action:
                other_action.setChecked(False)
        self._operation_group.blockSignals(was_blocked)
        self.instructionSelected.emit(instruction)

    def _pick_color(self, object_type):
        current = self._colors.get(object_type, QColor())
        color = QColorDialog.getColor(
            current,
            self,
            f"Select {object_type} color",
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if color.isValid():
            if color.alpha() == 255:
                color.setAlpha(150)
            self.set_color(object_type, color)
            self.colorChanged.emit(object_type, color)

    def clear_active_tool(self):
        was_blocked = self._operation_group.blockSignals(True)
        for action in self._operation_group.actions():
            action.setChecked(False)
        self._operation_group.blockSignals(was_blocked)

    def set_active_tool(self, instruction):
        action = self.operation_actions.get(instruction)
        if not action:
            return
        was_blocked = self._operation_group.blockSignals(True)
        action.setChecked(True)
        self._operation_group.blockSignals(was_blocked)

    def set_action_availability(
        self,
        has_selection=False,
        selected_object_type=None,
        operation_active=False,
        has_region=False,
    ):
        is_polygon = selected_object_type == "polygon"
        is_point = selected_object_type == "point"
        is_linestring = selected_object_type == "linestring"

        for instruction, action in self.operation_actions.items():
            if operation_active:
                action.setEnabled(False)
            elif instruction in self.CREATE_ACTIONS:
                action.setEnabled(True)
            elif instruction in self.MOVE_ACTIONS:
                action.setEnabled(has_selection)
            elif instruction in self.CHANGE_ACTIONS:
                action.setEnabled(has_selection and not is_point)
            elif instruction in self.POLYGON_EDIT_ACTIONS:
                action.setEnabled(has_selection and (is_polygon or is_linestring))
            else:
                action.setEnabled(True)

        if self.delete_action is not None:
            self.delete_action.setEnabled(has_selection and not operation_active)
        if self.delete_image_region_action is not None:
            self.delete_image_region_action.setEnabled(has_region and not operation_active)

    def set_visibility(self, object_type, visible):
        action = self.visibility_actions.get(object_type)
        if not action:
            return
        show_icon, hide_icon = action.data()
        action.setChecked(visible)
        action.setIcon(self._icon(show_icon if visible else hide_icon))

    def set_color(self, object_type, color):
        color = QColor(color)
        self._colors[object_type] = color
        self._update_color_action_style(object_type, color)

    def _update_color_action_style(self, object_type, color):
        action = self.color_actions.get(object_type)
        if not action:
            return

        button = self.widgetForAction(action)
        if button is None:
            QTimer.singleShot(0, lambda: self._update_color_action_style(object_type, color))
            return

        button.setStyleSheet(
            "QToolButton {"
            f"border: 2px solid {color.name()};"
            "border-radius: 4px;"
            f"background-color: {color.name(QColor.NameFormat.HexArgb)};"
            "padding: 3px;"
            "}"
            "QToolButton:hover {"
            f"background-color: {color.lighter(115).name(QColor.NameFormat.HexArgb)};"
            f"border: 2px solid {color.lighter(115).name()};"
            "}"
        )

    def _icon(self, icon_name):
        return icon(icon_name)

    def _state_icon(self, icon_name, active_icon_name, disabled_icon: str | None = None):
        state_icon = QIcon()
        state_icon.addFile(icon_path_str(icon_name), QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        state_icon.addFile(icon_path_str(active_icon_name), QSize(), QIcon.Mode.Normal, QIcon.State.On)
        if disabled_icon is not None:
            state_icon.addFile(icon_path_str(disabled_icon), QSize(), QIcon.Mode.Disabled, QIcon.State.Off)
        return state_icon
