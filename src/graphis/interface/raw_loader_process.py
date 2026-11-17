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

import rawpy


def loader_raw(path, send_conn):
    try:
        with rawpy.imread(path) as raw:
            src = raw.postprocess(user_flip=0)
            h, w, ch = src.shape
            bytes_per_line = ch * w
            img_data = [src.data.tobytes(), w, h, bytes_per_line]
    except Exception:
        img_data = []
    try:
        send_conn.send(img_data)
    finally:
        send_conn.close()
