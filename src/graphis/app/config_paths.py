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

from pathlib import Path

from PySide6.QtCore import QStandardPaths

APP_NAME = "GRAPHIS"
ORGANIZATION_NAME = "GRAPHIS"


def app_config_dir() -> Path:
    path_text = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericConfigLocation)
    path = (Path(path_text) / APP_NAME) if path_text else Path.home() / ".config" / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def app_config_file(name: str) -> Path:
    return app_config_dir() / name
