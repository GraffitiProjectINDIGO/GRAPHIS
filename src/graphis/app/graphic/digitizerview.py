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

from PySide6.QtCore import QEvent, QPoint, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPen, QShortcut, QTransform
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QColorDialog,
    QComboBox,
    QGraphicsView,
    QGridLayout,
    QLabel,
    QSlider,
    QToolButton,
    QWidget,
)

from graphis.app.gui.resources import icon as resource_icon
from graphis.app.popups.image_metadata_popup import ImageMetadataPopup


class DIGITIZERView(QGraphicsView):
    visualRotationChanged = Signal(int)
    exifRotationRequested = Signal()
    metadataRequested = Signal()
    aiModeChanged = Signal(bool)
    aiToolChanged = Signal(str)
    aiResetRequested = Signal()
    aiPolygonRequested = Signal()
    aiPreclassificationChanged = Signal(bool)
    aiMaskColorChanged = Signal(QColor)
    aiBackendChanged = Signal(str)
    aiDeviceChanged = Signal(str)
    polygonBrushToggled = Signal(bool)
    polygonBrushModeChanged = Signal(str)
    polygonBrushSizeChanged = Signal(int)
    factor = 2.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._smooth_pixmap = True
        self._ai_mask_color = QColor(0, 120, 255)
        self._ai_initializing = False
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setMouseTracking(True)

        # self.setDragMode(QGraphicsView.ScrollHandDrag)
        QShortcut(QKeySequence.ZoomIn, self, activated=self.zoom_in)
        QShortcut(QKeySequence.ZoomOut, self, activated=self.zoom_out)

        self.rightPressed = False
        self.middlePressed = False

        self._dragPos = QPoint()
        self.x_pos = 0
        self.y_pos = 0
        self._auto_fit_on_resize = False
        self._visual_rotation_degrees = 0
        self._exif_rotation_available = False
        self._overlay_margin = 10
        self._overlay_user_pos = None
        self._overlay_drag_pos = None
        self._ai_overlay_user_pos = None
        self._ai_overlay_drag_pos = None
        self._brush_overlay_user_pos = None
        self._brush_overlay_drag_pos = None
        self._polygon_brush_cursor_pos = None

        self.image_controls = QWidget(self)
        self.image_controls.setObjectName("imageViewerControls")
        self.image_controls.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.image_controls.setCursor(Qt.CursorShape.SizeAllCursor)
        self.image_controls.installEventFilter(self)

        layout = QGridLayout(self.image_controls)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        self.fit_image_button = self._create_overlay_button("fit-image.svg", "Fit image")
        self.smoothing_button = self._create_overlay_button("smoothing-active.svg", "Smooth image scaling")
        self.smoothing_button.setCheckable(True)
        self.smoothing_button.setChecked(True)
        self.metadata_button = self._create_overlay_button("about.svg", "Show imported EXIF metadata JSON")
        self.metadata_button.setCheckable(True)
        self.zoom_active_object_button = self._create_overlay_button(
            "zoom-active-object.svg",
            "Zoom to selected geometry",
        )
        self.rotate_view_button = self._create_overlay_button(
            "rotate-view.svg",
            "Rotate view 90 degrees clockwise (visual only; coordinates stay original)",
        )
        self.reset_rotation_button = self._create_overlay_button(
            "reset-rotation.svg",
            "Reset visual rotation",
        )
        self.exif_rotation_button = self._create_overlay_button(
            "rotate-exif.svg",
            "Reset visual rotation to imported EXIF orientation",
        )
        layout.addWidget(self.fit_image_button, 0, 1)
        layout.addWidget(self.zoom_active_object_button, 0, 2)
        layout.addWidget(self.smoothing_button, 0, 0)
        layout.addWidget(self.metadata_button, 2, 0)
        layout.addWidget(self.rotate_view_button, 1, 0)
        layout.addWidget(self.reset_rotation_button, 1, 1)
        layout.addWidget(self.exif_rotation_button, 1, 2)

        self.fit_image_button.clicked.connect(lambda _checked=False: self.fit_image())
        self.smoothing_button.clicked.connect(self.set_smooth_pixmap)
        self.metadata_button.clicked.connect(lambda _checked=False: self.metadataRequested.emit())
        self.zoom_active_object_button.clicked.connect(lambda _checked=False: self.zoom_to_active_object())
        self.rotate_view_button.clicked.connect(lambda _checked=False: self.rotate_visual_view())
        self.reset_rotation_button.clicked.connect(lambda _checked=False: self.reset_visual_rotation())
        self.exif_rotation_button.clicked.connect(lambda _checked=False: self.exifRotationRequested.emit())

        self.metadata_popup = ImageMetadataPopup(self)

        self.image_controls.setStyleSheet("""
            QWidget#imageViewerControls {
                background-color: rgba(48, 54, 65, 210);
                border: 1px solid rgb(90, 98, 112);
                border-radius: 5px;
            }
            QToolButton {
                background: rgb(150, 150, 150);
                border: 1px solid rgb(70, 78, 92);
                border-radius: 4px;
                padding: 2px;
            }
            QToolButton:hover {
                background: rgb(65, 74, 90);
            }
            QToolButton:pressed {
                background: rgb(90, 110, 135);
            }
            QToolButton:checked {
                background: rgb(58, 105, 78);
                border: 1px solid rgb(105, 150, 120);
            }
            QToolButton:checked:hover {
                background: rgb(68, 122, 90);
            }
            QToolButton:disabled {
                background: rgb(85, 85, 85);
            }
        """)
        self._create_ai_controls()
        self._create_polygon_brush_controls()
        self._position_overlay_buttons()
        self.image_controls.show()
        self.ai_controls.show()
        self.sync_overlay_buttons()

    def _create_polygon_brush_controls(self):
        self.polygon_brush_controls = QWidget(self)
        self.polygon_brush_controls.setObjectName("polygonBrushControls")
        self.polygon_brush_controls.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.polygon_brush_controls.setCursor(Qt.CursorShape.SizeAllCursor)
        self.polygon_brush_controls.installEventFilter(self)
        self.polygon_brush_controls.setStyleSheet(
            self.image_controls.styleSheet().replace("imageViewerControls", "polygonBrushControls")
            + "QToolButton:checked { color: rgb(235, 235, 235); }"
        )
        layout = QGridLayout(self.polygon_brush_controls)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)
        self.polygon_brush_button = QToolButton(self.polygon_brush_controls)
        self.polygon_brush_button.setIcon(resource_icon("smoothing-pixel.svg"))
        self.polygon_brush_button.setText("Polygon broom")
        self.polygon_brush_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.polygon_brush_button.setCheckable(True)
        self.polygon_brush_button.setToolTip("Sculpt a polygon's outer border. Escape or right-click cancels.")
        layout.addWidget(self.polygon_brush_button, 0, 0)
        self.polygon_brush_settings = QWidget(self.polygon_brush_controls)
        settings = QGridLayout(self.polygon_brush_settings)
        settings.setContentsMargins(0, 0, 0, 0)
        self.polygon_brush_expand = QToolButton(self.polygon_brush_settings)
        self.polygon_brush_shrink = QToolButton(self.polygon_brush_settings)
        self.polygon_brush_group = QButtonGroup(self)
        for column, (button, text, mode) in enumerate((
            (self.polygon_brush_expand, "Expand", "expand"),
            (self.polygon_brush_shrink, "Shrink", "shrink"),
        )):
            button.setText(text)
            button.setCheckable(True)
            self.polygon_brush_group.addButton(button)
            button.clicked.connect(lambda _checked=False, value=mode: self.polygonBrushModeChanged.emit(value))
            settings.addWidget(button, 0, column)
        self.polygon_brush_expand.setChecked(True)
        self.polygon_brush_slider = QSlider(Qt.Orientation.Horizontal, self.polygon_brush_settings)
        self.polygon_brush_slider.setRange(4, 200)
        self.polygon_brush_slider.setValue(16)
        self.polygon_brush_slider.setToolTip("Broom diameter in image pixels")
        self.polygon_brush_size_label = QLabel("16 px", self.polygon_brush_settings)
        self.polygon_brush_size_label.setStyleSheet("color: rgb(220, 220, 220); background: transparent;")
        settings.addWidget(self.polygon_brush_slider, 1, 0)
        settings.addWidget(self.polygon_brush_size_label, 1, 1)
        layout.addWidget(self.polygon_brush_settings, 1, 0)
        self.polygon_brush_settings.hide()
        self.polygon_brush_controls.hide()
        self.polygon_brush_button.toggled.connect(self._polygon_brush_toggled)
        self.polygon_brush_slider.valueChanged.connect(self._polygon_brush_size_changed)

    def _polygon_brush_toggled(self, enabled):
        self.polygon_brush_settings.setVisible(enabled)
        self._polygon_brush_cursor_pos = None
        self._position_overlay_buttons()
        self.viewport().update()
        self.polygonBrushToggled.emit(enabled)

    def _polygon_brush_size_changed(self, size):
        self.polygon_brush_size_label.setText(f"{size} px")
        self.polygonBrushSizeChanged.emit(size)
        self.viewport().update()

    def set_polygon_brush_checked(self, enabled):
        blocked = self.polygon_brush_button.blockSignals(True)
        self.polygon_brush_button.setChecked(enabled)
        self.polygon_brush_button.blockSignals(blocked)
        self.polygon_brush_settings.setVisible(enabled)
        if not enabled:
            self._polygon_brush_cursor_pos = None
        self._position_overlay_buttons()
        self.viewport().update()

    def sync_polygon_brush_controls(self):
        scene = self.scene()
        target = scene.polygon_brush_target() if hasattr(scene, "polygon_brush_target") else None
        eligible = target is not None and not scene.ai_mode_enabled
        self.polygon_brush_controls.setVisible(eligible)
        busy = bool(getattr(scene, "instruction_active", False))
        self.polygon_brush_button.setEnabled(eligible and not busy)
        self.polygon_brush_settings.setEnabled(not busy)
        if not eligible:
            self.set_polygon_brush_checked(False)
        self._position_overlay_buttons()

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        if self.polygon_brush_button.isChecked() and self._polygon_brush_cursor_pos is not None:
            painter.save()
            radius = self.polygon_brush_slider.value() / 2
            outline = QPen(QColor("#202832"), 3)
            outline.setCosmetic(True)
            painter.setPen(outline)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(self._polygon_brush_cursor_pos, radius, radius)
            pen = QPen(QColor("#f5f5f5"), 1)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(QColor(255, 255, 255, 25))
            painter.drawEllipse(self._polygon_brush_cursor_pos, radius, radius)
            painter.restore()

    def leaveEvent(self, event):
        self._polygon_brush_cursor_pos = None
        self.viewport().update()
        super().leaveEvent(event)

    def _create_ai_controls(self):
        self.ai_controls = QWidget(self)
        self.ai_controls.setObjectName("aiViewerControls")
        self.ai_controls.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.ai_controls.setCursor(Qt.CursorShape.SizeAllCursor)
        self.ai_controls.installEventFilter(self)

        layout = QGridLayout(self.ai_controls)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        self.ai_mode_button = self._create_ai_overlay_button("metadata-tools.svg", "AI segmentation view")
        self.ai_positive_point_button = self._create_ai_overlay_button("add_node.svg", "AI positive click")
        self.ai_negative_point_button = self._create_ai_overlay_button("remove_node.svg", "AI negative prompt")
        self.ai_rectangle_button = self._create_ai_overlay_button("rectangle.svg", "Add AI rectangle selection to mask")
        self.ai_background_button = self._create_ai_overlay_button(
            "smoothing-pixel.svg", "AI background brush: paint background, release to refine mask"
        )
        self.ai_mask_color_button = self._create_ai_color_button("AI mask color")
        self._update_ai_mask_color_button()
        self.ai_preclassification_button = self._create_ai_overlay_button(
            "preview-thumbnails.svg",
            "Show AI pre-classification",
        )
        self.ai_reset_button = self._create_ai_overlay_button("Flat_cross_icon.svg", "Reset AI mask")
        self.ai_polygon_button = self._create_ai_overlay_button(
            "polygon.svg",
            "Convert AI mask to one smooth polygon: the largest mask part (20 px outward buffer, up to 400 points, "
            "no holes)",
        )

        self.ai_mode_button.setCheckable(True)
        self.ai_positive_point_button.setCheckable(True)
        self.ai_negative_point_button.setCheckable(True)
        self.ai_rectangle_button.setCheckable(True)
        self.ai_background_button.setCheckable(True)
        self.ai_preclassification_button.setCheckable(True)
        self.ai_positive_point_button.setChecked(True)

        self.ai_tool_group = QButtonGroup(self)
        self.ai_tool_group.setExclusive(True)
        self.ai_tool_group.addButton(self.ai_positive_point_button)
        self.ai_tool_group.addButton(self.ai_negative_point_button)
        self.ai_tool_group.addButton(self.ai_rectangle_button)
        self.ai_tool_group.addButton(self.ai_background_button)

        layout.addWidget(self.ai_mode_button, 0, 0)
        layout.addWidget(self.ai_positive_point_button, 0, 1)
        layout.addWidget(self.ai_negative_point_button, 0, 2)
        layout.addWidget(self.ai_rectangle_button, 1, 0)
        layout.addWidget(self.ai_background_button, 1, 1)
        layout.addWidget(self.ai_preclassification_button, 1, 2)
        layout.addWidget(self.ai_reset_button, 2, 0)
        layout.addWidget(self.ai_mask_color_button, 2, 1)
        layout.addWidget(self.ai_polygon_button, 2, 2)

        self.ai_backend_combo = self._create_ai_combo(
            "AI segmentation model. Changing it loads the model in the background."
        )
        self.ai_device_combo = self._create_ai_combo("Processing device. CPU is used when a GPU fails.")
        layout.addWidget(self.ai_backend_combo, 3, 0, 1, 3)
        layout.addWidget(self.ai_device_combo, 4, 0, 1, 3)
        self.ai_backend_combo.activated.connect(
            lambda _index: self.aiBackendChanged.emit(str(self.ai_backend_combo.currentData()))
        )
        self.ai_device_combo.activated.connect(
            lambda _index: self.aiDeviceChanged.emit(str(self.ai_device_combo.currentData()))
        )

        self.ai_mode_button.toggled.connect(self._ai_mode_toggled)
        self.ai_positive_point_button.clicked.connect(lambda _checked=False: self.aiToolChanged.emit("positive_point"))
        self.ai_negative_point_button.clicked.connect(lambda _checked=False: self.aiToolChanged.emit("negative_point"))
        self.ai_rectangle_button.clicked.connect(lambda _checked=False: self.aiToolChanged.emit("rectangle"))
        self.ai_background_button.clicked.connect(lambda _checked=False: self.aiToolChanged.emit("background"))
        self.ai_preclassification_button.toggled.connect(self.aiPreclassificationChanged)
        self.ai_reset_button.clicked.connect(lambda _checked=False: self.aiResetRequested.emit())
        self.ai_polygon_button.clicked.connect(lambda _checked=False: self.aiPolygonRequested.emit())
        self.ai_mask_color_button.clicked.connect(self._choose_ai_mask_color)

        self.ai_controls.setStyleSheet("""
            QWidget#aiViewerControls {
                background-color: rgba(36, 62, 74, 215);
                border: 1px solid rgb(80, 118, 132);
                border-radius: 5px;
            }
            QToolButton {
                background: rgb(150, 150, 150);
                border: 1px solid rgb(70, 78, 92);
                border-radius: 4px;
                padding: 2px;
            }
            QToolButton:hover {
                background: rgb(65, 86, 96);
            }
            QToolButton:pressed {
                background: rgb(92, 116, 128);
            }
            QToolButton:checked {
                background: rgb(58, 105, 118);
                border: 1px solid rgb(105, 160, 175);
            }
            QToolButton:checked:hover {
                background: rgb(66, 122, 138);
            }
            QToolButton:disabled {
                background: rgb(85, 85, 85);
            }
            QComboBox {
                background: rgb(52, 59, 72);
                color: rgb(230, 230, 230);
                border: 1px solid rgb(70, 78, 92);
                border-radius: 4px;
                padding: 1px 4px;
                font-size: 8pt;
            }
            QComboBox QAbstractItemView {
                background: rgb(40, 44, 52);
                color: rgb(230, 230, 230);
                selection-background-color: rgb(58, 105, 118);
            }
        """)

    def _create_ai_overlay_button(self, icon_name, tooltip):
        button = QToolButton(self.ai_controls)
        button.setIcon(resource_icon(icon_name))
        button.setIconSize(QSize(22, 22))
        button.setFixedSize(30, 30)
        button.setToolTip(tooltip)
        button.setAutoRaise(False)
        return button

    def _create_ai_combo(self, tooltip):
        combo = QComboBox(self.ai_controls)
        combo.setToolTip(tooltip)
        combo.setFixedWidth(98)
        combo.setCursor(Qt.CursorShape.ArrowCursor)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.view().setMinimumWidth(220)
        return combo

    @staticmethod
    def _set_combo_options(combo, options, current):
        combo.blockSignals(True)
        combo.clear()
        for key, label in options:
            combo.addItem(label, key)
            combo.setItemData(combo.count() - 1, label, Qt.ItemDataRole.ToolTipRole)
        index = combo.findData(current)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def set_ai_backend_options(self, options, current):
        self._set_combo_options(self.ai_backend_combo, options, current)

    def set_ai_device_options(self, options, current):
        self._set_combo_options(self.ai_device_combo, options, current)

    def _create_ai_color_button(self, tooltip):
        button = QToolButton(self.ai_controls)
        button.setFixedSize(30, 30)
        button.setToolTip(tooltip)
        button.setAutoRaise(False)
        return button

    def _choose_ai_mask_color(self):
        color = QColorDialog.getColor(self._ai_mask_color, self, "AI mask color")
        if not color.isValid():
            return
        self._ai_mask_color = color
        self._update_ai_mask_color_button()
        self.aiMaskColorChanged.emit(color)

    def _update_ai_mask_color_button(self):
        if not hasattr(self, "ai_mask_color_button"):
            return
        self.ai_mask_color_button.setStyleSheet(
            f"""
            QToolButton {{
                background-color: {self._ai_mask_color.name()};
                border: 1px solid rgb(70, 78, 92);
                border-radius: 4px;
            }}
            QToolButton:hover {{
                border: 1px solid rgb(220, 220, 220);
            }}
            QToolButton:disabled {{
                background-color: rgb(85, 85, 85);
            }}
            """
        )

    def _create_overlay_button(self, icon_name, tooltip):
        button = QToolButton(self.image_controls)
        button.setIcon(resource_icon(icon_name))
        button.setIconSize(QSize(22, 22))
        button.setFixedSize(30, 30)
        button.setToolTip(tooltip)
        button.setAutoRaise(False)
        return button

    def eventFilter(self, source, event):
        if source is getattr(self, "polygon_brush_controls", None):
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._brush_overlay_drag_pos = event.position().toPoint()
                return True
            if event.type() == QEvent.Type.MouseMove and self._brush_overlay_drag_pos is not None:
                target = self.polygon_brush_controls.pos() + event.position().toPoint() - self._brush_overlay_drag_pos
                self._brush_overlay_user_pos = self._clamped_overlay_pos(target, self.polygon_brush_controls)
                self.polygon_brush_controls.move(self._brush_overlay_user_pos)
                return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self._brush_overlay_drag_pos = None
                return True
        if source is self.image_controls:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._overlay_drag_pos = event.position().toPoint()
                event.accept()
                return True
            if event.type() == QEvent.Type.MouseMove and self._overlay_drag_pos is not None:
                target = self.image_controls.pos() + event.position().toPoint() - self._overlay_drag_pos
                self._overlay_user_pos = self._clamped_overlay_pos(target)
                self.image_controls.move(self._overlay_user_pos)
                if self.metadata_popup.isVisible():
                    self._position_metadata_popup()
                    self.metadata_popup.raise_()
                event.accept()
                return True
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self._overlay_drag_pos = None
                event.accept()
                return True
        if source is getattr(self, "ai_controls", None):
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._ai_overlay_drag_pos = event.position().toPoint()
                event.accept()
                return True
            if event.type() == QEvent.Type.MouseMove and self._ai_overlay_drag_pos is not None:
                target = self.ai_controls.pos() + event.position().toPoint() - self._ai_overlay_drag_pos
                self._ai_overlay_user_pos = self._clamped_overlay_pos(target, self.ai_controls)
                self.ai_controls.move(self._ai_overlay_user_pos)
                event.accept()
                return True
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self._ai_overlay_drag_pos = None
                event.accept()
                return True
        return super().eventFilter(source, event)

    def _ai_mode_toggled(self, enabled):
        self.sync_ai_buttons()
        self.aiModeChanged.emit(enabled)

    def set_ai_mode_checked(self, enabled):
        self.ai_mode_button.setChecked(bool(enabled))

    def set_ai_preclassification_checked(self, checked):
        self.ai_preclassification_button.setChecked(bool(checked))

    def reset_ai_controls(self):
        self.ai_mode_button.setChecked(False)
        self.ai_positive_point_button.setChecked(True)
        self.ai_preclassification_button.setChecked(False)
        self.aiToolChanged.emit("positive_point")
        self.aiModeChanged.emit(False)
        self.aiPreclassificationChanged.emit(False)
        self.sync_ai_buttons()

    def set_smooth_pixmap(self, enabled):
        self._smooth_pixmap = bool(enabled)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self._smooth_pixmap)
        self.apply_smooth_pixmap_to_scene()
        self._sync_smoothing_button_icon()
        self.viewport().update()

    def apply_smooth_pixmap_to_scene(self):
        scene = self.scene()
        image_item = getattr(scene, "image_item", None) if scene is not None else None
        if image_item is not None:
            mode = (
                Qt.TransformationMode.SmoothTransformation
                if self._smooth_pixmap
                else Qt.TransformationMode.FastTransformation
            )
            image_item.setTransformationMode(mode)

    def smooth_pixmap(self):
        return self._smooth_pixmap

    def _sync_smoothing_button_icon(self):
        if self._smooth_pixmap:
            self.smoothing_button.setIcon(resource_icon("smoothing-active.svg"))
            self.smoothing_button.setToolTip("Smooth image scaling")
        else:
            self.smoothing_button.setIcon(resource_icon("smoothing-pixel.svg"))
            self.smoothing_button.setToolTip("Direct pixel scaling")

    def mousePressEvent(self, event):
        if self.polygon_brush_button.isChecked():
            self._polygon_brush_cursor_pos = self.mapToScene(event.position().toPoint())
            self.viewport().update()
        # print(event.pos())
        self._dragPos = event.position()
        if event.button() == Qt.MiddleButton:
            self.middlePressed = True
            QApplication.setOverrideCursor(Qt.ClosedHandCursor)
        if event.button() == Qt.RightButton:
            self.rightPressed = True
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.middlePressed = False
            # QApplication.restoreOverrideCursor()
            # QApplication.restoreOverrideCursor()
            QApplication.restoreOverrideCursor()
        if event.button() == Qt.RightButton:
            self.rightPressed = False
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self.polygon_brush_button.isChecked():
            self._polygon_brush_cursor_pos = self.mapToScene(event.position().toPoint())
            self.viewport().update()

        new_pos = event.position()
        if self.middlePressed:
            diff = new_pos - self._dragPos
            self._dragPos = new_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - diff.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - diff.y())
            event.accept()
        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        num_degrees = event.angleDelta().y() / 10
        num_steps = num_degrees / 15.0
        # event.scenePos
        # self.centerOn(self.mapToScene(event.pos()))
        old_mouse_img_coo = self.mapToScene(event.position().toPoint())
        diff_vec = event.position() - QPoint(int(self.width() / 2), int(self.height() / 2))
        self.zoom(pow(0.8, num_steps))
        new_middle_map_pos = self.mapFromScene(old_mouse_img_coo).toPointF() - diff_vec
        self.centerOn(self.mapToScene(new_middle_map_pos.toPoint()))

    def zoom_in(self):
        self.zoom(DIGITIZERView.factor)

    def zoom_out(self):
        self.zoom(1 / DIGITIZERView.factor)

    def zoom(self, f):
        self._auto_fit_on_resize = False

        scale = self._view_scale()
        if scale < 60 and f > 1:
            self.scale(f, f)
        if scale > 0.01 and f < 1:
            self.scale(f, f)
        self._position_overlay_buttons()
        # if self.scene() is not None:
        # self.centerOn(self.scene().image_item)

    def fitInView(self, *args):
        if not args or args[0] is None or not self._scene_has_items():
            self._auto_fit_on_resize = False
            self.sync_overlay_buttons()
            return None
        return self._fit_in_view_with_visual_rotation(*args, auto_fit=True)

    def fit_image(self):
        image_item = self._fit_image_target()
        if image_item is None:
            self._auto_fit_on_resize = False
            self.sync_overlay_buttons()
            return
        self.fitInView(image_item, Qt.KeepAspectRatio)
        self.sync_overlay_buttons()

    def zoom_to_active_object(self):
        item = self._active_geometry_target()
        if item is None:
            self.sync_overlay_buttons()
            return

        rect = item.sceneBoundingRect()
        scene_rect = self.scene().sceneRect()
        padding = max(
            max(rect.width(), rect.height()) * 0.2,
            max(scene_rect.width(), scene_rect.height()) * 0.005,
            10.0,
        )
        target = QRectF(rect).adjusted(-padding, -padding, padding, padding)
        image_rect = self._fit_image_rect()
        if image_rect is not None:
            clamped_target = target.intersected(image_rect)
            if not clamped_target.isEmpty():
                target = clamped_target

        self._auto_fit_on_resize = False
        self._fit_in_view_with_visual_rotation(target, Qt.KeepAspectRatio, auto_fit=False)

    def active_object_fully_visible(self):
        item = self._active_geometry_target()
        if item is None:
            return False

        rect = QRectF(item.sceneBoundingRect())
        if rect.isNull() or rect.isEmpty():
            return False

        viewport_polygon = self.mapToScene(self.viewport().rect())
        points = (
            rect.topLeft(),
            QPointF(rect.right(), rect.top()),
            rect.bottomRight(),
            QPointF(rect.left(), rect.bottom()),
        )
        return all(viewport_polygon.containsPoint(point, Qt.FillRule.WindingFill) for point in points)

    def _fit_in_view_with_visual_rotation(self, *args, auto_fit):
        self._auto_fit_on_resize = auto_fit
        self.setTransform(QTransform())
        self._apply_visual_rotation_to_transform()
        result = super().fitInView(*args)
        self.sync_overlay_buttons()
        return result

    def rotate_visual_view(self):
        self.set_visual_rotation(self._visual_rotation_degrees + 90)

    def reset_visual_rotation(self):
        self.set_visual_rotation(0)

    def set_visual_rotation(self, degrees, emit_signal=True):
        degrees = int(degrees) % 360
        if degrees == self._visual_rotation_degrees:
            self.sync_overlay_buttons()
            return

        center = self._viewport_scene_center()
        scale = self._view_scale()
        self._visual_rotation_degrees = degrees
        self.setTransform(QTransform())
        self.scale(scale, scale)
        self._apply_visual_rotation_to_transform()
        if center is not None:
            self.centerOn(center)
        self.sync_overlay_buttons()
        if emit_signal:
            self.visualRotationChanged.emit(degrees)

    def visual_rotation(self):
        return self._visual_rotation_degrees

    def set_exif_rotation_available(self, available):
        self._exif_rotation_available = bool(available)
        self.sync_overlay_buttons()

    def _apply_visual_rotation_to_transform(self):
        if self._visual_rotation_degrees:
            self.rotate(self._visual_rotation_degrees)

    def _view_scale(self):
        determinant = abs(self.transform().determinant())
        if determinant <= 0:
            return 1.0
        return determinant**0.5

    def _viewport_scene_center(self):
        scene = self.scene()
        if scene is None:
            return None
        return self.mapToScene(self.viewport().rect().center())

    def _fit_image_target(self):
        scene = self.scene()
        if scene is None:
            return None

        image_item = getattr(scene, "image_item", None)
        if image_item is None:
            return None

        try:
            if image_item.scene() is not scene:
                return None
            if image_item.pixmap().isNull():
                return None
            if image_item.boundingRect().isNull():
                return None
        except RuntimeError:
            return None
        return image_item

    def _fit_image_rect(self):
        image_item = self._fit_image_target()
        if image_item is None:
            return None
        try:
            image_rect = image_item.sceneBoundingRect()
        except RuntimeError:
            return None
        if not image_rect.isValid() or image_rect.isEmpty():
            return None
        return image_rect

    def _active_geometry_target(self):
        scene = self.scene()
        if scene is None:
            return None

        active_geometry_item = getattr(scene, "active_geometry_item", None)
        item = active_geometry_item() if callable(active_geometry_item) else getattr(scene, "active_item", None)
        if item is None:
            return None

        try:
            if item.scene() is not scene:
                return None
            if not hasattr(item, "object_type"):
                return None
            rect = item.sceneBoundingRect()
            if not rect.isValid() or rect.isEmpty():
                return None
        except RuntimeError:
            return None
        return item

    def sync_overlay_buttons(self):
        has_image = self._fit_image_target() is not None
        self.fit_image_button.setEnabled(has_image)
        self.smoothing_button.setEnabled(has_image)
        self.smoothing_button.setChecked(self._smooth_pixmap)
        self._sync_smoothing_button_icon()
        self.metadata_button.setEnabled(has_image)
        self.zoom_active_object_button.setEnabled(self._active_geometry_target() is not None)
        self.rotate_view_button.setEnabled(has_image)
        self.reset_rotation_button.setEnabled(has_image and self._visual_rotation_degrees != 0)
        self.exif_rotation_button.setEnabled(has_image and self._exif_rotation_available)
        if not has_image:
            self.hide_metadata_popup()
        self.sync_ai_buttons()
        self.sync_polygon_brush_controls()

    def sync_ai_buttons(self):
        has_image = self._fit_image_target() is not None
        ai_enabled = has_image and self.ai_mode_button.isChecked() and not self._ai_initializing
        self.ai_mode_button.setEnabled(has_image)
        self.ai_positive_point_button.setEnabled(ai_enabled)
        self.ai_negative_point_button.setEnabled(ai_enabled)
        self.ai_rectangle_button.setEnabled(ai_enabled)
        self.ai_background_button.setEnabled(ai_enabled)
        self.ai_preclassification_button.setEnabled(ai_enabled)
        self.ai_reset_button.setEnabled(ai_enabled)
        self.ai_polygon_button.setEnabled(ai_enabled)
        self.ai_mask_color_button.setEnabled(ai_enabled)
        if not has_image and self.ai_mode_button.isChecked():
            self.ai_mode_button.setChecked(False)

    def set_ai_initializing(self, initializing):
        self._ai_initializing = bool(initializing)
        self.ai_mode_button.setToolTip(
            "Preparing segmentation model... Click to use AI as soon as it is ready."
            if initializing else "AI segmentation view"
        )
        self.sync_ai_buttons()

    def toggle_metadata_popup(self, metadata):
        if self.metadata_popup.isVisible():
            self.hide_metadata_popup()
            return
        self.show_metadata_popup(metadata)

    def show_metadata_popup(self, metadata):
        self.metadata_popup.set_metadata(metadata)
        self.metadata_popup.show()
        self.metadata_button.setChecked(True)
        self._position_metadata_popup()
        self.metadata_popup.raise_()

    def hide_metadata_popup(self):
        self.metadata_popup.hide()
        self.metadata_button.setChecked(False)

    def _position_overlay_buttons(self):
        self.image_controls.adjustSize()
        if self._overlay_user_pos is None:
            viewport_top_left = self.viewport().geometry().topLeft()
            target = QPoint(viewport_top_left.x() + self._overlay_margin, viewport_top_left.y() + self._overlay_margin)
        else:
            target = self._overlay_user_pos
        self._overlay_user_pos = (
            None if self._overlay_user_pos is None else self._clamped_overlay_pos(target, self.image_controls)
        )
        self.image_controls.move(self._clamped_overlay_pos(target, self.image_controls))
        self.image_controls.raise_()
        self.ai_controls.adjustSize()
        if self._ai_overlay_user_pos is None:
            viewport_rect = self.viewport().geometry()
            target = QPoint(
                viewport_rect.right() - self.ai_controls.width() - self._overlay_margin + 1,
                viewport_rect.top() + self._overlay_margin,
            )
        else:
            target = self._ai_overlay_user_pos
        self._ai_overlay_user_pos = (
            None if self._ai_overlay_user_pos is None else self._clamped_overlay_pos(target, self.ai_controls)
        )
        self.ai_controls.move(self._clamped_overlay_pos(target, self.ai_controls))
        self.ai_controls.raise_()
        self.polygon_brush_controls.adjustSize()
        viewport_rect = self.viewport().geometry()
        target = self._brush_overlay_user_pos or QPoint(
            viewport_rect.right() - self.polygon_brush_controls.width() - self._overlay_margin + 1,
            viewport_rect.bottom() - self.polygon_brush_controls.height() - self._overlay_margin + 1,
        )
        self.polygon_brush_controls.move(self._clamped_overlay_pos(target, self.polygon_brush_controls))
        self.polygon_brush_controls.raise_()
        if self.metadata_popup.isVisible():
            self._position_metadata_popup()
            self.metadata_popup.raise_()

    def reset_overlay_position(self):
        self._brush_overlay_user_pos = None
        self._brush_overlay_drag_pos = None
        self._overlay_user_pos = None
        self._overlay_drag_pos = None
        self._ai_overlay_user_pos = None
        self._ai_overlay_drag_pos = None
        self._position_overlay_buttons()

    def _clamped_overlay_pos(self, target, widget=None):
        widget = widget or self.image_controls
        viewport_rect = self.viewport().geometry()
        widget.adjustSize()
        max_x = viewport_rect.right() - widget.width() + 1
        max_y = viewport_rect.bottom() - widget.height() + 1
        min_x = viewport_rect.left()
        min_y = viewport_rect.top()
        return QPoint(
            max(min_x, min(target.x(), max_x)),
            max(min_y, min(target.y(), max_y)),
        )

    def _position_metadata_popup(self):
        viewport_rect = self.viewport().geometry()
        margin = 10
        width = min(620, max(1, viewport_rect.width() - 2 * margin))
        height = min(360, max(1, viewport_rect.height() - 2 * margin))
        self.metadata_popup.resize(width, height)
        x = viewport_rect.left() + margin
        y = viewport_rect.bottom() - margin - height + 1
        self.metadata_popup.move(x, y)

    def _scene_has_items(self):
        scene = self.scene()
        return scene is not None and len(scene.items()) > 0

    # EVENT Resize
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_overlay_buttons()
        self.sync_overlay_buttons()
        if self._auto_fit_on_resize and self._scene_has_items():
            image_item = self._fit_image_target()
            if image_item is not None:
                self.fitInView(image_item, Qt.KeepAspectRatio)

    def showEvent(self, event):
        super().showEvent(event)
        self._position_overlay_buttons()
        self.image_controls.show()
        self.ai_controls.show()
        self.sync_overlay_buttons()
