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

from dataclasses import dataclass, field

from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor

from graphis.app.gui.resources import icon_path_str

CHILD_KEYS = (
    "children",
    "childRegions",
    "childImageRegions",
    "imageRegions",
    "regions",
    "subRegions",
)


def first_text(value, default=""):
    if isinstance(value, dict):
        if "x-default" in value:
            return str(value["x-default"])
        for item in value.values():
            text = first_text(item)
            if text:
                return text
    if isinstance(value, list):
        for item in value:
            text = first_text(item)
            if text:
                return text
    if isinstance(value, str):
        return value
    return default


def set_lang_text(region, key, value):
    if value:
        region[key] = {"x-default": value}
    else:
        region.pop(key, None)


def set_string_list(region, key, value):
    if value:
        region[key] = [value]
    else:
        region.pop(key, None)


def region_shape(region):
    boundary = region.get("regionBoundary") or region.get("RegionBoundary") or {}
    if isinstance(boundary, dict):
        return boundary.get("rbShape") or boundary.get("RbShape") or ""
    return ""


def boundary_shape_icon_path(shape):
    shape = str(shape or "").lower()
    if shape == "rectangle":
        return icon_path_str("rectangle.svg")
    if shape == "polygon":
        return icon_path_str("polygon.svg")
    if shape == "multipolygon":
        return icon_path_str("multipolygon.svg")
    if shape == "circle":
        return icon_path_str("circle.svg")
    if shape == "point":
        return icon_path_str("point.svg")
    if shape == "multipoint":
        return icon_path_str("multipoint.svg")
    if shape in {"line", "linestring"}:
        return icon_path_str("linestring.svg")
    if shape == "multilinestring":
        return icon_path_str("multilinestring.svg")
    return ""


def region_role(region):
    return struct_name(region.get("rRole") or region.get("RRole") or [])


def region_type(region):
    return struct_name(region.get("rCtype") or region.get("RCtype") or [])


def struct_name(value):
    if isinstance(value, list) and value:
        return struct_name(value[0])
    if isinstance(value, dict):
        return first_text(value.get("name") or value.get("Name") or value)
    return first_text(value)


def find_child_list(region):
    for key in CHILD_KEYS:
        value = region.get(key)
        if isinstance(value, list):
            return key, value
    return None, None


@dataclass
class RegionNode:
    object_id: str
    parent_id: str | None
    region: dict
    path: list
    depth: int = 0
    children: list["RegionNode"] = field(default_factory=list)
    graph_pos: QPointF | None = None
    validation_issues: list = field(default_factory=list)
    geometry_owner_id: str | None = None
    geometry_part_index: int | None = None
    geometry_ring_index: int | None = None
    geometry_color: str = "#202832"

    @property
    def background_color(self):
        color = QColor(self.geometry_color)
        return QColor(
            (color.red() + 32) // 2,
            (color.green() + 40) // 2,
            (color.blue() + 50) // 2,
        ).name()

    @property
    def RegionID(self):
        return first_text(self.region.get("rId") or self.region.get("RId"), "")

    @property
    def title(self):
        return first_text(self.region.get("name") or self.region.get("Name"), self.RegionID or self.object_id)

    @property
    def person(self):
        return first_text(self.region.get("PersonInImage", []))

    @property
    def organisation(self):
        return first_text(self.region.get("OrganisationInImageName", []))

    @property
    def subtitle(self):
        parts = [part for part in (region_type(self.region), region_role(self.region), region_shape(self.region)) if part]
        return " | ".join(parts)

    @property
    def detail_lines(self):
        if self.geometry_owner_id is not None:
            return ["Geometry part of the same region", "Select to edit this part's geometry"]
        lines = []
        region_id = self.RegionID
        name = first_text(self.region.get("name") or self.region.get("Name"), "")
        role = region_role(self.region)
        content_type = region_type(self.region)

        if region_id:
            lines.append(f"rID: {region_id}")
        if name:
            lines.append(f"Name: {name}")
        if role:
            lines.append(f"Role: {role}")
        if content_type:
            lines.append(f"Type: {content_type}")

        return lines

    @property
    def validation_severity(self):
        if any(getattr(issue, "severity", "") == "error" for issue in self.validation_issues):
            return "error"
        if any(getattr(issue, "severity", "") == "warning" for issue in self.validation_issues):
            return "warning"
        return ""

    @property
    def validation_summary(self):
        if not self.validation_issues:
            return ""
        issue = self.validation_issues[0]
        return f"{getattr(issue, 'severity', '').upper()}: {getattr(issue, 'message', '')}"

    @property
    def validation_tooltip(self):
        lines = []
        for issue in self.validation_issues:
            lines.append(
                f"{getattr(issue, 'severity', '').upper()} {getattr(issue, 'path', '')} "
                f"{getattr(issue, 'code', '')}: {getattr(issue, 'message', '')}"
            )
        return "\n".join(lines)
