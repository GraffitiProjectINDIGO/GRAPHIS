from PySide2.QtCore import (QPoint, Qt, Slot, Signal)
from PySide2.QtGui import (QKeySequence, QPainter)
from PySide2.QtWidgets import *


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
        self._dragPos = event.pos()
        if event.button() == Qt.MidButton:
            self.middlePressed = True
            QApplication.setOverrideCursor(Qt.ClosedHandCursor)
        if event.button() == Qt.RightButton:
            self.rightPressed = True
        super(DIGITIZERView, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MidButton:
            self.middlePressed = False
            # QApplication.restoreOverrideCursor()
            # QApplication.restoreOverrideCursor()
            QApplication.restoreOverrideCursor()
        if event.button() == Qt.RightButton:
            self.rightPressed = False
        super(DIGITIZERView, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):

        new_pos = event.pos()
        if self.middlePressed:
            diff = new_pos - self._dragPos
            self._dragPos = new_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - diff.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - diff.y())
            event.accept()
        super(DIGITIZERView, self).mouseMoveEvent(event)

    def wheelEvent(self, event):
        num_degrees = event.delta() / 10
        num_steps = num_degrees / 15.0
        # event.scenePos
        # self.centerOn(self.mapToScene(event.pos()))
        old_mouse_img_coo = self.mapToScene(event.pos())
        diff_vec = event.pos() - QPoint(self.width()/2, self.height()/2)
        self.zoom(pow(0.8, num_steps))
        new_middle_map_pos = self.mapFromScene(old_mouse_img_coo)-diff_vec
        self.centerOn(self.mapToScene(new_middle_map_pos))

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
