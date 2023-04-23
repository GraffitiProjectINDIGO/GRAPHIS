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
import os
from pathlib import Path
from sqlite3 import dbapi2


def uri4sqlite(fn: str) -> str:
    uri = Path(fn).resolve().as_uri()
    if len(uri) > 7 and uri[7] != '/':
        # a network path. Insert 2 more slashes after the scheme.
        uri = '{}//{}'.format(uri[:7], uri[7:])
    return uri


def init(db):
    db.row_factory = dbapi2.Row
    db.execute("PRAGMA foreign_keys = ON")
    supports_foreign_keys = db.execute("PRAGMA foreign_keys").fetchone()[0]
    assert supports_foreign_keys

    n_cpus = os.cpu_count()
    if n_cpus:
        db.execute("PRAGMA threads = {}".format(n_cpus))


def create(db_fn: str):
    with dbapi2.connect(db_fn) as db:
        init(db)
        db.executescript('''
            CREATE TABLE images ( 
                id INTEGER NOT NULL PRIMARY KEY, 
                name TEXT,
                width  INTEGER,
                height INTEGER,
                user TEXT,
                deleted_orig_tag INTEGER DEFAULT 0,
                path   TEXT NOT NULL UNIQUE,
                orig_img_region_leftover TEXT,
                preview blob 
            ); 


            CREATE TABLE objects (
                id INTEGER NOT NULL PRIMARY KEY,
                image REFERENCES images(id),
                user TEXT,
                object_type TEXT,
                orig_img_region TEXT,
                changed INTEGER DEFAULT 0,
                data TEXT
            ); 
                     
            ''')

        db.executescript('''
            CREATE INDEX idx_image_objects ON objects(image);
        ''')


if __name__ == '__main__':
    dbFn = 'test_debug.sqlite'
    create(dbFn)
