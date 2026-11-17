from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


def image_metadata_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return dict(data) if isinstance(data, Mapping) else {}
    return {}


def image_metadata_visual_rotation(image_metadata: Any) -> int:
    metadata = image_metadata_dict(image_metadata)
    return orientation_visual_rotation(_orientation_value(metadata))


def image_metadata_orientation_present(image_metadata: Any) -> bool:
    metadata = image_metadata_dict(image_metadata)
    orientation = _orientation_value(metadata)
    if orientation is None:
        return False
    if isinstance(orientation, str) and not orientation.strip():
        return False
    return True


def _orientation_value(metadata: Mapping[str, Any]) -> Any:
    return metadata.get("orientation")


def orientation_visual_rotation(orientation: Any) -> int:
    if orientation is None:
        return 0

    numeric = _orientation_int(orientation)
    if numeric is not None:
        return {
            1: 0,
            2: 0,
            3: 180,
            4: 180,
            5: 90,
            6: 90,
            7: 270,
            8: 270,
        }.get(numeric, 0)

    text = str(orientation).strip().lower()
    if not text:
        return 0
    if "180" in text or "bottom, right" in text or "bottom, left" in text:
        return 180
    if "270" in text or "90 ccw" in text or "left, bottom" in text or "right, bottom" in text:
        return 270
    if "90" in text or "right, top" in text or "left, top" in text:
        return 90
    return 0


def _orientation_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            return int(stripped)
    return None
