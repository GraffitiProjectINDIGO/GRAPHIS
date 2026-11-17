"""Draft-4 Region Member Of references use Region Identifiers, never database keys."""

import copy
import json
import logging
import re

from iptc_iris import normalize_metadata

from graphis.interface.imgregion_adapter import IMGREGION_STANDARD

logger = logging.getLogger(__name__)

MEMBERSHIP_KEYS = ("rMemberOf", "RMemberOf", "Iptc4xmpExt:rMemberOf", "ImageRegionMemberOf")
OBSOLETE_PARENT_KEYS = ("parentId", "parentRegionId", "parentRId", "rParent", "RParent", "partOf")
PARENT_KEYS = MEMBERSHIP_KEYS


def normalize_region_membership(region):
    region = copy.deepcopy(region)
    for key in OBSOLETE_PARENT_KEYS:
        region.pop(key, None)
    parsed = normalize_metadata({"ImageRegion": [region]}, standard=IMGREGION_STANDARD).image_regions[0]
    for key in MEMBERSHIP_KEYS:
        region.pop(key, None)
    if "rMemberOf" in parsed.raw:
        region["rMemberOf"] = parsed.r_member_of
    return region


def region_identifier(region):
    value = region.get("rId", region.get("RId", ""))
    return str(value) if isinstance(value, (str, int)) else ""


def _without_boundary(region):
    """Membership only depends on rId and rMemberOf; dropping the boundary skips geometry validation."""
    if not isinstance(region, dict):
        return region
    return {key: value for key, value in region.items() if str(key).rsplit(":", 1)[-1].lower() != "regionboundary"}


def _membership_validation(regions):
    collection = normalize_metadata(
        {"ImageRegion": [_without_boundary(region) for region in regions]}, standard=IMGREGION_STANDARD
    ).image_regions
    issues = [
        issue for issue in collection.validation_result(ignore_dimensions=True).issues
        if issue.path.endswith(".rMemberOf")
    ]
    return collection, issues


def parent_object_map(regions, object_ids):
    """Map library-validated references to graph nodes without discarding malformed regions."""
    ids = [str(value) for value in object_ids]
    collection, issues = _membership_validation(regions)
    invalid_indices = set()
    for issue in issues:
        match = re.fullmatch(r"imageRegion\[(\d+)\]\.rMemberOf", issue.path)
        if match:
            invalid_indices.add(int(match.group(1)))
        logger.warning("%s: %s", issue.code, issue.message)
    by_identifier = {}
    duplicates = set()
    for region, object_id in zip(collection, ids, strict=True):
        identifier = region.r_id
        if isinstance(identifier, str) and identifier:
            if identifier in by_identifier:
                duplicates.add(identifier)
            by_identifier[identifier] = object_id
    for identifier in duplicates:
        by_identifier.pop(identifier, None)
    return {
        ids[index]: by_identifier[region.r_member_of]
        for index, region in enumerate(collection)
        if index not in invalid_indices and isinstance(region.r_member_of, str)
        and region.r_member_of in by_identifier
    }


def parent_map_from_rows(rows):
    regions = [json.loads(row["data"]) for row in rows]
    resolved = parent_object_map(regions, [row["id"] for row in rows])
    return {int(child): int(parent) for child, parent in resolved.items()}


def export_region_memberships(regions):
    """Use IPTC-IRIS checks before writing, preserving unresolved references as warnings."""
    regions = [normalize_region_membership(region) for region in regions]
    _collection, issues = _membership_validation(regions)
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        raise ValueError("; ".join(f"{issue.path}: {issue.message}" for issue in errors))
    for issue in issues:
        logger.warning("%s: %s", issue.code, issue.message)
    return regions
