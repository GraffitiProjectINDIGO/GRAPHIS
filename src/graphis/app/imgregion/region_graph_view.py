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

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QGraphicsView, QHBoxLayout, QLabel, QToolButton, QWidget

from graphis.app.gui.resources import icon as resource_icon


class RegionGraphView(QGraphicsView):
    autoLayoutRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        # self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self._panning = False
        self._last_pos = None
        self._fit_pending = False
        self._install_graph_controls()
        self._install_validation_overlay()

    def showEvent(self, event):
        super().showEvent(event)
        self._position_graph_controls()
        self._position_validation_overlay()
        self._sync_graph_controls()
        if self._fit_pending:
            QTimer.singleShot(0, self.fit_graph)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_graph_controls()
        self._position_validation_overlay()
        self._sync_graph_controls()
        if self._fit_pending:
            QTimer.singleShot(0, self.fit_graph)

    def wheelEvent(self, event):
        factor = 1.18 if event.angleDelta().y() > 0 else 1 / 1.18
        current = self.transform().m11()
        next_scale = current * factor
        if factor > 1 and next_scale <= 8.0:
            self.scale(factor, factor)
            self._position_graph_controls()
            self._position_validation_overlay()
            return
        if factor < 1 and next_scale >= 0.02:
            self.scale(factor, factor)
        self._position_graph_controls()
        self._position_validation_overlay()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._last_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning and self._last_pos is not None:
            delta = event.position() - self._last_pos
            self._last_pos = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self._last_pos = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def fit_graph(self):
        scene = self.scene()
        if scene and scene.items():
            if self.viewport().width() < 20 or self.viewport().height() < 20:
                self._fit_pending = True
                return
            if hasattr(scene, "update_scene_rect"):
                scene.update_scene_rect()
            self.fitInView(scene.itemsBoundingRect().adjusted(-80, -80, 80, 80), Qt.AspectRatioMode.KeepAspectRatio)
            self._fit_pending = False
        self._sync_graph_controls()

    def set_validation_issues(self, issues):
        issues = list(issues or [])
        errors = [issue for issue in issues if getattr(issue, "severity", "") == "error"]
        warnings = [issue for issue in issues if getattr(issue, "severity", "") == "warning"]
        self._set_validation_overlay(self.error_validation_overlay, self.error_message_label, errors)
        self._set_validation_overlay(self.warning_validation_overlay, self.warning_message_label, warnings)
        self._position_validation_overlay()

    def _install_graph_controls(self):
        self.graph_controls = QWidget(self)
        self.graph_controls.setObjectName("regionGraphControls")
        self.graph_controls.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self.graph_controls)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        self.fit_graph_button = self._create_graph_control_button("fit-graph.svg", "Fit graph")
        self.auto_layout_button = self._create_graph_control_button("auto-layout-graph.svg", "Auto layout graph")
        layout.addWidget(self.fit_graph_button)
        layout.addWidget(self.auto_layout_button)

        self.fit_graph_button.clicked.connect(lambda _checked=False: self.fit_graph())
        self.auto_layout_button.clicked.connect(lambda _checked=False: self.autoLayoutRequested.emit())

        self.graph_controls.setStyleSheet("""
            QWidget#regionGraphControls {
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
            QToolButton:disabled {
                background: rgb(85, 85, 85);
            }
        """)
        self._position_graph_controls()
        self._sync_graph_controls()

    def _install_validation_overlay(self):
        self.error_validation_overlay, self.error_message_label = self._create_validation_overlay(
            "regionGraphErrorOverlay",
            "Errors",
            "#e45b5b",
            "rgba(56, 32, 38, 230)",
        )
        self.warning_validation_overlay, self.warning_message_label = self._create_validation_overlay(
            "regionGraphWarningOverlay",
            "Warnings",
            "#d9a441",
            "rgba(52, 44, 28, 230)",
        )

    def _create_validation_overlay(self, object_name, title, color, background):
        overlay = QWidget(self)
        overlay.setObjectName(object_name)
        overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(overlay)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(5)

        title_label = QLabel(f"{title}:", overlay)
        title_label.setObjectName("regionGraphValidationTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        message_label = QLabel(overlay)
        message_label.setObjectName("regionGraphValidationMessage")
        message_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        layout.addWidget(title_label)
        layout.addWidget(message_label, 1)
        overlay.setStyleSheet(self._validation_overlay_style(object_name, color, background))
        overlay.hide()
        return overlay, message_label

    def _validation_overlay_style(self, object_name, color, background):
        return f"""
            QWidget#{object_name} {{
                background-color: {background};
                border: 1px solid {color};
            }}
            QLabel#regionGraphValidationTitle {{
                color: {color};
                font: 700 8pt "Segoe UI";
                background: transparent;
            }}
            QLabel#regionGraphValidationMessage {{
                color: rgb(235, 238, 242);
                font: 8pt "Segoe UI";
                background: transparent;
            }}
        """

    def _set_validation_overlay(self, overlay, message_label, issues):
        if not issues:
            overlay.hide()
            return

        lines = []
        for issue in issues[:4]:
            code = getattr(issue, "code", "")
            message = getattr(issue, "message", "")
            lines.append(f"{code}: {message}" if code else message)
        if len(issues) > 4:
            lines.append(f"{len(issues) - 4} more...")
        message_label.setText("\n".join(lines))
        overlay.show()

    def _create_graph_control_button(self, icon_name, tooltip):
        button = QToolButton(self.graph_controls)
        button.setIcon(resource_icon(icon_name))
        button.setIconSize(QSize(22, 22))
        button.setFixedSize(30, 30)
        button.setToolTip(tooltip)
        button.setAutoRaise(False)
        return button

    def _position_graph_controls(self):
        self.graph_controls.adjustSize()
        top_left = self.viewport().geometry().topLeft()
        self.graph_controls.move(top_left.x() + 10, top_left.y() + 10)
        self.graph_controls.raise_()

    def _position_validation_overlay(self):
        if not hasattr(self, "error_validation_overlay"):
            return
        viewport_rect = self.viewport().geometry()
        width = viewport_rect.width()
        x = viewport_rect.left()
        y = viewport_rect.bottom() + 1

        # Position from bottom to top: warnings at the bottom, errors above.
        for overlay in (self.warning_validation_overlay, self.error_validation_overlay):
            if overlay.isHidden():
                continue
            overlay.setFixedWidth(width)
            height = self._validation_overlay_height(overlay, width)
            y -= height + 2
            overlay.setGeometry(x, max(viewport_rect.top(), y), width, height)
            overlay.raise_()

    def _validation_overlay_height(self, overlay, width):
        layout = overlay.layout()
        margins = layout.contentsMargins()
        title_label = layout.itemAt(0).widget()
        message_label = layout.itemAt(1).widget()
        title_width = title_label.sizeHint().width()
        message_width = max(20, width - margins.left() - margins.right() - layout.spacing() - title_width)

        if message_label.wordWrap():
            message_rect = message_label.fontMetrics().boundingRect(
                0,
                0,
                message_width,
                10000,
                Qt.TextFlag.TextWordWrap,
                message_label.text(),
            )
            message_height = message_rect.height()
        else:
            message_height = message_label.fontMetrics().height()

        content_height = max(title_label.fontMetrics().height(), message_height)
        return content_height + margins.top() + margins.bottom() + 2

    def _sync_graph_controls(self):
        scene = self.scene()
        enabled = scene is not None and bool(scene.items())
        self.fit_graph_button.setEnabled(enabled)
        self.auto_layout_button.setEnabled(enabled)
