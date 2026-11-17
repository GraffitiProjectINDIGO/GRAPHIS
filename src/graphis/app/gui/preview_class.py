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

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QRectF, QSize, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QStyledItemDelegate

from graphis.app.var_classes import TEXT_HEIGHT, TEXT_WIDTH, PreviewModelData

PREVIEW_DATA_ROLE = Qt.UserRole + 100


# Create a custom namedtuple class to hold our data.
class PreviewDelegate(QStyledItemDelegate):
    """
    Render thumbnail cells
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.thumbnail_size = QSize(300, 200)
        self.rectangle_color = QColor("#000000")
        self.polygon_color = QColor("#000000")
        self.circle_color = QColor("#000000")
        self.point_color = QColor("#000000")
        self.linestring_color = QColor("#000000")
        self.width = 0
        self.height = 0
        self._led_cache = {}

    def _overlay_scale(self):
        if self.width <= 0 or self.height <= 0:
            return 1.0
        width_scale = self.width / 300
        height_scale = self.height / 200
        return max(0.5, min(1.0, width_scale, height_scale))

    def _overlay_font(self, scale):
        font = QFont(self.emblemFont)
        font.setPointSizeF(max(6.0, self._base_emblem_point_size * scale))
        return font

    def get_cached_led(self, size, color_hex, bright_hex, dark_hex):
        """Generates the LED graphic once for a specific size and color, then stores it in the cache."""
        # Use both size and color as a composite key for the cache dictionary
        size_key = int(size)
        cache_key = (size_key, color_hex)

        if cache_key in self._led_cache:
            return self._led_cache[cache_key]

        # Calculate a larger boundary box to allocate enough space for the glow effect
        glow_size = int(size * 1.6)

        # Create a pixmap supporting an alpha channel for clean background transparency
        pixmap = QPixmap(glow_size, glow_size)
        pixmap.fill(Qt.GlobalColor.transparent)

        # Initialize the internal painter to draw directly onto the offscreen pixmap
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)

        # Define coordinates relative to the new pixmap canvas
        center = glow_size / 2.0

        # Convert base color hex to QColor for the ambient glow
        base_color = QColor(color_hex)

        # 1. Render the soft ambient glow background using the specific base color
        glow_grad = QRadialGradient(center, center, glow_size / 2.0)
        glow_grad.setColorAt(
            0.0, QColor(base_color.red(), base_color.green(), base_color.blue(), 100)
        )  # Semi-transparent
        glow_grad.setColorAt(1.0, QColor(base_color.red(), base_color.green(), base_color.blue(), 0))  # Fully transparent
        p.setBrush(QBrush(glow_grad))
        p.drawEllipse(QRectF(0, 0, glow_size, glow_size))

        # 2. Render the 3D LED body on top
        led_x = (glow_size - size) / 2.0
        led_y = (glow_size - size) / 2.0

        # Offset the gradient center (35% top-left) to simulate a realistic light reflection
        led_grad = QRadialGradient(led_x + (size * 0.35), led_y + (size * 0.35), size * 0.7)
        led_grad.setColorAt(0.0, QColor(bright_hex))  # Bright hot-spot center
        led_grad.setColorAt(0.6, base_color)  # Current base color
        led_grad.setColorAt(1.0, QColor(dark_hex))  # Dark vignette outer rim
        p.setBrush(QBrush(led_grad))
        p.drawEllipse(QRectF(led_x, led_y, size, size))

        p.end()

        # Save the finalized graphic to cache and return it
        self._led_cache[cache_key] = pixmap
        return pixmap

    def paint(self, painter, option, index):
        # data is our preview object
        data = index.model().data(index, PREVIEW_DATA_ROLE)
        if data is None:
            return

        extension = data.title.split(".")[-1]
        polygon_number = data.polygon_number
        circle_number = data.circle_number
        linestring_number = data.linestring_number
        point_number = data.point_number
        rectangle_number = data.rectangle_number
        warning = data.warning_image
        error = data.error_image
        rot = data.visual_rotation_degrees

        self.width = option.rect.width()
        self.height = option.rect.height()

        overlay_scale = self._overlay_scale()
        width_image_box = self.width - 1 - TEXT_WIDTH * overlay_scale - 1
        height_image_box = self.height
        # Draw rectangle in which the image will be placed
        box_rect = QRectF(option.rect.x(), option.rect.y(), self.width, self.height)

        painter.setRenderHint(QPainter.Antialiasing, True)
        if data.missing_file:
            frame_color = QColor("#a63535")
        elif data.is_active:
            frame_color = QColor("#53b56b")
        else:
            frame_color = QColor("#111111")

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(frame_color, 2))
        painter.drawRect(box_rect)
        painter.setRenderHint(QPainter.Antialiasing, False)

        image_rect = QRectF(
            option.rect.x() + 2,
            option.rect.y() + 2,
            width_image_box - 4,
            height_image_box - 4,
        )
        self._draw_preview_image(painter, data.image, image_rect, data.visual_rotation_degrees)

        x = option.rect.x() + width_image_box + 1
        y = option.rect.y()

        # Visual indicator warning, error, rotation, changed image region
        dot_size_scaled = 15 * overlay_scale
        painter.setPen(Qt.NoPen)

        y_new = y + 5
        if error:
            painter.setBrush(QColor("#ed0909"))
            painter.drawEllipse(
                QRectF(
                    x + dot_size_scaled / 2.0,
                    y + 5,
                    dot_size_scaled,
                    dot_size_scaled,
                )
            )
        y_new = y_new + 4 + dot_size_scaled
        if warning:
            painter.setBrush(QColor("#f0b905"))
            painter.drawEllipse(
                QRectF(
                    x + dot_size_scaled / 2.0,
                    y_new,
                    dot_size_scaled,
                    dot_size_scaled,
                )
            )

        # Draw other content left to the image
        font = QFont()
        font.setBold(True)
        font.setPointSizeF(max(6.0, 8.0 * overlay_scale))

        if data.exif_orientation_present:
            if data.exif_rotation_degrees != data.visual_rotation_degrees:
                painter.setPen(QColor(Qt.GlobalColor.red))
            else:
                painter.setPen(QColor(Qt.GlobalColor.green))
        else:
            painter.setPen(QColor(Qt.GlobalColor.white))

        y_new = y_new + dot_size_scaled + 4
        painter.setFont(font)
        sec_rect = QRectF(
            x,
            y_new,
            TEXT_WIDTH * self._overlay_scale(),
            TEXT_HEIGHT * self._overlay_scale(),
        )
        painter.drawText(sec_rect, Qt.AlignCenter, f"{rot}°")

        y_new = y_new + TEXT_HEIGHT * self._overlay_scale()
        #y = option.rect.y() + int(self.height / 2.0 - TEXT_HEIGHT * overlay_scale)

        if point_number:
            self.print_label_number(painter, x, y_new, font, point_number, self.point_color)
        y_new += 2 + TEXT_HEIGHT * self._overlay_scale()

        if circle_number:
            self.print_label_number(painter, x, y_new, font, circle_number, self.circle_color)
        y_new += 2 + TEXT_HEIGHT * self._overlay_scale()

        if linestring_number:
            self.print_label_number(painter, x, y_new, font, linestring_number, self.linestring_color)
        y_new += 2 + TEXT_HEIGHT * self._overlay_scale()

        if rectangle_number:
            self.print_label_number(painter, x, y_new, font, rectangle_number, self.rectangle_color)

        y_new += 2 + TEXT_HEIGHT * self._overlay_scale()
        if polygon_number:
            self.print_label_number(painter, x, y_new, font, polygon_number, self.polygon_color)

        y_new = option.rect.y() + self.height - TEXT_HEIGHT * self._overlay_scale()
        extension = extension.upper()
        self.print_label_number(painter, x, y_new, font, extension, QColor("#5f6bfe"))

        ## --- Replace your original code snippet with this block ---
        ## 1. Setup base configurations and pen styles
        # painter.setPen(QPen(QColor("#00d9ed"), 1))
        # led_size = 20.0 * overlay_scale
        # glow_offset = (led_size * 1.6 - led_size) / 2.0

        ## 2. Draw the black background backing if either warning or error is active
        # if warning or error:
        #    # Slightly expanded the bounding box height and width to prevent the soft LED glow from clipping
        #    bg_x = option.rect.x() + self.width - 4 - 2 - led_size - glow_offset
        #    bg_y = option.rect.y() + 2 - glow_offset
        #    bg_w = 4 + led_size + (glow_offset * 2)
        #    bg_h = 4 + 2 + (2 * led_size) + (glow_offset * 2)
        #    painter.fillRect(QRectF(bg_x, bg_y, bg_w, bg_h), QColor("#000000"))

        ## Reset pen style as the LEDs don't use hard borders
        # painter.setPen(Qt.PenStyle.NoPen)

        ## 3. Render the Error LED (Red)
        # if error:
        #    # Fetch pre-rendered red LED from cache
        #    red_led = self.get_cached_led(led_size, "#ed0909", "#ff6b6b", "#700000")

        #    # Calculate original positioning adjusted by the glow offset
        #    x_pos = option.rect.x() + self.width - 2 - 1 - led_size - glow_offset
        #    y_pos = option.rect.y() + 2 + 2 - glow_offset

        #    # Blit the pixmap onto the widget surface
        #    painter.drawPixmap(int(x_pos), int(y_pos), red_led)

        ## 4. Render the Warning LED (Yellow)
        # if warning:
        #    # Fetch pre-rendered yellow LED from cache
        #    yellow_led = self.get_cached_led(led_size, "#f0b905", "#ffeb85", "#7a5c00")

        #    # Calculate original stacked positioning adjusted by the glow offset
        #    x_pos = option.rect.x() + self.width - 2 - 1 - led_size - glow_offset
        #    y_pos = option.rect.y() + 2 + 2 + 2 + led_size - glow_offset

        #    # Blit the pixmap onto the widget surface
        #    painter.drawPixmap(int(x_pos), int(y_pos), yellow_led)

    def sizeHint(self, option, index):
        # All items the same size.
        return QSize(self.thumbnail_size.width(), self.thumbnail_size.height())

    def set_thumbnail_size(self, size):
        self.thumbnail_size = QSize(size.width(), size.height())

    def _draw_preview_image(self, painter, pixmap, target_rect, rotation_degrees):
        if pixmap.isNull() or target_rect.width() <= 0 or target_rect.height() <= 0:
            return

        rotation = int(rotation_degrees) % 360
        source_width = pixmap.width()
        source_height = pixmap.height()
        if rotation in {90, 270}:
            fitted_width = source_height
            fitted_height = source_width
        else:
            fitted_width = source_width
            fitted_height = source_height

        scale = min(target_rect.width() / fitted_width, target_rect.height() / fitted_height)
        draw_width = source_width * scale
        draw_height = source_height * scale

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.translate(target_rect.center())
        if rotation:
            painter.rotate(rotation)
        painter.drawPixmap(
            QRectF(-draw_width / 2.0, -draw_height / 2.0, draw_width, draw_height),
            pixmap,
            QRectF(0, 0, source_width, source_height),
        )
        painter.restore()

    def print_label_number(self, painter, pos_x, pos_y, font, text: str | int | float, colour):
        painter.save()
        painter.setFont(font)
        painter.setPen(QColor(Qt.white))
        colour = colour
        sec_rect = QRectF(pos_x, pos_y, TEXT_WIDTH * self._overlay_scale(), TEXT_HEIGHT * self._overlay_scale())
        painter_path = QPainterPath()
        painter_path.addRoundedRect(sec_rect, 5 * self._overlay_scale(), 5 * self._overlay_scale())
        painter.fillPath(painter_path, colour)
        painter.drawText(sec_rect, Qt.AlignCenter, str(text))
        painter.restore()


class PreviewModel(QAbstractTableModel):
    headers = ("Image", "Path", "Error", "Warning", "Geometries", "Rot.")

    def __init__(self):
        super().__init__()
        # .data holds our data for display, as a list of Preview objects.
        self.previews = []

    def appendData(self, data=PreviewModelData):
        row = len(self.previews)
        self.beginInsertRows(QModelIndex(), row, row)
        self.previews.append(data)
        self.endInsertRows()

    def data(self, index, role):
        if not index.isValid():
            return
        try:
            data = self.previews[index.row()]
        except IndexError:
            return

        if role == PREVIEW_DATA_ROLE:
            return data

        if role == Qt.DisplayRole:
            return self._display_value(data, index.column())

        if role == Qt.ToolTipRole:
            return self._tooltip_value(data, index.column())

        if role == Qt.UserRole:
            return data.path

        if role == Qt.UserRole + 1:
            return data.id

        if role == Qt.BackgroundRole:
            if data.missing_file:
                return QBrush(QColor("#5b4242"))
            if data.is_active:
                return QBrush(QColor("#425b48"))

        if role == Qt.ForegroundRole:
            if index.column() == 2 and data.error_image:
                return QBrush(QColor("#ed0909"))
            if index.column() == 3 and data.warning_image:
                return QBrush(QColor("#f0b905"))

        if role == Qt.TextAlignmentRole and index.column() in {2, 3, 4, 5}:
            return Qt.AlignCenter

    def _display_value(self, data, column):
        if column == 0:
            return data.title
        if column == 1:
            return data.path
        if column == 2:
            return ""
        if column == 3:
            return ""
        if column == 4:
            return data.polygon_number + data.rectangle_number + data.circle_number + data.point_number + data.linestring_number
        if column == 5:
            return f"{data.visual_rotation_degrees} deg"
        return ""

    def _tooltip_value(self, data, column):
        if column == 4:
            return (f"Rectangles: {data.rectangle_number}\n"
                    f"Polygons: {data.polygon_number}\n"
                    f"Points: {data.point_number}\n",
                    f"Lines: {data.linestring_number}\n"
                    f"Circles: {data.circle_number}")
        if column == 5:
            if not data.exif_orientation_present:
                return (
                    "Visual image-viewer rotation only. Coordinates stay referenced to the original image.\n"
                    "EXIF Orientation: not present"
                )
            return (
                "Visual image-viewer rotation only. Coordinates stay referenced to the original image.\n"
                f"EXIF rotation: {data.exif_rotation_degrees} deg"
            )
        return data.title

    def _index_for_flat_index(self, flat_index):
        return self.index(flat_index, 0)

    def _emit_flat_index_changed(self, flat_index):
        left = self.index(flat_index, 0)
        right = self.index(flat_index, self.columnCount() - 1)
        self.dataChanged.emit(left, right)

    def _flat_index_for_image_id(self, image_id):
        for idx, preview in enumerate(self.previews):
            if preview.id == image_id:
                return idx
        return None

    def set_missing_image(self, image_id, missing=True):
        flat_index = self._flat_index_for_image_id(image_id)
        if flat_index is None:
            return False

        if self.previews[flat_index].missing_file == missing:
            return True

        self.previews[flat_index].missing_file = missing
        self._emit_flat_index_changed(flat_index)
        return True

    def set_error_image(self, image_id, error=True):
        flat_index = self._flat_index_for_image_id(image_id)
        if flat_index is None:
            return False

        if self.previews[flat_index].error_image == error:
            return True

        self.previews[flat_index].error_image = error
        self._emit_flat_index_changed(flat_index)
        return True

    def clear_error_image(self, image_id=None):
        changed_indexes = []
        for flat_index, preview in enumerate(self.previews):
            if image_id is not None and preview.id != image_id:
                continue
            if preview.error_image:
                preview.error_image = False
                changed_indexes.append(flat_index)

        for flat_index in changed_indexes:
            self._emit_flat_index_changed(flat_index)
        return bool(changed_indexes)

    def set_warning_image(self, image_id, warning=True):
        flat_index = self._flat_index_for_image_id(image_id)
        if flat_index is None:
            return False

        if self.previews[flat_index].warning_image == warning:
            return True

        self.previews[flat_index].warning_image = warning
        self._emit_flat_index_changed(flat_index)
        return True

    def clear_warning_image(self, image_id=None):
        changed_indexes = []
        for flat_index, preview in enumerate(self.previews):
            if image_id is not None and preview.id != image_id:
                continue
            if preview.warning_image:
                preview.warning_image = False
                changed_indexes.append(flat_index)

        for flat_index in changed_indexes:
            self._emit_flat_index_changed(flat_index)
        return bool(changed_indexes)

    def set_active_image(self, image_id):
        if self._flat_index_for_image_id(image_id) is None:
            return False

        changed_indexes = []
        for flat_index, preview in enumerate(self.previews):
            is_active = preview.id == image_id
            if preview.is_active != is_active:
                preview.is_active = is_active
                changed_indexes.append(flat_index)

        for flat_index in changed_indexes:
            self._emit_flat_index_changed(flat_index)
        return True

    def set_visual_rotation(self, image_id, degrees):
        flat_index = self._flat_index_for_image_id(image_id)
        if flat_index is None:
            return False

        degrees = int(degrees) % 360
        if self.previews[flat_index].visual_rotation_degrees == degrees:
            return True

        self.previews[flat_index].visual_rotation_degrees = degrees
        self._emit_flat_index_changed(flat_index)
        return True

    def visual_rotation(self, image_id):
        flat_index = self._flat_index_for_image_id(image_id)
        if flat_index is None:
            return 0
        return int(self.previews[flat_index].visual_rotation_degrees) % 360

    def exif_rotation(self, image_id):
        flat_index = self._flat_index_for_image_id(image_id)
        if flat_index is None:
            return 0
        return int(self.previews[flat_index].exif_rotation_degrees) % 360

    def exif_orientation_present(self, image_id):
        flat_index = self._flat_index_for_image_id(image_id)
        if flat_index is None:
            return False
        return bool(self.previews[flat_index].exif_orientation_present)

    def image_metadata(self, image_id):
        flat_index = self._flat_index_for_image_id(image_id)
        if flat_index is None:
            return {}
        return dict(self.previews[flat_index].image_metadata)

    def clear_active_image(self):
        changed_indexes = []
        for flat_index, preview in enumerate(self.previews):
            if preview.is_active:
                preview.is_active = False
                changed_indexes.append(flat_index)

        for flat_index in changed_indexes:
            self._emit_flat_index_changed(flat_index)

    def add_number(self, image_id, object_type):
        flat_index = self._flat_index_for_image_id(image_id)
        if flat_index is None or object_type not in {"rectangle", "polygon", "circle", "point", "linestring"}:
            return False

        if object_type == "rectangle":
            self.previews[flat_index].rectangle_number = self.previews[flat_index].rectangle_number + 1
        elif object_type == "polygon":
            self.previews[flat_index].polygon_number = self.previews[flat_index].polygon_number + 1
        elif object_type == "circle":
            self.previews[flat_index].circle_number = self.previews[flat_index].circle_number + 1
        elif object_type == "point":
            self.previews[flat_index].point_number = self.previews[flat_index].point_number + 1
        elif object_type == "linestring":
            self.previews[flat_index].linestring_number = self.previews[flat_index].linestring_number + 1
        self._emit_flat_index_changed(flat_index)
        return True

    def remove_number(self, image_id, object_type):
        flat_index = self._flat_index_for_image_id(image_id)
        if flat_index is None or object_type not in {"rectangle", "polygon", "circle", "point", "linestring"}:
            return False

        if object_type == "rectangle":
            self.previews[flat_index].rectangle_number = max(0, self.previews[flat_index].rectangle_number - 1)
        elif object_type == "polygon":
            self.previews[flat_index].polygon_number = max(0, self.previews[flat_index].polygon_number - 1)
        elif object_type == "circle":
            self.previews[flat_index].circle_number = max(0, self.previews[flat_index].circle_number - 1)
        elif object_type == "point":
            self.previews[flat_index].point_number = max(0, self.previews[flat_index].point_number - 1)
        elif object_type == "linestring":
            self.previews[flat_index].linestring_number = max(0, self.previews[flat_index].linestring_number - 1)
        self._emit_flat_index_changed(flat_index)
        return True

    def rowCount(self, parent=None):
        if parent is None:
            parent = QModelIndex()
        if parent.isValid():
            return 0
        return len(self.previews)

    def columnCount(self, parent=None):
        if parent is None:
            parent = QModelIndex()
        if parent.isValid():
            return 0
        return len(self.headers)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        try:
            return self.headers[section]
        except IndexError:
            return None

    def get_index(self, compare_image_id):
        for row, preview in enumerate(self.previews):
            if preview.id == compare_image_id:
                return self.index(row, 0)
        return None

    def get_relative_index(self, compare_image_id, step):
        flat_index = self._flat_index_for_image_id(compare_image_id)
        if flat_index is None:
            return None

        next_index = flat_index + step
        if next_index < 0 or next_index >= len(self.previews):
            return None
        return self.index(next_index, 0)
