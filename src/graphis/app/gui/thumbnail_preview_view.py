# Copyright (C) 2026 Martin Wieser

from PySide6.QtCore import QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QListView,
    QMenu,
    QStackedWidget,
    QStyledItemDelegate,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from graphis.app.gui.preview_class import PREVIEW_DATA_ROLE
from graphis.app.gui.resources import icon as resource_icon


def show_thumbnail_context_menu(parent, global_pos, index, action_signal):
    if not index.isValid():
        return

    image_path = index.data(Qt.ItemDataRole.UserRole)
    image_id = index.data(Qt.ItemDataRole.UserRole + 1)
    if image_path is None or image_id is None:
        return

    menu = QMenu(parent)
    menu.setMinimumWidth(160)
    menu.setStyleSheet("""
        QMenu {
            min-width: 160px;
            background-color: rgb(0, 0, 0);
        }
        QMenu::item {
            padding: 3px 24px 3px 10px;
        }
        QMenu::item:selected {
            background-color: rgb(65, 74, 90);
            color: rgb(255, 255, 255);
        }
        QMenu::separator {
            height: 1px;
            margin: 6px 12px;
            background: rgb(120, 120, 120);
        }
    """)
    open_image_action = menu.addAction("Open image")
    copy_path_action = menu.addAction("Copy image path")
    open_location_action = menu.addAction("Open location in Explorer")
    menu.addSeparator()
    restore_original_action = menu.addAction("Restore orig. image region")
    convert_relative_action = menu.addAction("Coordinates to relative")
    convert_pixel_action = menu.addAction("Coordinates to absolute (pixel)")
    menu.addSeparator()
    delete_image_action = menu.addAction("Delete image from database")

    action_map = {
        open_image_action: "open_image",
        copy_path_action: "copy_image_path",
        open_location_action: "open_image_location",
        restore_original_action: "restore_original_image_region",
        convert_relative_action: "convert_coordinates_relative",
        convert_pixel_action: "convert_coordinates_pixel",
        delete_image_action: "delete_image",
    }

    selected_action = menu.exec(global_pos)
    if selected_action in action_map:
        action_signal.emit(action_map[selected_action], index)


class ThumbnailPreviewView(QListView):
    thumbnailDecreaseRequested = Signal()
    thumbnailIncreaseRequested = Signal()
    thumbnailActionRequested = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setViewMode(QListView.ViewMode.IconMode)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setSpacing(10)
        self.setUniformItemSizes(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.thumbnail_controls = QWidget(self)
        self.thumbnail_controls.setObjectName("thumbnailSizeControls")
        self.thumbnail_controls.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self.thumbnail_controls)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        self.thumbnail_decrease_button = self._create_control_button(
            "thumbnail-size-decrease.svg",
            "Decrease thumbnail size",
        )
        self.thumbnail_increase_button = self._create_control_button(
            "thumbnail-size-increase.svg",
            "Increase thumbnail size",
        )
        layout.addWidget(self.thumbnail_decrease_button)
        layout.addWidget(self.thumbnail_increase_button)

        self.thumbnail_decrease_button.clicked.connect(lambda _checked=False: self.thumbnailDecreaseRequested.emit())
        self.thumbnail_increase_button.clicked.connect(lambda _checked=False: self.thumbnailIncreaseRequested.emit())

        self.thumbnail_controls.setStyleSheet("""
            QWidget#thumbnailSizeControls {
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
        self.thumbnail_controls.adjustSize()
        self.thumbnail_controls.show()
        self.thumbnail_controls.raise_()

    def _create_control_button(self, icon_name, tooltip):
        button = QToolButton(self.thumbnail_controls)
        button.setIcon(resource_icon(icon_name))
        button.setIconSize(QSize(22, 22))
        button.setFixedSize(30, 30)
        button.setToolTip(tooltip)
        button.setAutoRaise(False)
        return button

    def contextMenuEvent(self, event):
        index = self.indexAt(event.pos())
        show_thumbnail_context_menu(self, event.globalPos(), index, self.thumbnailActionRequested)

    def set_thumbnail_size_controls_enabled(self, can_decrease, can_increase):
        self.thumbnail_decrease_button.setEnabled(can_decrease)
        self.thumbnail_increase_button.setEnabled(can_increase)

    def set_thumbnail_item_size(self, size):
        spacing = self.spacing()
        self.setGridSize(QSize(size.width() + spacing, size.height() + spacing))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_thumbnail_controls()

    def showEvent(self, event):
        super().showEvent(event)
        self._position_thumbnail_controls()
        self.thumbnail_controls.show()
        self.thumbnail_controls.raise_()

    def _position_thumbnail_controls(self):
        self.thumbnail_controls.adjustSize()
        margin = 4
        top_left = self.viewport().geometry().topLeft()
        self.thumbnail_controls.move(top_left.x() + margin, top_left.y() + margin)
        self.thumbnail_controls.raise_()


class ThumbnailTableView(QTableView):
    thumbnailActionRequested = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setSortingEnabled(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setItemDelegate(PreviewTableDelegate(self))
        self.verticalHeader().hide()
        self._configure_column_header()
        self.setStyleSheet("""
            QTableView {
                background-color: rgb(80, 80, 80);
                alternate-background-color: rgb(70, 70, 70);
                color: rgb(230, 230, 230);
            }
            QHeaderView::section {
                background-color: rgb(55, 61, 75);
                color: rgb(230, 230, 230);
                border: none;
                border-right: 1px solid rgb(80, 80, 80);
                padding: 4px 6px;
            }
            QTableView::item:selected {
                background-color: rgb(95, 102, 115);
                color: rgb(255, 255, 255);
                outline: 0;
            }
        """)
        self.setMouseTracking(True)
        self.entered.connect(self._select_hovered_row)

    def _select_hovered_row(self, index):
        if index.isValid():
            self.selectRow(index.row())

    def leaveEvent(self, event):
        self.clearSelection()
        super().leaveEvent(event)

    def setModel(self, model):
        super().setModel(model)
        if model is not None:
            self._fit_columns_to_viewport()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_columns_to_viewport()

    def _configure_column_header(self):
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(24)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)

    def _fit_columns_to_viewport(self):
        model = self.model()
        if model is None:
            return

        self.resizeColumnToContents(2)
        self.resizeColumnToContents(3)
        self.resizeColumnToContents(4)
        self.resizeColumnToContents(5)

        fixed_width = sum(self.columnWidth(column) for column in (2, 3, 4, 5))
        remaining_width = max(0, self.viewport().width() - fixed_width - 2)
        title_min_width = self._header_width(0)
        path_min_width = self._header_width(1)
        min_variable_width = title_min_width + path_min_width

        if remaining_width <= min_variable_width:
            title_width = title_min_width
            path_width = max(path_min_width, remaining_width - title_width)
        else:
            title_width = max(title_min_width, int(remaining_width * 0.35))
            path_width = remaining_width - title_width

        self.setColumnWidth(0, title_width)
        self.setColumnWidth(1, path_width)

    def _header_width(self, column):
        model = self.model()
        if model is None:
            return 60

        text = model.headerData(column, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole)
        return self.fontMetrics().horizontalAdvance(str(text)) + 28

    def contextMenuEvent(self, event):
        index = self.indexAt(event.pos())
        show_thumbnail_context_menu(self, event.globalPos(), index, self.thumbnailActionRequested)


class PreviewTableDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        if index.column() not in {2, 3}:
            super().paint(painter, option, index)
            return

        preview = index.data(PREVIEW_DATA_ROLE)
        if preview is None:
            super().paint(painter, option, index)
            return

        should_draw = preview.error_image if index.column() == 2 else preview.warning_image
        color = QColor("#ed0909") if index.column() == 2 else QColor("#f0b905")

        super().paint(painter, option, index)
        if not should_draw:
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        radius = min(5.0, max(3.0, option.rect.height() / 5.0))
        center = option.rect.center()
        painter.drawEllipse(QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2))
        painter.restore()


class ThumbnailPreviewPanel(QWidget):
    thumbnailDecreaseRequested = Signal()
    thumbnailIncreaseRequested = Signal()
    thumbnailActionRequested = Signal(str, object)
    doubleClicked = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.thumbnail_view = ThumbnailPreviewView(self)
        self.table_view = ThumbnailTableView(self)
        self.stack = QStackedWidget(self)
        self.stack.addWidget(self.thumbnail_view)
        self.stack.addWidget(self.table_view)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.stack)

        self.thumbnail_view.thumbnailDecreaseRequested.connect(lambda: self.thumbnailDecreaseRequested.emit())
        self.thumbnail_view.thumbnailIncreaseRequested.connect(lambda: self.thumbnailIncreaseRequested.emit())
        self.thumbnail_view.thumbnailActionRequested.connect(
            lambda action, index: self.thumbnailActionRequested.emit(action, index)
        )
        self.table_view.thumbnailActionRequested.connect(
            lambda action, index: self.thumbnailActionRequested.emit(action, index)
        )
        self.thumbnail_view.doubleClicked.connect(lambda index: self.doubleClicked.emit(index))
        self.table_view.doubleClicked.connect(lambda index: self.doubleClicked.emit(index))

    def set_table_mode(self, table_mode):
        self.stack.setCurrentWidget(self.table_view if table_mode else self.thumbnail_view)

    def table_mode(self):
        return self.stack.currentWidget() == self.table_view

    def setModel(self, model):
        self.thumbnail_view.setModel(model)
        self.table_view.setModel(model)

    def setItemDelegate(self, delegate):
        self.thumbnail_view.setItemDelegate(delegate)

    def set_thumbnail_size_controls_enabled(self, can_decrease, can_increase):
        self.thumbnail_view.set_thumbnail_size_controls_enabled(can_decrease, can_increase)

    def set_thumbnail_item_size(self, size):
        self.thumbnail_view.set_thumbnail_item_size(size)

    def doItemsLayout(self):
        self.thumbnail_view.doItemsLayout()
        self.table_view.doItemsLayout()

    def viewport(self):
        return self.stack.currentWidget().viewport()
