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

import json
import logging
import os
from collections.abc import Mapping

from iptc_iris import normalize_metadata, run_metadata_tool, write_image_regions

from graphis.db.db_handler import DBHandler
from graphis.interface.imgregion_adapter import (
    CONTRIBUTOR_TAG,
    IMGREGION_STANDARD,
    TAG_DESCRIBER,
    TAG_TRANSCRIBER,
    fold_lang_alt_suffix_keys,
    log_region_validation_issues,
    metadata_value,
    normalize_lang_alt_text_fields,
    object_type_from_region,
    put_metadata_value_to_dict_or_remove,
    validate_image_regions_result,
)
from graphis.interface.region_membership import export_region_memberships, normalize_region_membership

logger = logging.getLogger(__name__)


def write_graphis_image_regions(path, regions, *, executable, tool="exiftool", keep_original=False):
    """Write GRAPHIS regions with IPTC-IRIS; ExifTool warnings raise `MetadataToolWarning`."""

    regions = export_region_memberships(regions)
    return write_image_regions(
        path,
        regions,
        executable=executable,
        tool=tool,
        keep_original=keep_original,
        validate=False,
        standard=IMGREGION_STANDARD,
    )


def _metadata_tags(metadata_tags: Mapping[str, str] | None = None) -> dict[str, str]:
    tags = {
        "TAG_DESCRIBER": TAG_DESCRIBER,
        "TAG_TRANSCRIBER": TAG_TRANSCRIBER,
        "CONTRIBUTOR_TAG": CONTRIBUTOR_TAG,
    }
    if metadata_tags:
        tags.update({key: value for key, value in metadata_tags.items() if value})
    return tags


def _normalize_configured_region_tags(region: dict, metadata_tags: Mapping[str, str] | None = None) -> dict:
    tags = _metadata_tags(metadata_tags)
    data = fold_lang_alt_suffix_keys(region)
    data = normalize_region_membership(data)
    boundary = data.get("regionBoundary") or {}
    if isinstance(boundary, dict):
        for detail in boundary.get("rbMbPartDetails") or []:
            if isinstance(detail, dict) and isinstance(detail.get("rbMbPdPartId"), (str, int)):
                detail["rbMbPdPartId"] = str(detail["rbMbPdPartId"])
    normalize_lang_alt_text_fields(data, tags=(tags["TAG_DESCRIBER"], tags["TAG_TRANSCRIBER"]))
    contributor_value = metadata_value(data, tags["CONTRIBUTOR_TAG"])
    if contributor_value:
        put_metadata_value_to_dict_or_remove(data, tags["CONTRIBUTOR_TAG"], contributor_value)
    return data


def read_image_region_metadata(path, path_to_metadata_tool, tool: str = "exiftool"):
    """Read image metadata through IPTC-IRIS' metadata-tool backend."""

    return run_metadata_tool(path, tool, executable=path_to_metadata_tool, standard=IMGREGION_STANDARD)


def parse_img_region(
    region: dict,
    img_width: int,
    img_height: int,
    metadata_tags: Mapping[str, str] | None = None,
):
    """Normalize one Image Region and return Graphis object metadata.

    Graphis persists the returned `data` as canonical IPTC-IRIS JSON. Pixel
    conversion for the scene is handled at the UI boundary.
    """

    metadata = normalize_metadata(
        {
            "imageWidth": img_width,
            "imageHeight": img_height,
            "imageRegion": [fold_lang_alt_suffix_keys(region)],
        },
        standard=IMGREGION_STANDARD,
    )
    image_regions = metadata.image_regions.as_diagnostic_dict_list()
    data = image_regions[0] if image_regions else {}
    data = _normalize_configured_region_tags(data, metadata_tags)
    object_type = object_type_from_region(data)
    log_region_validation_issues(data, img_width=img_width, img_height=img_height, context="Imported Image Region")
    return object_type, data, ""


def meta_writer(
    db1: DBHandler,
    user: str,
    keep_orig: bool = False,
    path_to_metadata_tool: str = "exiftool",
    metadata_tool: str = "exiftool",
    metadata_tags: Mapping[str, str] | None = None,
) -> bool:
    logger.info("Write data to image - ImageRegions.")

    count_image_written = 0
    count_image_failed = 0
    count_image_warning = 0

    db = DBHandler()
    db.db_load(db1.db_path, user)
    db.db_user = user

    images = db.db_load_images_list()

    for img in images:
        new_path = os.path.normpath(os.path.join(db1.db_path, img["path"]))
        force_change = bool(img["deleted_orig_tag"])

        if img["s_count"] > 0 or img["deleted_orig_tag"]:
            objects = db.db_load_objects_image(img["id"])
            img_regions = []

            try:
                for obj in objects:
                    if obj["changed"]:
                        force_change = True
                    img_region = json.loads(obj["data"])
                    img_region = _normalize_configured_region_tags(img_region, metadata_tags)
                    img_regions.append(img_region)
            except (KeyError, TypeError, json.JSONDecodeError):
                count_image_failed += 1
                logger.error("%s: Writing failed - region metadata could not be prepared.", new_path)
                logger.debug("Image Region metadata preparation details for %s", new_path, exc_info=True)
                continue

            validation_result = validate_image_regions_result(
                img_regions,
                img_width=img["width"],
                img_height=img["height"],
            )
            validation_issues = validation_result.overview_issues + validation_result.issues
            has_validation_errors = any(issue.severity == "error" for issue in validation_issues)
            has_validation_warnings = any(issue.severity == "warning" for issue in validation_issues)

            if has_validation_warnings:
                count_image_warning += 1
                logger.warning("%s: data warnings present.", new_path)

            if force_change:
                if has_validation_errors:
                    count_image_failed += 1
                    logger.error("%s: Writing failed - region validation failed.", new_path)
                    continue

                try:
                    write_graphis_image_regions(
                        new_path,
                        img_regions,
                        executable=path_to_metadata_tool,
                        tool=metadata_tool,
                        keep_original=keep_orig,
                    )
                except Exception as err:
                    count_image_failed += 1
                    logger.error("%s: Writing failed - %s", new_path, err)
                    logger.debug("EXIF writing failure details for %s", new_path, exc_info=True)
                else:
                    count_image_written += 1

    logger.info(
        "Metadata writing finished: %i images written successfully, %i images failed, %i images with warnings.",
        count_image_written,
        count_image_failed,
        count_image_warning,
        extra={"finished": True},
    )
    return count_image_failed == 0
