# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""The Image Regions of the image that is open in GRAPHIS.

``OpenImageRegions`` is the single place where the GUI gets region data for the open image:
the digitizer gets drawable geometry, the region editor gets rows, validation issues and
parent links. Each region is parsed and validated once and the results are kept while the
image stays open. The database is re-read on every access (cheap); parsing and validation
are repeated only for regions whose stored data changed, so edits, undo/redo and imports
are always reflected without explicit invalidation.
"""

import json
import logging

from graphis.interface.imgregion_adapter import (
    image_validation_issues_by_object,
    pixel_coordinates_from_region,
    validate_image_object_result,
)
from graphis.interface.region_membership import parent_map_from_rows

logger = logging.getLogger(__name__)

MULTI_GEOMETRY_TYPES = {"multipoint", "multilinestring", "multipolygon"}


class OpenImageRegions:
    def __init__(self, db, image_id):
        self.db = db
        self.image_id = image_id
        self._rows = []
        self._image = None
        self._state_key = None
        self._validation = None
        self._validation_done = False
        self._parent_map = None
        self._geometry = {}
        self._size_key = None

    # ---------------------------------------------------------------- data

    def _refresh(self):
        rows = [dict(row) for row in self.db.db_load_objects_image(self.image_id)]
        image = self.db.db_load_image_record(self.image_id)
        image = dict(image) if image else None
        key = (
            tuple((row.get("id"), row.get("object_type"), row.get("data")) for row in rows),
            None if image is None else (image.get("width"), image.get("height")),
        )
        if key != self._state_key:
            self._state_key = key
            self._rows = rows
            self._image = image
            self._validation = None
            self._validation_done = False
            self._parent_map = None
            if key[1] != self._size_key:
                self._geometry.clear()
                self._size_key = key[1]
            else:
                # Keep parsed geometry only for regions whose data is unchanged.
                current = {(row.get("id"), row.get("data")) for row in rows}
                self._geometry = {k: v for k, v in self._geometry.items() if k in current}

    @property
    def rows(self):
        """Database rows of all regions of the image, as dictionaries."""
        self._refresh()
        return self._rows

    @property
    def image(self):
        """The image record (including width and height), or None."""
        self._refresh()
        return self._image

    @property
    def size(self):
        image = self.image
        return (image["width"], image["height"]) if image else (None, None)

    # ---------------------------------------------------------- validation

    @property
    def validation_result(self):
        """IPTC-IRIS validation of all regions of the image, computed once per state."""
        self._refresh()
        if not self._validation_done:
            self._validation_done = True
            width, height = self.size
            try:
                self._validation = (
                    validate_image_object_result(self._rows, img_width=width, img_height=height)
                    if self._image else None
                )
            except Exception:
                logger.exception("Image Region validation failed for image %s", self.image_id)
                self._validation = None
        return self._validation

    @property
    def validation_issues(self):
        result = self.validation_result
        return result.issues if result is not None else []

    def issues_by_object(self):
        return image_validation_issues_by_object(self.rows, self.validation_issues)

    def parent_map(self):
        """Child object id -> parent object id from rMemberOf references."""
        self._refresh()
        if self._parent_map is None:
            self._parent_map = parent_map_from_rows(self._rows)
        return self._parent_map

    # ------------------------------------------------------------ geometry

    def geometry(self, row):
        """Pixel geometry ``(shape, coordinates)`` for drawing, or None if it cannot be drawn."""
        key = (row.get("id"), row.get("data"))
        if key not in self._geometry:
            self._geometry[key] = self._parse_geometry(row)
        return self._geometry[key]

    def _parse_geometry(self, row):
        try:
            data = json.loads(row["data"])
        except (KeyError, TypeError, json.JSONDecodeError):
            return None
        boundary = data.get("regionBoundary") if isinstance(data, dict) else None
        if not isinstance(boundary, dict):
            return None
        if row.get("object_type") in MULTI_GEOMETRY_TYPES and boundary.get("rbCoordinates") in (None, [], "[]"):
            return None
        width, height = self.size
        try:
            return pixel_coordinates_from_region(data, width, height)
        except (KeyError, TypeError, ValueError) as err:
            logger.warning("Cannot draw malformed Image Region object %s: %s", row.get("id"), err)
            return None

    def drawable_regions(self):
        """Yield ``(row, data, shape, coordinates)`` for every region that can be drawn."""
        for row in self.rows:
            geometry = self.geometry(row)
            if geometry is not None:
                yield row, json.loads(row["data"]), geometry[0], geometry[1]
