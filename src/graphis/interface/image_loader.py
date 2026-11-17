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

import os
from multiprocessing import get_context
from multiprocessing.connection import wait
from pathlib import Path

from PIL import Image, ImageQt
from PySide6 import QtGui
from PySide6.QtGui import QImageReader

from graphis.interface.raw_loader_process import loader_raw

Image.MAX_IMAGE_PIXELS = 9999999999999999999
PROCESS_CONTEXT = get_context("spawn")

image_formats_direct_load = []
for x in QImageReader.supportedImageFormats():
    image_formats_direct_load.append("." + x.data().decode().lower())


def image_loader(filename: str) -> QtGui.QImage:
    if Path(filename).suffix.lower() in image_formats_direct_load:
        reader = QImageReader(os.fspath(filename))
        reader.setAutoTransform(False)
        img = reader.read()

        if not img.isNull() and img.height() > 0:
            return img

    try:
        buf, w, h, bytes_per_line = load_raw_in_process(filename)
        img = QtGui.QImage(buf, w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888).copy()
    except Exception:
        with Image.open(filename) as img_pil:
            img_pil.load()
            img_pil = img_pil.convert("RGBA")
            img = ImageQt.ImageQt(img_pil).copy()

    return img


def load_raw_in_process(filename: str):
    receive_conn, send_conn = PROCESS_CONTEXT.Pipe(duplex=False)
    proc = PROCESS_CONTEXT.Process(target=loader_raw, args=(filename, send_conn))
    proc.start()
    send_conn.close()

    try:
        ready = wait([receive_conn, proc.sentinel])
        if receive_conn in ready:
            try:
                img_data = receive_conn.recv()
            except EOFError as err:
                proc.join()
                raise RuntimeError("RAW loader closed before returning image data.") from err
            proc.join()
            if not img_data:
                raise ValueError("RAW loader did not return image data.")
            return img_data

        proc.join()
        raise RuntimeError(f"RAW loader exited before returning image data. Exit code: {proc.exitcode}")
    finally:
        receive_conn.close()
