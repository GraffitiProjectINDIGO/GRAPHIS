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

"""Graphis adapter helpers for the imgregion API.

Graphis keeps scene geometry in image-pixel coordinates, while persisted object
metadata is canonical imgregion JSON. This module is the boundary between both
representations.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import logging
import re
from typing import Any

import numpy
from iptc_iris import (
    ImageRegion,
    ImageRegionList,
    MultiboundaryPart,
    Standard,
    ValidationIssue,
    ValidationResult,
    join_multiboundary_parts,
    split_multiboundary_parts,
)

# GRAPHIS creates multi-geometries, holes, memberships and depth orders, which the
# IPTC 2026.1 draft defines. Every imgregion call that validates or writes uses this profile.
IMGREGION_STANDARD: Standard = "2026.1-draft"

CONTRIBUTOR_TAG = "Contributor"
TAG_DESCRIBER = "Description"
TAG_TRANSCRIBER = "Title"

TAG_ALIASES = {
    "XMP-iptcExt:Contributor": CONTRIBUTOR_TAG,
    "XMP-dc:Description": TAG_DESCRIBER,
    "XMP-dc:Title": TAG_TRANSCRIBER,
    "RegionBoundary": "regionBoundary",
    "RId": "rId",
    "Name": "name",
    "RCtype": "rCtype",
    "RRole": "rRole",
}

LANG_ALT_TEXT_RE = re.compile(r"""^lang=(?P<quote>["'])(?P<language>[^"']+)(?P=quote)\s*(?P<text>.*)$""")
LANG_ALT_ITEMS_RE = re.compile(
    r"""(?:^|,\s*)lang=(?P<quote>["'])(?P<language>[^"']+)(?P=quote)\s*(?P<text>.*?)(?=,\s*lang=["']|$)"""
)
LANGUAGE_CODE_RE = re.compile(r"^(?:[a-z]{2,3}(?:-[A-Za-z]{2,8})?|x-default)$")
LANG_ALT_SUFFIX_RE = re.compile(r"^(?P<base>.+)-(?P<language>[a-z]{2,3}(?:-[A-Za-z]{2,8})?|x-default)$")
REGION_BOUNDARY_SHAPES = {
    "circle",
    "point",
    "multipoint",
    "polygon",
    "multipolygon",
    "rectangle",
    "linestring",
    "multilinestring",
}
REGION_BOUNDARY_BASE_SHAPES = {
    "multipoint": "point",
    "multilinestring": "linestring",
    "multipolygon": "polygon",
}
IMAGE_REGION_INDEX_RE = re.compile(r"imageRegion\[(\d+)\]")


def canonical_region_tag(tag: str) -> str:
    tag = str(tag)
    if tag in TAG_ALIASES:
        return TAG_ALIASES[tag]
    if ":" in tag:
        suffix = tag.rsplit(":", 1)[1]
        if suffix in {CONTRIBUTOR_TAG, TAG_DESCRIBER, TAG_TRANSCRIBER}:
            return suffix
    return tag


def storage_region_tag(tag: str) -> str:
    """Return the metadata key Graphis should store for a user-configured tag."""

    tag = str(tag)
    if ":" in tag:
        return tag
    return canonical_region_tag(tag)


def _list_value(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def text_value(value, default: str = "") -> str:
    """Return a UI-safe string from canonical imgregion text values."""
    if value is None:
        return default
    if isinstance(value, str):
        match = LANG_ALT_TEXT_RE.match(value.strip())
        if match is not None:
            return match.group("text")
        return value
    if isinstance(value, list):
        return text_value(value[-1], default) if value else default
    if isinstance(value, dict):
        if "x-default" in value:
            return text_value(value["x-default"], default)
        return text_value(next(iter(value.values()), default), default)
    return str(value)


def metadata_lang_alt_value(metadata: dict, tag: str) -> dict[str, str] | None:
    """Read a LangAlt text field from Graphis/canonical/tool-shaped metadata."""

    if not isinstance(metadata, dict):
        return None

    value = _metadata_lang_alt_from_suffixed_keys(metadata, tag)
    if value:
        return value

    for candidate in _metadata_tag_candidates(tag):
        if candidate in metadata:
            return lang_alt_value(metadata.get(candidate))

    dc_key = _dc_nested_key(tag)
    nested_dc = metadata.get("dc")
    if dc_key and isinstance(nested_dc, dict) and dc_key in nested_dc:
        return lang_alt_value(nested_dc.get(dc_key))

    return None


def metadata_value(metadata: dict, tag: str, default=None):
    """Read a metadata value by configured tag or known Graphis/tool aliases."""

    if not isinstance(metadata, dict):
        return default

    for candidate in _metadata_tag_candidates(tag):
        if candidate in metadata:
            return metadata.get(candidate)
    return default


def fold_lang_alt_suffix_keys(metadata):
    """Merge ExifTool-style ``Tag-lang`` sibling keys into LangAlt mappings."""

    if isinstance(metadata, list):
        return [fold_lang_alt_suffix_keys(item) for item in metadata]
    if not isinstance(metadata, dict):
        return metadata

    folded = {}
    suffix_items = {}
    for key, value in metadata.items():
        value = fold_lang_alt_suffix_keys(value)
        match = LANG_ALT_SUFFIX_RE.match(str(key))
        if match is not None:
            base = match.group("base")
            language = match.group("language")
            suffix_items.setdefault(base, {})[language] = value
        else:
            folded[key] = value

    for base, alternatives in suffix_items.items():
        existing = lang_alt_value(folded.get(base))
        if existing:
            alternatives = {**existing, **alternatives}
        folded[base] = alternatives

    return folded


def metadata_text_value(metadata: dict, tag: str, default: str = "") -> str:
    value = metadata_lang_alt_value(metadata, tag)
    return text_value(value, default) if value is not None else default


def lang_alt_value(value) -> dict[str, str] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(language): text_value(text) for language, text in value.items() if text_value(text)}
    if isinstance(value, list):
        merged = {}
        for item in value:
            item_value = lang_alt_value(item)
            if item_value:
                merged.update(item_value)
        return merged or None
    text = text_value(value).strip()
    if not text:
        return None
    if isinstance(value, str):
        alternatives = _parse_lang_alt_items(value)
        if alternatives:
            return alternatives
        match = LANG_ALT_TEXT_RE.match(value.strip())
        if match is not None:
            return {match.group("language"): match.group("text")}
    return {"x-default": text}


def _parse_lang_alt_items(value: str) -> dict[str, str] | None:
    matches = list(LANG_ALT_ITEMS_RE.finditer(value.strip()))
    if len(matches) < 2:
        return None
    return {match.group("language"): match.group("text") for match in matches}


def put_lang_alt_value_to_dict_or_remove(dict_attribute, tag, value: dict[str, str] | None):
    tag = storage_region_tag(tag)
    _remove_metadata_aliases(dict_attribute, tag)
    clean_value = {str(language): str(text) for language, text in (value or {}).items() if language and text}
    if clean_value:
        dict_attribute[tag] = clean_value
    return dict_attribute


def normalize_lang_alt_text_fields(dict_attribute, tags=(TAG_DESCRIBER, TAG_TRANSCRIBER)):
    for tag in tags:
        value = metadata_lang_alt_value(dict_attribute, tag)
        if value is not None:
            put_lang_alt_value_to_dict_or_remove(dict_attribute, tag, value)
    return dict_attribute


def update_lang_alt_default(existing_value, default_text: str) -> dict[str, str] | None:
    value = lang_alt_value(existing_value) or {}
    default_text = str(default_text or "").strip()
    if default_text:
        value["x-default"] = default_text
    else:
        value.pop("x-default", None)
    return value or None


def _metadata_tag_candidates(tag: str) -> tuple[str, ...]:
    canonical = canonical_region_tag(tag)
    suffix = str(tag).rsplit(":", 1)[-1]
    return tuple(
        dict.fromkeys(
            candidate
            for candidate in (
                str(tag),
                canonical,
                suffix,
                _lower_first(canonical),
                _lower_first(suffix),
                canonical.casefold(),
                suffix.casefold(),
            )
            if candidate
        )
    )


def _metadata_lang_alt_from_suffixed_keys(metadata: dict, tag: str) -> dict[str, str] | None:
    value = {}
    for candidate in _metadata_tag_candidates(tag):
        candidate_value = lang_alt_value(metadata.get(candidate)) if candidate in metadata else None
        if candidate_value:
            value.update(candidate_value)
        for key, item_value in metadata.items():
            if not isinstance(key, str) or not key.startswith(f"{candidate}-"):
                continue
            language = key[len(candidate) + 1 :]
            if LANGUAGE_CODE_RE.match(language) is None:
                continue
            text = text_value(item_value).strip()
            if text:
                value[language] = text
    return value or None


def put_metadata_value_to_dict_or_remove(dict_attribute, tag, value):
    tag = storage_region_tag(tag)
    _remove_metadata_aliases(dict_attribute, tag)
    if value:
        dict_attribute[tag] = value
    return dict_attribute


def _dc_nested_key(tag: str) -> str:
    canonical = canonical_region_tag(tag)
    if canonical in {TAG_DESCRIBER, TAG_TRANSCRIBER}:
        return _lower_first(canonical)
    return ""


def _remove_metadata_aliases(dict_attribute, tag):
    for candidate in _metadata_tag_candidates(tag):
        dict_attribute.pop(candidate, None)
    dc_key = _dc_nested_key(tag)
    nested_dc = dict_attribute.get("dc")
    if dc_key and isinstance(nested_dc, dict):
        nested_dc.pop(dc_key, None)
        if not nested_dc:
            dict_attribute.pop("dc", None)


def _lower_first(value: str) -> str:
    return value[:1].lower() + value[1:] if value else ""


def language_alternative_items(value, default_language: str = "x-default") -> list[tuple[str, str]]:
    """Return language-alternative text as ordered ``(language, text)`` pairs."""

    if value is None:
        return []
    if isinstance(value, dict):
        items = []
        for language, text in value.items():
            items.append((str(language), text_value(text)))
        return items

    text = text_value(value).strip()
    return [(default_language, text)] if text else []


def language_alternative_value(default_text: str, alternatives: list[tuple[str, str]]) -> dict[str, str] | None:
    """Build canonical LangAlt data from UI values."""

    value = {}
    default_text = str(default_text or "").strip()
    if default_text:
        value["x-default"] = default_text

    for language, text in alternatives:
        language = str(language or "").strip()
        text = str(text or "").strip()
        if language and text:
            value[language] = text

    return value or None


def put_lang_alt_to_dict_or_remove(dict_attribute, tag, default_text: str, alternatives: list[tuple[str, str]]):
    tag = storage_region_tag(tag)
    _remove_metadata_aliases(dict_attribute, tag)
    value = language_alternative_value(default_text, alternatives)
    if value:
        dict_attribute[tag] = value
    return dict_attribute


def entity_identifiers(entity: dict) -> list:
    return _list_value(entity.get("identifiers", entity.get("Identifier", [])))


def entity_identifier(entity: dict, default: str = "") -> str:
    values = entity_identifiers(entity)
    return text_value(values[-1], default) if values else default


def entity_name(entity: dict, default: str = "") -> str:
    value = entity.get("name", entity.get("Name", default))
    return text_value(value, default)


def entity_roles(entity: dict) -> list:
    return [text_value(role) for role in _list_value(entity.get("role", entity.get("Role", [])))]


def _entity(identifier: str = "", name: str = "", role: str = "", *, name_as_list: bool = False) -> dict:
    data = {}
    if identifier:
        data["identifiers"] = [identifier]
    if name:
        data["name"] = [name] if name_as_list else name
    if role:
        data["role"] = [role]
    return data


def put_text_to_dict_or_remove(dict_attribute, tag, text: str):
    tag = storage_region_tag(tag)
    if text == "":
        if dict_attribute.get(tag, ""):
            dict_attribute.pop(tag)
    else:
        dict_attribute[tag] = text

    return dict_attribute


def put_struct_to_dict_or_remove(dict_attribute, tag, indentifier: str, name: str):
    tag = storage_region_tag(tag)
    _remove_metadata_aliases(dict_attribute, tag)
    if indentifier or name:
        dict_attribute[tag] = [_entity(indentifier, name)]

    return dict_attribute


def find_key_role(dict_attribute, dict_value, role):
    value = _list_value(metadata_value(dict_attribute, dict_value, []))
    if value:
        for idx, item in enumerate(value):
            roles = entity_roles(item)
            if roles:
                if roles[0] == role:
                    return True, idx

    return False, 0


def put_struc_tag_name_list(dict_attribute, tag, role, indentifier, name):
    tag = storage_region_tag(tag)
    success, idx = find_key_role(dict_attribute, tag, role)
    existing = _list_value(metadata_value(dict_attribute, tag, []))
    _remove_metadata_aliases(dict_attribute, tag)
    if success:
        if indentifier or name:
            existing[idx] = _entity(indentifier, name, role, name_as_list=True)
        else:
            existing.pop(idx)
    else:
        if indentifier or name:
            existing = existing if isinstance(existing, list) else [existing] if isinstance(existing, dict) else []
            existing.append(_entity(indentifier, name, role, name_as_list=True))
    if existing:
        dict_attribute[tag] = existing

    return dict_attribute


def put_struc_tag(dict_attribute, tag, role, indentifier, name):
    tag = storage_region_tag(tag)
    success, idx = find_key_role(dict_attribute, tag, role)
    existing = _list_value(metadata_value(dict_attribute, tag, []))
    _remove_metadata_aliases(dict_attribute, tag)
    if success:
        if indentifier or name:
            existing[idx] = _entity(indentifier, name, role)
        else:
            existing.pop(idx)
    else:
        if indentifier or name:
            existing = existing if isinstance(existing, list) else [existing] if isinstance(existing, dict) else []
            existing.append(_entity(indentifier, name, role))
    if existing:
        dict_attribute[tag] = existing

    return dict_attribute


def append_struc_tag_namelist(dict_attribute, tag, role, indentifier, name):
    tag = storage_region_tag(tag)
    success, idx = find_key_role(dict_attribute, tag, role)
    existing = _list_value(metadata_value(dict_attribute, tag, []))
    _remove_metadata_aliases(dict_attribute, tag)
    if success:
        if indentifier or name:
            identifiers = entity_identifiers(existing[idx])
            names = _list_value(existing[idx].get("name", existing[idx].get("Name", [])))
            if (not identifiers or indentifier != identifiers[-1]) or (not names or name != names[-1]):
                existing[idx].setdefault("identifiers", identifiers).append(indentifier)
                existing[idx].setdefault("name", names).append(name)

    else:
        if indentifier or name:
            existing.append(_entity(indentifier, name, role, name_as_list=True))
    if existing:
        dict_attribute[tag] = existing

    return dict_attribute


def _strip_closing_duplicate(points: list) -> list:
    if len(points) < 2:
        return points
    first = points[0]
    last = points[-1]
    if first[0] == last[0] and first[1] == last[1]:
        return points[:-1]
    return points


def object_type_from_region(region: dict) -> str:
    boundary = region.get("regionBoundary", {}) if isinstance(region, dict) else {}
    shape = boundary.get("rbShape") if isinstance(boundary, dict) else None
    return shape if shape in REGION_BOUNDARY_SHAPES else "invalid"


def base_object_type(object_type: str) -> str:
    return REGION_BOUNDARY_BASE_SHAPES.get(object_type, object_type)


def boundary_from_pixel_coordinates(object_type: str, list_coordinates) -> dict[str, Any]:
    object_type = object_type.lower()
    if object_type == "polygon":
        points = _strip_closing_duplicate(list(list_coordinates))
        return {
            "rbShape": "polygon",
            "rbUnit": "pixel",
            "rbVertices": [{"rbX": point[0], "rbY": point[1]} for point in points],
        }

    if object_type == "rectangle":
        np_coordinates = numpy.array(list_coordinates)
        min_rec = numpy.min(np_coordinates, axis=0)
        max_rec = numpy.max(np_coordinates, axis=0)
        return {
            "rbShape": "rectangle",
            "rbUnit": "pixel",
            "rbX": float(min_rec[0]),
            "rbY": float(min_rec[1]),
            "rbW": float(max_rec[0] - min_rec[0]),
            "rbH": float(max_rec[1] - min_rec[1]),
        }

    if object_type == "circle":
        return {
            "rbShape": "circle",
            "rbUnit": "pixel",
            "rbX": list_coordinates[0],
            "rbY": list_coordinates[1],
            "rbRx": list_coordinates[2],
        }

    if object_type == "point":
        return {
            "rbShape": "point",
            "rbUnit": "pixel",
            "rbCoordinates": json.dumps([list_coordinates[0], list_coordinates[1]], separators=(",", ":")),
        }

    if object_type == "multipoint":
        return {
            "rbShape": "multipoint",
            "rbUnit": "pixel",
            "rbCoordinates": json.dumps(list_coordinates, separators=(",", ":")),
        }

    if object_type in {"line", "linestring"}:
        return {
            "rbShape": "linestring",
            "rbUnit": "pixel",
            "rbCoordinates": json.dumps(list_coordinates, separators=(",", ":")),
        }

    if object_type == "multilinestring":
        return {
            "rbShape": "multilinestring",
            "rbUnit": "pixel",
            "rbCoordinates": json.dumps(list_coordinates, separators=(",", ":")),
        }

    if object_type == "multipolygon":
        return {
            "rbShape": "multipolygon",
            "rbUnit": "pixel",
            "rbCoordinates": json.dumps(list_coordinates, separators=(",", ":")),
        }

    raise ValueError(f"Unsupported region object type: {object_type}")


def create_region_boundary(img_width, img_height, object_type, list_coordinates, unit: str = "relative"):
    pixel_boundary = boundary_from_pixel_coordinates(object_type, list_coordinates)
    if unit == "pixel":
        return pixel_boundary

    region = ImageRegion.from_raw(
        {"regionBoundary": pixel_boundary},
        image_width=img_width,
        image_height=img_height,
    )
    return region.change_unit(unit, image_width=img_width, image_height=img_height).as_dict()["regionBoundary"]


def pixel_coordinates_from_region(region: dict, img_width, img_height):
    image_region = ImageRegion.from_raw(
        region,
        image_width=img_width,
        image_height=img_height,
        allow_malformed=True,
    )
    boundary = image_region.as_dict()["regionBoundary"]
    if boundary.get("rbUnit") != "pixel":
        # Converting builds and validates a new region, so only convert when needed.
        pixel_region = image_region.change_unit("pixel", image_width=img_width, image_height=img_height)
        boundary = pixel_region.as_dict()["regionBoundary"]
    shape = boundary["rbShape"]

    if shape == "polygon":
        if "rbCoordinates" in boundary:
            coordinates = boundary["rbCoordinates"]
            if isinstance(coordinates, str):
                coordinates = json.loads(coordinates)
            return shape, coordinates
        coordinates = [[vertex["rbX"], vertex["rbY"]] for vertex in boundary["rbVertices"]]
        if coordinates:
            coordinates.append(coordinates[0])
        return shape, coordinates

    if shape == "rectangle":
        x = boundary["rbX"]
        y = boundary["rbY"]
        w = boundary["rbW"]
        h = boundary["rbH"]
        return shape, [[x, y], [x + w, y], [x + w, y + h], [x, y + h], [x, y]]

    if shape == "circle":
        return shape, [boundary["rbX"], boundary["rbY"], boundary["rbRx"]]

    if shape == "point":
        coordinates = boundary["rbCoordinates"]
        if isinstance(coordinates, str):
            coordinates = json.loads(coordinates)
        return shape, [coordinates[0], coordinates[1]]

    if shape == "multipoint":
        coordinates = boundary["rbCoordinates"]
        if isinstance(coordinates, str):
            coordinates = json.loads(coordinates)
        return shape, coordinates

    if shape == "linestring":
        coordinates = boundary["rbCoordinates"]
        if isinstance(coordinates, str):
            coordinates = json.loads(coordinates)
        return shape, coordinates

    if shape == "multilinestring":
        coordinates = boundary["rbCoordinates"]
        if isinstance(coordinates, str):
            coordinates = json.loads(coordinates)
        return shape, coordinates

    if shape == "multipolygon":
        coordinates = boundary["rbCoordinates"]
        if isinstance(coordinates, str):
            coordinates = json.loads(coordinates)
        return shape, coordinates

    raise ValueError(f"Unsupported region boundary shape: {shape}")


def valid_region_geometry_merge_modes(
    source_region: dict, target_region: dict, img_width=None, img_height=None, target_part_index: int | None = None
):
    modes = []
    candidates = list(_candidate_region_geometry_merge_modes(source_region, target_region))
    if (
        target_part_index is not None
        and region_shape_name(target_region) == "multipolygon"
        and region_shape_name(source_region) in {"rectangle", "polygon"}
    ):
        candidates.append("inner_polygon")
    for mode in candidates:
        try:
            merged = merge_region_geometries(
                target_region, source_region, img_width, img_height, mode, target_part_index=target_part_index
            )
        except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        issues = validate_region_data(merged, img_width=img_width, img_height=img_height)
        if not any(issue.severity == "error" for issue in issues):
            modes.append(mode)
    return modes


def combine_multigeometry_regions(target_region: dict, source_regions, img_width, img_height, mode: str) -> dict:
    """Build one multi-boundary, including existing target parts when present."""
    readers = {
        "multipoint": _points_from_boundary,
        "multilinestring": _lines_from_boundary,
        "multipolygon": _polygons_from_boundary,
    }
    if mode not in readers:
        raise ValueError(f"Unsupported multi-geometry type: {mode}")
    target = copy.deepcopy(target_region)
    target_boundary = _region_boundary(target_region)
    target_unit = target_boundary.get("rbUnit", "pixel")
    coordinates = target_boundary.get("rbCoordinates")
    empty_target = target_boundary.get("rbShape") == mode and coordinates in (None, [], "[]")
    regions = list(source_regions) if empty_target else [target_region, *source_regions]
    parts: list[MultiboundaryPart] = []
    for region in regions:
        boundary = _pixel_boundary(region, img_width, img_height)
        if boundary.get("rbShape") == mode:
            # An existing multi-geometry keeps the details of its parts.
            parts.extend(multigeometry_parts(boundary))
            continue
        if mode == "multipolygon" and boundary.get("rbShape") == "rectangle":
            _shape, ring = pixel_coordinates_from_region(region, img_width, img_height)
            coordinates = [[_closed_ring(ring)]]
        else:
            coordinates = readers[mode](boundary)
        # IPTC: Part Id, Name, and Description may be initialised from the combined source region.
        details = _part_details_from_region(region)
        parts.extend(MultiboundaryPart(part, **details) for part in coordinates)
    if len(parts) < 2:
        raise ValueError(f"{mode} requires at least two parts.")
    boundary = {"rbShape": mode, "rbUnit": "pixel"}
    set_multigeometry_parts(boundary, parts)
    target["regionBoundary"] = _boundary_to_unit(boundary, target_unit, img_width, img_height)
    _pixel_boundary(target, img_width, img_height)
    return target


def merge_region_geometries(
    target_region: dict, source_region: dict, img_width, img_height, mode: str, target_part_index: int | None = None
) -> dict:
    if mode in {"multipoint", "multilinestring", "multipolygon"}:
        if region_shape_name(target_region) != mode:
            raise ValueError("Choose an existing compatible multigeometry as the target.")
        return combine_multigeometry_regions(target_region, [source_region], img_width, img_height, mode)
    target = copy.deepcopy(target_region)
    target_boundary = _pixel_boundary(target_region, img_width, img_height)
    source_boundary = _pixel_boundary(source_region, img_width, img_height)
    target_unit = _region_boundary(target_region).get("rbUnit", "relative")
    target_unit = target_unit if target_unit in {"pixel", "relative"} else "relative"

    if mode == "inner_polygon":
        target_polygons = _polygons_from_boundary(target_boundary)
        source_polygons = _polygons_from_boundary(source_boundary)
        if len(source_polygons) != 1 or len(source_polygons[0]) != 1:
            raise ValueError("Inner polygon merges require one simple source polygon.")
        if target_boundary["rbShape"] == "multipolygon":
            if target_part_index is None or not 0 <= target_part_index < len(target_polygons):
                raise ValueError("Choose the polygon within the multipolygon that should contain the inner polygon.")
            target_polygons[target_part_index].append(source_polygons[0][0])
            merged_boundary = copy.deepcopy(target_boundary)
            merged_boundary["rbCoordinates"] = json.dumps(target_polygons, separators=(",", ":"))
        else:
            if len(target_polygons) != 1:
                raise ValueError("Choose a single containing polygon.")
            merged_boundary = {
                "rbShape": "polygon",
                "rbUnit": "pixel",
                "rbCoordinates": json.dumps(target_polygons[0] + [source_polygons[0][0]], separators=(",", ":")),
            }
    else:
        raise ValueError(f"Unsupported region geometry merge mode: {mode}")

    target["regionBoundary"] = _boundary_to_unit(merged_boundary, target_unit, img_width, img_height)
    _pixel_boundary(target, img_width, img_height)
    return target


def _candidate_region_geometry_merge_modes(source_region: dict, target_region: dict):
    source_shape = region_shape_name(source_region)
    target_shape = region_shape_name(target_region)
    if source_shape in {"point", "multipoint"} and target_shape == "multipoint":
        return ("multipoint",)
    if source_shape in {"linestring", "multilinestring"} and target_shape == "multilinestring":
        return ("multilinestring",)
    if source_shape in {"rectangle", "polygon", "multipolygon"} and target_shape in {
        "rectangle", "polygon", "multipolygon"
    }:
        modes = ["multipolygon"] if target_shape == "multipolygon" else []
        if source_shape in {"rectangle", "polygon"} and target_shape in {"rectangle", "polygon"}:
            modes.append("inner_polygon")
        return tuple(modes)
    return ()


def region_shape_name(region: dict) -> str:
    boundary = _region_boundary(region)
    return str(boundary.get("rbShape", "") or "")


def _region_boundary(region: dict) -> dict:
    boundary = region.get("regionBoundary", {}) if isinstance(region, dict) else {}
    if not isinstance(boundary, dict):
        raise ValueError("regionBoundary must be an object.")
    return boundary


def _pixel_boundary(region: dict, img_width, img_height) -> dict:
    image_region = ImageRegion.from_raw(
        region,
        image_width=img_width,
        image_height=img_height,
        allow_malformed=True,
    )
    return image_region.change_unit("pixel", image_width=img_width, image_height=img_height).as_dict()["regionBoundary"]


def _boundary_to_unit(boundary: dict, unit: str, img_width, img_height) -> dict:
    if unit == "pixel":
        return boundary
    image_region = ImageRegion.from_raw(
        {"regionBoundary": boundary},
        image_width=img_width,
        image_height=img_height,
        allow_malformed=True,
    )
    return image_region.change_unit(unit, image_width=img_width, image_height=img_height).as_dict()["regionBoundary"]


def _coordinate_value(boundary: dict):
    value = boundary.get("rbCoordinates")
    if isinstance(value, str):
        return json.loads(value)
    return value


def _closed_ring(points):
    ring = [list(point) for point in points]
    if ring and ring[0] != ring[-1]:
        ring.append(list(ring[0]))
    return ring


def _points_from_boundary(boundary: dict):
    shape = boundary.get("rbShape")
    coordinates = _coordinate_value(boundary)
    if shape == "point":
        return [coordinates]
    if shape == "multipoint":
        return list(coordinates)
    raise ValueError(f"Cannot read points from {shape} boundary.")


def _lines_from_boundary(boundary: dict):
    shape = boundary.get("rbShape")
    coordinates = _coordinate_value(boundary)
    if shape == "linestring":
        return [coordinates]
    if shape == "multilinestring":
        return list(coordinates)
    raise ValueError(f"Cannot read lines from {shape} boundary.")


def _polygons_from_boundary(boundary: dict):
    shape = boundary.get("rbShape")
    if shape == "rectangle":
        x, y, width, height = (boundary[key] for key in ("rbX", "rbY", "rbW", "rbH"))
        return [[_closed_ring([[x, y], [x + width, y], [x + width, y + height], [x, y + height]])]]
    if shape == "polygon":
        coordinates = _coordinate_value(boundary)
        if coordinates is not None:
            return [[_closed_ring(ring) for ring in coordinates]]
        vertices = boundary.get("rbVertices")
        if not isinstance(vertices, list):
            raise ValueError("polygon requires rbVertices or rbCoordinates.")
        return [[_closed_ring([[vertex["rbX"], vertex["rbY"]] for vertex in vertices])]]
    if shape == "multipolygon":
        return [[_closed_ring(ring) for ring in polygon] for polygon in _coordinate_value(boundary)]
    raise ValueError(f"Cannot read polygons from {shape} boundary.")


def update_region_boundary_from_pixels(region: dict, img_width, img_height, object_type: str, list_coordinates) -> dict:
    updated = copy.deepcopy(region) if isinstance(region, dict) else {}
    old_boundary = updated.get("regionBoundary", {})
    unit = old_boundary.get("rbUnit", "relative") if isinstance(old_boundary, dict) else "relative"
    unit = unit if unit in {"pixel", "relative"} else "relative"
    updated["regionBoundary"] = create_region_boundary(img_width, img_height, object_type, list_coordinates, unit=unit)
    return updated


def update_multigeometry_part_from_pixels(
    region: dict, img_width, img_height, part_index: int, coordinates, ring_index: int = 0, move_polygon: bool = False
) -> dict:
    updated = copy.deepcopy(region)
    boundary = _pixel_boundary(region, img_width, img_height)
    parts = _coordinate_value(boundary)
    shape = boundary["rbShape"]
    if shape not in {"polygon", "multipolygon", "multipoint", "multilinestring"}:
        raise ValueError("The selected region is not a multigeometry.")
    if shape in {"polygon", "multipolygon"}:
        if shape == "polygon":
            parts = _polygons_from_boundary(boundary)
        old_ring = parts[part_index][ring_index]
        ring = _closed_ring(_strip_closing_duplicate(list(coordinates)))
        if move_polygon and ring_index == 0:
            dx, dy = ring[0][0] - old_ring[0][0], ring[0][1] - old_ring[0][1]
            parts[part_index] = [[[x + dx, y + dy] for x, y in old] for old in parts[part_index]]
        else:
            parts[part_index][ring_index] = ring
    else:
        parts[part_index] = copy.deepcopy(coordinates)
    boundary["rbCoordinates"] = json.dumps(parts[0] if shape == "polygon" else parts, separators=(",", ":"))
    if shape == "polygon":
        boundary.pop("rbVertices", None)
    unit = _region_boundary(region).get("rbUnit", "relative")
    updated["regionBoundary"] = _boundary_to_unit(boundary, unit, img_width, img_height)
    _pixel_boundary(updated, img_width, img_height)
    return updated


def multigeometry_parts(boundary: dict) -> list[MultiboundaryPart]:
    """Return the parts of a multi-geometry boundary, each coupled with its part details.

    Operations that insert, remove, or reorder parts should edit this list and
    write it back with `set_multigeometry_parts`, so part details stay with
    their part and every Part Index is assigned from the final order.
    """
    return split_multiboundary_parts(boundary.get("rbCoordinates"), boundary.get("rbMbPartDetails"))


def set_multigeometry_parts(boundary: dict, parts) -> dict:
    """Write coupled parts back as rbCoordinates and rbMbPartDetails with fresh Part Index values."""
    coordinates, details = join_multiboundary_parts(parts)
    boundary["rbCoordinates"] = json.dumps(coordinates, separators=(",", ":"))
    if details:
        boundary["rbMbPartDetails"] = details
    else:
        boundary.pop("rbMbPartDetails", None)
    return boundary


def _part_details_from_region(region: dict) -> dict:
    """Return Part Id, Name, and Description initialised from a region being combined."""
    values = {
        "part_id": text_value(region.get("rId") or region.get("RId")).strip(),
        "part_name": text_value(region.get("name")).strip(),
        "part_description": text_value(metadata_value(region, TAG_DESCRIBER)).strip(),
    }
    return {key: value or None for key, value in values.items()}


def multigeometry_part(region: dict, part_index: int) -> MultiboundaryPart:
    """Return one part of a multi-geometry region with its part details."""
    parts = multigeometry_parts(_region_boundary(region))
    if not 0 <= part_index < len(parts):
        raise ValueError("Choose a valid part of the multigeometry.")
    return parts[part_index]


def apply_part_details_to_region(region: dict, part: MultiboundaryPart, used_region_ids=()) -> dict:
    """Restore a detached region's rId, name, and description from its former part details.

    The rId is only restored when no other region uses it, because Region
    Identifiers must stay unique. Values the part does not have are left as
    they are.
    """
    if part.part_id and part.part_id not in set(used_region_ids):
        region["rId"] = part.part_id
    if part.part_name:
        region["name"] = {"x-default": part.part_name}
    if part.part_description:
        put_metadata_value_to_dict_or_remove(region, TAG_DESCRIBER, {"x-default": part.part_description})
    return region


def detach_multigeometry_part(region: dict, img_width, img_height, part_index: int):
    """Return the remaining region and a detached single-part boundary in the original units."""
    boundary = _region_boundary(region)
    shape = boundary.get("rbShape")
    base_shape = {"multipoint": "point", "multilinestring": "linestring", "multipolygon": "polygon"}.get(shape)
    if base_shape is None:
        raise ValueError("Choose a part of a multipoint, multilinestring, or multipolygon.")
    parts = _coordinate_value(boundary)
    if not 0 <= part_index < len(parts) or len(parts) < 2:
        raise ValueError("Choose a valid part of a multigeometry with at least two parts.")
    detached_boundary = copy.deepcopy(boundary)
    detached_boundary["rbShape"] = base_shape
    detached_boundary["rbCoordinates"] = json.dumps(parts[part_index], separators=(",", ":"))
    detached_boundary.pop("rbMbPartDetails", None)
    remaining = remove_multigeometry_part(region, img_width, img_height, part_index)
    _pixel_boundary({"regionBoundary": detached_boundary}, img_width, img_height)
    return remaining, detached_boundary


def remove_multigeometry_part(region: dict, img_width, img_height, part_index: int, ring_index: int = 0) -> dict:
    updated = copy.deepcopy(region)
    boundary = _region_boundary(updated)
    shape = boundary.get("rbShape")
    if shape == "polygon":
        if ring_index == 0:
            updated.pop("regionBoundary", None)
            return updated
        rings = _coordinate_value(boundary)
        del rings[ring_index]
        boundary["rbCoordinates"] = json.dumps(rings, separators=(",", ":"))
        _pixel_boundary(updated, img_width, img_height)
        return updated
    base_shape = {"multipoint": "point", "multilinestring": "linestring", "multipolygon": "polygon"}.get(shape)
    if base_shape is None:
        raise ValueError("The selected region is not a multigeometry.")
    parts = multigeometry_parts(boundary)
    if shape == "multipolygon" and ring_index > 0:
        part = parts[part_index]
        rings = copy.deepcopy(part.coordinates)
        del rings[ring_index]
        parts[part_index] = dataclasses.replace(part, coordinates=rings)
    else:
        del parts[part_index]
    if len(parts) == 1 and not (shape == "multipolygon" and ring_index > 0):
        # A single remaining part is a plain shape; part details only exist for multi-geometries.
        boundary["rbShape"] = base_shape
        boundary["rbCoordinates"] = json.dumps(parts[0].coordinates, separators=(",", ":"))
        boundary.pop("rbMbPartDetails", None)
    else:
        set_multigeometry_parts(boundary, parts)
    _pixel_boundary(updated, img_width, img_height)
    return updated


def change_region_unit(region: dict, unit: str, img_width, img_height) -> dict:
    """Return a region copy with its boundary converted to pixel or relative units."""

    image_region = ImageRegion.from_raw(
        region,
        image_width=img_width,
        image_height=img_height,
        allow_malformed=True,
    )
    return image_region.change_unit(
        unit,
        image_width=img_width,
        image_height=img_height,
        allow_malformed=True,
    ).as_diagnostic_dict()


def validate_region_data(region: dict, img_width=None, img_height=None, path: str = "imageRegion[0]"):
    image_region = ImageRegion.from_raw(
        region,
        image_width=img_width,
        image_height=img_height,
        allow_malformed=True,
    )
    return image_region.validate(
        path,
        image_width=img_width,
        image_height=img_height,
        ignore_dimensions=img_width is None or img_height is None,
    )


def validate_image_regions_result(regions: list[dict], img_width=None, img_height=None):
    image_regions = ImageRegionList.from_raw(
        regions,
        image_width=img_width,
        image_height=img_height,
        allow_malformed=True,
        standard=IMGREGION_STANDARD,
    )
    return image_regions.validation_result(ignore_dimensions=img_width is None or img_height is None)


def validate_image_regions(regions: list[dict], img_width=None, img_height=None):
    return validate_image_regions_result(regions, img_width=img_width, img_height=img_height).issues


def validate_image_object_result(objects, img_width=None, img_height=None):
    regions = []
    issues = []
    for index, obj in enumerate(objects):
        try:
            data = obj.get("data") if isinstance(obj, dict) else obj["data"]
            region = json.loads(data) if isinstance(data, str) else data
        except (KeyError, TypeError, json.JSONDecodeError) as err:
            issues.append(
                ValidationIssue(
                    "error",
                    "IMAGE_REGION_JSON_INVALID",
                    f"imageRegion[{index}]",
                    f"Image Region data is not valid JSON: {err}",
                )
            )
            region = {}
        regions.append(region if isinstance(region, dict) else {})

    try:
        result = validate_image_regions_result(regions, img_width=img_width, img_height=img_height)
        return ValidationResult(issues=issues + result.issues, overview_issues=result.overview_issues)
    except Exception as err:
        issues.append(
            ValidationIssue(
                "error",
                "IMAGE_REGION_LIST_INVALID",
                "imageRegion",
                f"Image Region list validation failed: {err}",
            )
        )
    return ValidationResult(issues=issues)


def validate_image_object_rows(objects, img_width=None, img_height=None):
    return validate_image_object_result(objects, img_width=img_width, img_height=img_height).issues


def image_validation_issues_by_object(objects, issues):
    issues_by_object = {}
    for issue in issues:
        match = IMAGE_REGION_INDEX_RE.search(issue.path)
        if not match:
            continue
        index = int(match.group(1))
        if index < 0 or index >= len(objects):
            continue
        obj = objects[index]
        object_id = obj.get("id") if isinstance(obj, dict) else obj["id"]
        issues_by_object.setdefault(str(object_id), []).append(issue)
    return issues_by_object


def _issue_log_level(issue) -> int:
    """Map imgregion severities to log levels; info hints (e.g. deprecated rbVertices) are debug-only."""
    return {"error": logging.ERROR, "warning": logging.WARNING}.get(issue.severity, logging.DEBUG)


def log_validation_issues(issues, context: str = "Image Region"):
    logger = logging.getLogger(__name__)
    logged_keys = set()
    for issue in issues:
        key = (issue.severity, issue.code, issue.path)
        if key in logged_keys:
            continue
        logged_keys.add(key)
        level = _issue_log_level(issue)
        logger.log(level, "%s validation %s %s: %s", context, issue.path, issue.code, issue.message)
    return issues


def log_validation_result(result: ValidationResult, context: str = "Image Region"):
    logger = logging.getLogger(__name__)
    covered_paths = set()
    logged_keys = set()
    for issue in result.overview_issues:
        covered_paths.update(issue.paths)
        key = (issue.severity, issue.code, tuple(issue.paths))
        if key in logged_keys:
            continue
        logged_keys.add(key)
        level = _issue_log_level(issue)
        paths = ", ".join(issue.paths) if issue.paths else "imageRegion"
        logger.log(level, "%s validation %s %s: %s", context, paths, issue.code, issue.message)
    for issue in result.issues:
        if issue.path in covered_paths:
            continue
        key = (issue.severity, issue.code, issue.path)
        if key in logged_keys:
            continue
        logged_keys.add(key)
        level = _issue_log_level(issue)
        logger.log(level, "%s validation %s %s: %s", context, issue.path, issue.code, issue.message)
    return result.issues


def log_region_validation_issues(region: dict, img_width=None, img_height=None, context: str = "Image Region"):
    return log_validation_issues(
        validate_region_data(region, img_width=img_width, img_height=img_height),
        context=context,
    )


def log_image_object_validation_issues(
    objects,
    img_width=None,
    img_height=None,
    context: str = "Image Region",
    only_object_id=None,
):
    result = validate_image_object_result(objects, img_width=img_width, img_height=img_height)
    only_object_id = str(only_object_id) if only_object_id is not None else None
    logger = logging.getLogger(__name__)

    object_ids_by_index = {}
    for index, obj in enumerate(objects):
        object_id = obj.get("id") if isinstance(obj, dict) else obj["id"]
        object_ids_by_index[index] = str(object_id)

    covered_paths = set()
    for issue in result.overview_issues:
        covered_paths.update(issue.paths)
        issue_object_ids = [object_ids_by_index[index] for index in issue.indexes if index in object_ids_by_index]
        if only_object_id is not None and only_object_id not in issue_object_ids:
            continue
        issue_context = context
        if issue_object_ids:
            issue_context = f"{context} objects {', '.join(issue_object_ids)}"
        level = _issue_log_level(issue)
        paths = ", ".join(issue.paths) if issue.paths else "imageRegion"
        logger.log(level, "%s validation %s %s: %s", issue_context, paths, issue.code, issue.message)

    for issue in result.issues:
        if issue.path in covered_paths:
            continue
        issue_context = context
        issue_object_id = None
        match = IMAGE_REGION_INDEX_RE.search(issue.path)
        if match:
            index = int(match.group(1))
            if 0 <= index < len(objects):
                obj = objects[index]
                issue_object_id = obj.get("id") if isinstance(obj, dict) else obj["id"]
                issue_object_id = str(issue_object_id)
                issue_context = f"{context} object {issue_object_id}"
        if only_object_id is not None and issue_object_id != only_object_id:
            continue
        level = _issue_log_level(issue)
        logger.log(level, "%s validation %s %s: %s", issue_context, issue.path, issue.code, issue.message)
    return result.issues
