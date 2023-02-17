from PySide2 import QtWidgets
from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QColor


def stylesheet_parser_color_class(color):

	text = 'QPushButton {border: 2px solid '
	text += color.name() + '; border-radius: 5px;background-color: '
	text += color.name(QColor.HexArgb) + ';}\n'
	text += "QPushButton:hover {background-color: rgab(0, 255, 0,50);border: 2px solid rgb(35, 230, 32);}"

	return text


class COLORButton(QtWidgets.QPushButton):
	"""
	Custom Qt Widget to show a chosen color.

	Left-clicking the button shows the color-chooser, while
	right-clicking resets the color to None (no-color).
	"""

	colorChanged = Signal(QColor)

	def __init__(self, *args, color=None, **kwargs):
		super(COLORButton, self).__init__(*args, **kwargs)

		self._color = None
		self.dialogue_color = None
		self._default = color
		self.pressed.connect(self.on_color_picker)

	def set_color(self, color):
		if color != self._color:
			self._color = color

		if self._color:
			self.setStyleSheet(stylesheet_parser_color_class(self._color))
		else:
			self.setStyleSheet("")

	def color(self):
		return self._color

	def on_color_picker(self):
		"""
			Show color-picker dialog to select color.
			Qt will use the native dialog by default.
		"""
		dlg = QtWidgets.QColorDialog()
		dlg.setOption(QtWidgets.QColorDialog.ShowAlphaChannel, True)
		if not self.dialogue_color:
			self.dialogue_color = dlg.currentColor()
		else:
			dlg.setCurrentColor(self.dialogue_color)
		# dlg.setStyleSheet("QColorDialog {background-color: rgb((52, 59, 72));}")
		# dlg.exec_()
		color = dlg.getColor(options=QtWidgets.QColorDialog.ShowAlphaChannel)
		if color.isValid():
			if color.alpha() == 255:
				color.setAlpha(150)
			self.set_color(color)
			self.colorChanged.emit(color)

	def mousePressEvent(self, e):
		if e.button() == Qt.RightButton:
			self.set_color(self._default)

		return super(COLORButton, self).mousePressEvent(e)
