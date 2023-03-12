
from PySide2 import QtWidgets
from PySide2.QtWidgets import *
from PySide2 import QtCore
from PySide2.QtCore import Qt


class PlainTextEditFocusEvents(QtWidgets.QPlainTextEdit):

    focus_out = QtCore.Signal()

    def __init__(self, parent=None):
        super(PlainTextEditFocusEvents, self).__init__(parent)

    def focusInEvent(self, e):
        # Do something with the event here
        self.setStyleSheet("border: 2px solid rgb(100, 59, 72);background-color: rgb(52, 59, 72);")
        super(PlainTextEditFocusEvents, self).focusInEvent(e)

    def focusOutEvent(self, e):
        # Do something with the event here
        self.focus_out.emit()
        self.setStyleSheet("border: 2px solid rgb(52, 59, 72);background-color: rgb(52, 59, 72);")
        super(PlainTextEditFocusEvents, self).focusInEvent(e)

    def Focus(self):
        self.setFocus()
