from PySide2 import (QtCore, QtGui)
from pathlib import Path
from PIL import ImageQt
from PIL import Image
from PySide2.QtGui import QImageReader

Image.MAX_IMAGE_PIXELS = 9999999999999999999

image_formats_direct_load = []
for x in QImageReader.supportedImageFormats():
	image_formats_direct_load.append('.'+x.data().decode())


def image_loader(filename):

	if Path(filename).suffix.lower() in image_formats_direct_load:
		img = QtGui.QPixmap(filename)

	else:
		img = QtGui.QPixmap.fromImage(loader_raw(filename))

	if img.height() == 0:
		img_pil = Image.open(filename)
		img_pil = img_pil.convert("RGBA")
		img = QtGui.QPixmap.fromImage(ImageQt.ImageQt(img_pil))
		#
		# data = img_pil.tobytes("raw", "RGBA")
		# data = QtGui.QPixmap.fromImage(QtGui.QImage(data, img_pil.size[0], img_pil.size[1], QtGui.QImage.Format_RGBA8888))

	return img


def loader_raw(path):
	# image = QtGui.QImage()
	return []
	with rawpy.imread(path) as raw:
		src = raw.postprocess()
		h, w, ch = src.shape
		bytesPerLine = ch * w
		buf = src.data.tobytes()  # or bytes(src.data)
		image = QtGui.QImage(buf, w, h, bytesPerLine, QtGui.QImage.Format_RGB888)
	return image.copy()

