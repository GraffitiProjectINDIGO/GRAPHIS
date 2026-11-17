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

from PySide6.QtCore import QEvent, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import QDockWidget, QMainWindow, QVBoxLayout, QWidget

from graphis.app.gui.resources import icon as resource_icon

_UNBOUNDED_SIZE = 16777215


class GraphDockWidget(QDockWidget):
    layoutSettled = Signal()
    toggleRequested = Signal()

    def __init__(
        self,
        title,
        parent=None,
        *,
        docked_preferred_width=1000,
        docked_min_width=400,
        docked_max_width=1200,
        docked_preferred_height=520,
        docked_min_height=260,
        docked_max_height=720,
        floating_default_size=None,
        floating_min_size=None,
    ):
        super().__init__(title, parent)
        self._docked_preferred_width = docked_preferred_width
        self._docked_min_width = docked_min_width
        self._docked_max_width = docked_max_width
        self._docked_preferred_height = docked_preferred_height
        self._docked_min_height = docked_min_height
        self._docked_max_height = docked_max_height
        self._floating_default_size = floating_default_size or QSize(980, 720)
        self._floating_min_size = floating_min_size or QSize(560, 420)
        self._layout_settle_timer = QTimer(self)
        self._layout_settle_timer.setSingleShot(True)
        self._layout_settle_timer.timeout.connect(self.layoutSettled.emit)

        self.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetClosable)
        self.topLevelChanged.connect(self._handle_dock_state_changed)
        self.visibilityChanged.connect(self._handle_visibility_changed)
        self.dockLocationChanged.connect(self._handle_dock_location_changed)
        self._apply_size_constraints()

    def event(self, event):
        if self.isFloating() and event.type() in (
            QEvent.Type.MouseButtonDblClick,
            QEvent.Type.NonClientAreaMouseButtonDblClick,
        ):
            event.accept()
            return True

        if event.type() in (
            QEvent.Type.Show,
            QEvent.Type.Resize,
            QEvent.Type.Move,
            QEvent.Type.WindowStateChange,
        ):
            self.request_layout_settled()
        return super().event(event)

    def mouseDoubleClickEvent(self, event):
        if self.isFloating():
            event.accept()
            return
        if self._is_title_bar_event(event):
            self.toggleRequested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def show_or_raise(self, default_area=Qt.DockWidgetArea.RightDockWidgetArea):
        main_window = self._main_window()
        if main_window is not None and not self.isFloating():
            if main_window.dockWidgetArea(self) == Qt.DockWidgetArea.NoDockWidgetArea:
                main_window.addDockWidget(default_area, self)

        self._apply_size_constraints()
        self.show()
        self.raise_()
        if self.isFloating():
            self.activateWindow()
        self.request_layout_settled()

    def dock_to(self, area=Qt.DockWidgetArea.RightDockWidgetArea):
        main_window = self._main_window()
        if main_window is not None:
            main_window.addDockWidget(area, self)
        self.setFloating(False)
        self.show_or_raise(area)
        self.restore_preferred_docked_size(area)

    def float_window(self):
        self.setFloating(True)
        self._apply_size_constraints()
        if self.width() < self._floating_default_size.width() or self.height() < self._floating_default_size.height():
            self.resize(self._floating_default_size.expandedTo(self.minimumSize()))
        self.show()
        self.raise_()
        self.activateWindow()
        self.request_layout_settled()

    def restore_preferred_docked_size(self, area=None):
        main_window = self._main_window()
        if main_window is None or self.isFloating():
            return

        area = area or main_window.dockWidgetArea(self)
        if area in (
            Qt.DockWidgetArea.LeftDockWidgetArea,
            Qt.DockWidgetArea.RightDockWidgetArea,
        ):
            size = self._docked_preferred_width
            orientation = Qt.Orientation.Horizontal
        elif area in (
            Qt.DockWidgetArea.TopDockWidgetArea,
            Qt.DockWidgetArea.BottomDockWidgetArea,
        ):
            size = self._docked_preferred_height
            orientation = Qt.Orientation.Vertical
        else:
            return

        main_window.resizeDocks([self], [size], orientation)
        self.request_layout_settled()

    def request_layout_settled(self, delay=0):
        self._layout_settle_timer.start(delay)

    def _handle_dock_state_changed(self, _is_floating):
        self._apply_size_constraints()
        self.request_layout_settled()

    def _handle_visibility_changed(self, _is_visible):
        self._apply_size_constraints()
        self.request_layout_settled()

    def _handle_dock_location_changed(self, area):
        self._apply_size_constraints(area)
        self.request_layout_settled()

    def _apply_size_constraints(self, area=None):
        if self.isFloating():
            self.setMinimumSize(self._floating_min_size)
            self.setMaximumSize(QSize(_UNBOUNDED_SIZE, _UNBOUNDED_SIZE))
            return

        area = area or self._dock_area()
        if area in (
            Qt.DockWidgetArea.LeftDockWidgetArea,
            Qt.DockWidgetArea.RightDockWidgetArea,
        ):
            self.setMinimumSize(QSize(self._docked_min_width, 0))
            self.setMaximumSize(QSize(self._docked_max_width, _UNBOUNDED_SIZE))
            return

        if area in (
            Qt.DockWidgetArea.TopDockWidgetArea,
            Qt.DockWidgetArea.BottomDockWidgetArea,
        ):
            self.setMinimumSize(QSize(0, self._docked_min_height))
            self.setMaximumSize(QSize(_UNBOUNDED_SIZE, self._docked_max_height))
            return

        self.setMinimumSize(QSize(0, 0))
        self.setMaximumSize(QSize(_UNBOUNDED_SIZE, _UNBOUNDED_SIZE))

    def _dock_area(self):
        main_window = self._main_window()
        if main_window is None:
            return Qt.DockWidgetArea.NoDockWidgetArea
        return main_window.dockWidgetArea(self)

    def _is_title_bar_event(self, event):
        pos = event.position().toPoint()
        return self._title_bar_hit_rect().contains(pos)

    def _title_bar_hit_rect(self):
        content_widget = self.widget()
        if content_widget is not None:
            content_rect = content_widget.geometry()
            if content_rect.top() > 0:
                return QRect(0, 0, self.width(), content_rect.top())
            if content_rect.left() > 0:
                return QRect(0, 0, content_rect.left(), self.height())
        return QRect(0, 0, self.width(), 28).intersected(self.rect())

    def _main_window(self):
        parent = self.parentWidget()
        while parent is not None:
            if isinstance(parent, QMainWindow):
                return parent
            parent = parent.parentWidget()
        return None


class RegionEditorPopoutWindow(QWidget):
    dockRequested = Signal()

    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.Window
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint,
        )

        self.setWindowIcon(resource_icon("icon.png"))
        self.setStyleSheet("background-color: rgb(40, 44, 52);")
        self.setWindowTitle("Region graph")
        self.setObjectName("regionGraphPopout")
        self.setMinimumSize(QSize(560, 420))
        self.resize(980, 720)
        self._editor = None
        self._force_close = False
        self._docking_from_minimize = False

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def set_editor(self, editor):
        if self._editor is editor:
            return
        if self._editor is not None:
            self._layout.removeWidget(self._editor)
        self._editor = editor
        self._layout.addWidget(editor, 1)
        editor.show()

    def has_editor(self):
        return self._editor is not None

    def take_editor(self):
        editor = self._editor
        if editor is not None:
            self._layout.removeWidget(editor)
            editor.setParent(None)
            self._editor = None
        return editor

    def force_close(self):
        self._force_close = True
        self.close()

    def normalize_window_state(self):
        self.setWindowState(
            self.windowState()
            & ~Qt.WindowState.WindowMinimized
            & ~Qt.WindowState.WindowMaximized
            & ~Qt.WindowState.WindowFullScreen
        )

    def changeEvent(self, event):
        if (
            event.type() == QEvent.Type.WindowStateChange
            and self.windowState() & Qt.WindowState.WindowMinimized
            and not self._force_close
            and not self._docking_from_minimize
        ):
            self._docking_from_minimize = True
            self.normalize_window_state()
            QTimer.singleShot(0, self._dock_after_minimize)
        super().changeEvent(event)

    def _dock_after_minimize(self):
        self._docking_from_minimize = False
        if self._force_close:
            return
        self.dockRequested.emit()

    def closeEvent(self, event):
        if self._force_close:
            event.accept()
            return
        self.normalize_window_state()
        event.accept()
