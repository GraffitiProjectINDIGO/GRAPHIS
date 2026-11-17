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

import configparser
import logging
from collections import namedtuple
from pathlib import Path

from PySide6.QtGui import QBrush, QColor, QStandardItem

from graphis.interface.imgregion_adapter import (
    CONTRIBUTOR_TAG,
    TAG_DESCRIBER,
    TAG_TRANSCRIBER,
)

license_version = "GNU General Public License v3 or later (GPLv3+)"
build_year = "2026"

COLOR_CIRCLE_START = "#E69F00"
COLOR_RECTANGLE_START = "#009E73"
COLOR_POLYGON_START = "#56B4E9"
COLOR_POINT_START = "#D55E00"
COLOR_LINESTRING_START = "#CC79A7"

REGION_ROLE = "main subject area"

REGION_CREATOR_ROLE = "https://indigo.openatlas.eu/regioncreator"
DESCRIBER_ROLE = "https://indigo.openatlas.eu/describer"
TRANSCRIBER_ROLE = "https://indigo.openatlas.eu/transcriber"

RCTYPE_Standard_IDENTIFIER = "link to indigo graffito definition"
RCTYPE_Standard_NAME = "graffito"


image_region_role = [  # ["cropping", "http://cv.iptc.org/newscodes/imageregionrole/cropping"],
    # ["recommended cropping", "http://cv.iptc.org/newscodes/imageregionrole/recomCropping"],
    # ["landscape format cropping", "http://cv.iptc.org/newscodes/imageregionrole/landscapeCropping"],
    # ["portrait format cropping", "http://cv.iptc.org/newscodes/imageregionrole/portraitCropping"],
    # ["square format cropping", "http://cv.iptc.org/newscodes/imageregionrole/squareCropping"],
    # ["composite image item", "http://cv.iptc.org/newscodes/imageregionrole/compositeImageItem"],
    # ["copyright region", "http://cv.iptc.org/newscodes/imageregionrole/copyrightRegion"],
    # ["business use", "http://cv.iptc.org/newscodes/imageregionrole/businessUse"],
    ["area of interest", "https://vocabs.acdh.oeaw.ac.at/graphis-imgreg/areaOfInterest"],
    ["main subject area", "https://vocabs.acdh.oeaw.ac.at/graphis-imgreg/mainSubjectArea"],
    ["subject area", "https://vocabs.acdh.oeaw.ac.at/graphis-imgreg/subjectArea"],
]


class GeometryConfigs:
    def __init__(self):
        self.region_name_prefix = ""
        self.region_role_name = ""
        self.rctype_identifier = ""
        self.rctype_name = ""
        self.region_creator_role = ""
        self.describer_role = ""
        self.transcriber_role = ""
        self.color_start = ""

    def set_values(self, config_parser: configparser.ConfigParser, geom_type: str) -> bool:

        success = True

        if geom_type == "POLYGON":
            color_start = COLOR_POLYGON_START
        elif geom_type == "RECTANGLE":
            color_start = COLOR_RECTANGLE_START
        elif geom_type == "CIRCLE":
            color_start = COLOR_CIRCLE_START
        elif geom_type == "POINT":
            color_start = COLOR_POINT_START
        elif geom_type == "LINESTRING":
            color_start = COLOR_LINESTRING_START
        else:
            color_start = COLOR_CIRCLE_START
            success = False

        if not config_parser.has_section(geom_type):
            success = False
            config_parser.add_section(geom_type)

        section = config_parser[geom_type]
        self.region_role_name = section.get("REGION_ROLE_NAME", REGION_ROLE)
        if not get_image_region_role(self.region_role_name):
            self.region_role_name = REGION_ROLE
            success = False

        self.region_name_prefix = section.get("REGION_NAME_PREFIX", "")
        self.rctype_identifier = section.get("RCTYPE_IDENTIFIER", RCTYPE_Standard_IDENTIFIER)
        self.rctype_name = section.get("RCTYPE_NAME", RCTYPE_Standard_NAME)
        self.region_creator_role = section.get("REGION_CREATOR_ROLE", REGION_CREATOR_ROLE)
        self.describer_role = section.get("DESCRIBER_ROLE", DESCRIBER_ROLE)
        self.transcriber_role = section.get("TRANSCRIBER_ROLE", TRANSCRIBER_ROLE)
        self.color_start = section.get("COLOUR_START", color_start)

        return success


class Instructions:
    No_Instruction = "no"
    Polygon_Instruction = "Polygon"
    Circle_Instruction = "Circle"
    Point_Instruction = "Point"
    Linestring_Instruction = "Linestring"
    Rectangle_Instruction = "Rectangle"
    Move_Instruction = "Move"
    Change_Instruction = "Change"
    Add_Point = "Add_point"
    Remove_Point = "Remove_point"


preview = namedtuple("preview", "id path title image polygon_number rectangle_number circle_number point_number linestring_number")


class PreviewModelData:
    def __init__(
        self,
        id_image,
        path,
        title,
        image,
        polygon_number,
        rectangle_number,
        circle_number,
        point_number=0,
        linestring_number: int = 0,
        missing_file=False,
        is_active=False,
        error_image=False,
        warning_image=False,
        visual_rotation_degrees=0,
        exif_rotation_degrees=0,
        exif_orientation_present=False,
        image_metadata=None,
    ):
        self.id = id_image
        self.path = path
        self.title = title
        self.image = image
        self.polygon_number = polygon_number
        self.rectangle_number = rectangle_number
        self.circle_number = circle_number
        self.point_number = point_number
        self.linestring_number = linestring_number
        self.missing_file = missing_file
        self.is_active = is_active
        self.error_image = error_image
        self.warning_image = warning_image
        self.visual_rotation_degrees = visual_rotation_degrees
        self.exif_rotation_degrees = exif_rotation_degrees
        self.exif_orientation_present = exif_orientation_present
        self.image_metadata = image_metadata or {}


PREVIEW_HEIGHT = 500
CELL_PADDING = 1  # all sides
THUMBNAIL_MARGIN = 3
THUMBNAIL_FOOTER_PADDING = 3
TEXT_MARGIN = 3
TEXT_WIDTH = 30
TEXT_HEIGHT = 20

zoomin_factor = 0.8
point_size = 100

color_dark_red = QBrush(QColor(103, 40, 23))
color_dark_green = QBrush(QColor(0, 113, 77))
color_mid_yellow = QColor(102, 102, 0)

color_on_image_hoover = QColor(0, 255, 0, 50)

LOG_POPUP_BASE_STYLE = """
    QFrame#logPopupPanel {
        %s
        border: 1px solid rgb(90, 98, 112);
        border-radius: 6px;
    }
"""

LOGGING_STYLE = {
    logging.DEBUG: {
        "txt": QColor(255, 255, 255),
        "frame": LOG_POPUP_BASE_STYLE % "background-color: rgba(34, 113, 150, 220);",
        "icon": "info-40.svg",
    },
    logging.INFO: {
        "txt": QColor(255, 255, 255),
        "frame": LOG_POPUP_BASE_STYLE % "background-color: rgba(34, 113, 150, 220);",
        "icon": "info-40.svg",
    },
    logging.WARNING: {
        "txt": QColor(255, 180, 0),
        "frame": LOG_POPUP_BASE_STYLE % "background-color: rgba(150, 146, 34, 220);",
        "icon": "warning-40.svg",
    },
    logging.ERROR: {
        "txt": QColor("#f3523a"),
        "frame": LOG_POPUP_BASE_STYLE % "background-color: rgba(130, 67, 34, 220);",
        "icon": "error-40.svg",
    },
    logging.CRITICAL: {
        "txt": QColor(190, 90, 210),
        "frame": LOG_POPUP_BASE_STYLE % "background-color: rgba(128, 0, 128, 220);",
        "icon": "error-40.svg",
    },
    "finished": {
        "txt": QColor(120, 220, 170),
        "frame": LOG_POPUP_BASE_STYLE % "background-color: rgba(92, 150, 135, 220);",
        "icon": "flat_tick_icon.svg",
    },
}


def get_image_region_role(name: str):
    new_id = ""
    for x in image_region_role:
        if x[0] == name:
            new_id = x[1]

    return new_id


def load_config(config_file: Path | str):
    config = configparser.ConfigParser()

    success = True
    if Path(config_file).exists():
        config.read(config_file)
    else:
        success = False

    config_default = {
        "TAG_DESCRIBER": TAG_DESCRIBER,
        "TAG_TRANSCRIBER": TAG_TRANSCRIBER,
        "CONTRIBUTOR_TAG": CONTRIBUTOR_TAG,
    }
    if config.has_section("TAGS"):
        if config.has_option("TAGS", "TAG_DESCRIBER"):
            config_default["TAG_DESCRIBER"] = config["TAGS"]["TAG_DESCRIBER"].strip()
        else:
            success = False
        if config.has_option("TAGS", "TAG_TRANSCRIBER"):
            config_default["TAG_TRANSCRIBER"] = config["TAGS"]["TAG_TRANSCRIBER"].strip()
        else:
            success = False

        if config.has_option("TAGS", "CONTRIBUTOR_TAG"):
            config_default["CONTRIBUTOR_TAG"] = config["TAGS"]["CONTRIBUTOR_TAG"].strip()
        else:
            success = False
    else:
        success = False

    config_polygon = GeometryConfigs()
    polygon_success = config_polygon.set_values(config, "POLYGON")
    config_rectangle = GeometryConfigs()
    rectangle_success = config_rectangle.set_values(config, "RECTANGLE")
    config_circle = GeometryConfigs()
    circle_success = config_circle.set_values(config, "CIRCLE")

    config_point = GeometryConfigs()
    point_success = config_point.set_values(config, "POINT")

    config_linestring = GeometryConfigs()
    linestring_success = config_linestring.set_values(config, "LINESTRING")

    success = success and polygon_success and rectangle_success and circle_success and point_success and linestring_success

    return success, config_default, config_polygon, config_rectangle, config_circle, config_point, config_linestring


def list_of_points_to_list(poly):
    p_list = []
    for p in poly:
        p_list.append([p.x(), p.y()])

    return p_list


def fill_model_from_json(parent, d):
    if isinstance(d, dict):
        for key, value in d.items():
            it = QStandardItem(str(key))
            if isinstance(value, dict):
                parent.appendRow(it)
                fill_model_from_json(it, value)
            else:
                it2 = QStandardItem(str(value))
                parent.appendRow([it, it2])
