# Copyright (C) 2023 Martin Wieser
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

from pathlib import Path
from PIL import ImageQt
from PIL import Image
import rawpy
from multiprocessing import Process, Queue
from PySide6 import QtGui
from PySide6.QtGui import QImageReader
from PySide6.QtCore import SignalInstance

Image.MAX_IMAGE_PIXELS = 9999999999999999999

image_formats_direct_load = []
for x in QImageReader.supportedImageFormats():
    image_formats_direct_load.append('.' + x.data().decode())


def image_loader(filename: Path) -> QtGui.QPixmap:
    img = None
    if Path(filename).suffix.lower() in image_formats_direct_load:
        img = QtGui.QPixmap(filename)
        if img.height() > 0:
            return img

    try:
        q = Queue()
        proc = Process(target=loader_raw, args=(filename, q))
        proc.start()
        img = q.get()
        proc.join()

        buf, w, h, bytes_per_line = img
        img = QtGui.QPixmap.fromImage(QtGui.QImage(buf, w, h, bytes_per_line, QtGui.QImage.Format_RGB888))
    except:
        img_pil = Image.open(filename)
        img_pil = img_pil.convert("RGBA")
        img = QtGui.QPixmap.fromImage(ImageQt.ImageQt(img_pil))

    return img


def loader_raw(path, queu: Queue):
    try:
        with rawpy.imread(path) as raw:
            src = raw.postprocess()
            h, w, ch = src.shape
            bytes_per_line = ch * w
            buf = src.data.tobytes()  # or bytes(src.data)
            queu.put([buf, w, h, bytes_per_line])
    except:
        queu.put([])
