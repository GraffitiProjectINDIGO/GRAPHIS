#Copyright (C) 2023 Martin Wieser
#
#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from PySide6.QtCore import (QPoint, Qt)
from PySide6.QtGui import (QKeySequence, QPainter, QShortcut)
from PySide6.QtWidgets import (QGraphicsView, QApplication)


class DIGITIZERView(QGraphicsView):
    factor = 2.0

    def __init__(self, parent=None):
        super(DIGITIZERView, self).__init__(parent)
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

    def mousePressEvent(self, event):
        # print(event.pos())
        self._dragPos = event.position()
        if event.button() == Qt.MiddleButton:
            self.middlePressed = True
            QApplication.setOverrideCursor(Qt.ClosedHandCursor)
        if event.button() == Qt.RightButton:
            self.rightPressed = True
        super(DIGITIZERView, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.middlePressed = False
            # QApplication.restoreOverrideCursor()
            # QApplication.restoreOverrideCursor()
            QApplication.restoreOverrideCursor()
        if event.button() == Qt.RightButton:
            self.rightPressed = False
        super(DIGITIZERView, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):

        new_pos = event.position()
        if self.middlePressed:
            diff = new_pos - self._dragPos
            self._dragPos = new_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - diff.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - diff.y())
            event.accept()
        super(DIGITIZERView, self).mouseMoveEvent(event)

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

        if self.transform().m11() < 60 and f > 1:
            self.scale(f, f)
        if self.transform().m11() > 0.01 and f < 1:
            self.scale(f, f)
        # if self.scene() is not None:
            # self.centerOn(self.scene().image_item)

    # EVENT Resize
    def resizeEvent(self, event):
        return super(DIGITIZERView, self).resizeEvent(event)
