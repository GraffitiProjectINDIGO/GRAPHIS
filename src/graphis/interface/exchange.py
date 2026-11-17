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

from __future__ import annotations

import ast
import csv
import json
import logging
import os
import traceback
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from multiprocessing import get_context
from pathlib import Path
from queue import Empty
from typing import Any

import numpy

from graphis.db.db_handler import DBHandler
from graphis.interface.image_importer import (
    import_image,
    resolved_image_path,
    store_image_regions,
    store_preview,
)
from graphis.interface.image_loader import image_loader
from graphis.interface.imgregion_adapter import (
    create_region_boundary,
    metadata_text_value,
    pixel_coordinates_from_region,
    put_struc_tag,
    put_text_to_dict_or_remove,
    text_value,
)

logger = logging.getLogger(__name__)


CSV_ENCODING = "utf-8-sig"
CSV_DIALECT = {
    "delimiter": ",",
    "quotechar": '"',
    "doublequote": True,
}
CSV_WRITER_DIALECT = {
    **CSV_DIALECT,
    "quoting": csv.QUOTE_ALL,
    "lineterminator": "\n",
}
CSV_READER_DIALECT = {
    **CSV_DIALECT,
    "quoting": csv.QUOTE_MINIMAL,
}
PROCESS_CONTEXT = get_context("spawn")


@dataclass
class CsvImportResult:
    imported_images: int = 0
    added_objects: int = 0
    duplicate_objects: int = 0
    skipped_rows: int = 0
    missing_images: int = 0
    skipped_unreadable_images: int = 0


def export_rectangle_csv(
    objects: Iterable[Mapping[str, Any]],
    output_path: str | Path,
    db_path: str | Path,
    describer_tag: str,
    transcriber_tag: str,
) -> int:
    """Export Image Region objects to the rectangle CSV exchange format."""
    written = 0
    with Path(output_path).open("w", newline="", encoding=CSV_ENCODING) as fid:
        csv_writer = csv.writer(fid, **CSV_WRITER_DIALECT)
        csv_writer.writerow(
            [
                "image",
                "type",
                "RId",
                "UpperLeftX",
                "UpperLeftY",
                "Width",
                "Height",
                describer_tag,
                transcriber_tag,
                "Polygon",
            ]
        )

        for obj in objects:
            row = _rectangle_csv_row(obj, db_path, describer_tag, transcriber_tag)
            if row is None:
                continue
            csv_writer.writerow(row)
            written += 1

    return written


def import_rectangle_csv(
    csv_path: str | Path,
    db_path: str | Path,
    user: str,
    describer_tag: str,
    transcriber_tag: str,
    contributor_tag: str,
    region_creator_roles: Mapping[str, str],
    creator_identifier: str,
    creator_name: str,
    metadata_tool: str,
    metadata_tool_path,
) -> CsvImportResult:
    """Import Image Region objects from the rectangle CSV exchange format."""
    result = CsvImportResult()
    db = DBHandler()
    db.db_load(Path(db_path), user)
    db.db_user = user

    try:
        image_rows_by_path = _image_rows_by_absolute_path(db, Path(db_path))
        geometry_keys_by_image = _geometry_keys_by_image(db)

        with Path(csv_path).open("r", newline="", encoding=CSV_ENCODING) as fid:
            reader = csv.DictReader(fid, **CSV_READER_DIALECT)
            for row_number, row in enumerate(reader, start=2):
                image_path = _row_image_path(row, Path(csv_path).parent)
                if image_path is None:
                    result.skipped_rows += 1
                    logger.warning("Skipping CSV row %s without an image path.", row_number)
                    continue

                image_row = image_rows_by_path.get(_path_key(image_path))
                if image_row is None:
                    image_row = _import_missing_csv_image(
                        db,
                        image_path,
                        Path(db_path),
                        user,
                        describer_tag,
                        transcriber_tag,
                        contributor_tag,
                        metadata_tool,
                        metadata_tool_path,
                        result,
                    )
                    if image_row is None:
                        continue
                    image_rows_by_path[_path_key(image_path)] = image_row
                    geometry_keys_by_image[image_row["id"]] = _geometry_keys_for_image(db, image_row["id"])

                image_row = _ensure_csv_image_ready(
                    db,
                    image_row,
                    image_path,
                    user,
                    describer_tag,
                    transcriber_tag,
                    contributor_tag,
                    metadata_tool,
                    metadata_tool_path,
                    result,
                )
                if image_row is None:
                    continue
                image_rows_by_path[_path_key(image_path)] = image_row
                geometry_keys_by_image[image_row["id"]] = _geometry_keys_for_image(db, image_row["id"])

                data = _region_from_csv_row(
                    row,
                    image_row["width"],
                    image_row["height"],
                    describer_tag,
                    transcriber_tag,
                    contributor_tag,
                    region_creator_roles,
                    creator_identifier,
                    creator_name,
                )
                if data is None:
                    result.skipped_rows += 1
                    logger.warning("Skipping malformed CSV row %s.", row_number)
                    continue

                object_type = data["regionBoundary"]["rbShape"]
                geometry_key = _geometry_key(data, image_row["width"], image_row["height"])
                if geometry_key in geometry_keys_by_image.setdefault(image_row["id"], set()):
                    result.duplicate_objects += 1
                    continue

                db.db_store_object(image_row["id"], object_type, data, user=user)
                geometry_keys_by_image[image_row["id"]].add(geometry_key)
                result.added_objects += 1
    finally:
        db.con.close()

    return result


def import_rectangle_csv_in_process(
    csv_path: str | Path,
    db_path: str | Path,
    user: str,
    describer_tag: str,
    transcriber_tag: str,
    contributor_tag: str,
    region_creator_roles: Mapping[str, str],
    creator_identifier: str,
    creator_name: str,
    metadata_tool: str,
    metadata_tool_path,
) -> CsvImportResult:
    queue = PROCESS_CONTEXT.Queue()
    process = PROCESS_CONTEXT.Process(
        target=_import_rectangle_csv_process,
        args=(
            queue,
            csv_path,
            db_path,
            user,
            describer_tag,
            transcriber_tag,
            contributor_tag,
            region_creator_roles,
            creator_identifier,
            creator_name,
            metadata_tool,
            metadata_tool_path,
        ),
    )
    process.start()

    while process.is_alive():
        try:
            kind, payload = queue.get(timeout=0.1)
            process.join()
            if kind == "result":
                return payload
            raise RuntimeError(payload)
        except Empty:
            continue

    process.join()
    try:
        kind, payload = queue.get_nowait()
    except Empty as err:
        raise RuntimeError(f"CSV import process exited with code {process.exitcode}.") from err

    if kind == "result":
        return payload
    raise RuntimeError(payload)


def _import_rectangle_csv_process(
    queue: Any,
    csv_path: str | Path,
    db_path: str | Path,
    user: str,
    describer_tag: str,
    transcriber_tag: str,
    contributor_tag: str,
    region_creator_roles: Mapping[str, str],
    creator_identifier: str,
    creator_name: str,
    metadata_tool: str,
    metadata_tool_path,
):
    try:
        queue.put(
            (
                "result",
                import_rectangle_csv(
                    csv_path,
                    db_path,
                    user,
                    describer_tag,
                    transcriber_tag,
                    contributor_tag,
                    region_creator_roles,
                    creator_identifier,
                    creator_name,
                    metadata_tool,
                    metadata_tool_path,
                ),
            )
        )
    except Exception:
        queue.put(("error", traceback.format_exc()))


def _rectangle_csv_row(
    obj: Mapping[str, Any],
    db_path: str | Path,
    describer_tag: str,
    transcriber_tag: str,
) -> list[str] | None:
    image = resolved_image_path(Path(obj["imgpath"]), Path(db_path)).resolve(strict=False).as_posix()
    data = json.loads(obj["data"])

    try:
        shape, coordinates = pixel_coordinates_from_region(
            data,
            obj["img_width"],
            obj["img_height"],
        )
    except (KeyError, TypeError, ValueError) as err:
        logger.warning("Skipping malformed Image Region in CSV export: %s", err)
        return None

    np_coords = numpy.array(coordinates)
    if shape == "circle":
        uplx = np_coords[0] - np_coords[2]
        uply = np_coords[1] - np_coords[2]
        width = np_coords[2] * 2
        height = np_coords[2] * 2
    else:
        min_rec = numpy.min(np_coords, axis=0)
        max_rec = numpy.max(np_coords, axis=0)
        uplx = min_rec[0]
        uply = min_rec[1]
        width = max_rec[0] - min_rec[0]
        height = max_rec[1] - min_rec[1]

    polygon = ""
    if shape == "polygon":
        polygon = str(numpy.array(coordinates).tolist())

    description = metadata_text_value(data, describer_tag)
    transcription = metadata_text_value(data, transcriber_tag)
    rid = text_value(data.get("rId", ""))

    return [
        image,
        shape,
        rid,
        str(int(uplx)),
        str(int(uply)),
        str(int(width)),
        str(int(height)),
        description,
        transcription,
        polygon,
    ]


def _row_image_path(row: Mapping[str, str], csv_folder: Path) -> Path | None:
    value = (row.get("image") or row.get("Image") or "").strip()
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = csv_folder / path
    return path


def _import_missing_csv_image(
    db: DBHandler,
    image_path: Path,
    db_path: Path,
    user: str,
    describer_tag: str,
    transcriber_tag: str,
    contributor_tag: str,
    metadata_tool: str,
    metadata_tool_path,
    result: CsvImportResult,
):
    if not image_path.exists():
        result.missing_images += 1
        logger.warning("Skipping CSV rows for missing image: %s", image_path)
        return None

    image_result = import_image(
        db,
        image_path,
        db_path,
        user,
        metadata_tool,
        metadata_tool_path,
        _metadata_tags(describer_tag, transcriber_tag, contributor_tag),
    )
    if image_result.imported:
        result.imported_images += 1
    elif image_result.skipped_unreadable:
        result.skipped_unreadable_images += 1
        return None

    return _image_row_for_path(db, image_path, db_path)


def _ensure_csv_image_ready(
    db: DBHandler,
    image_row,
    image_path: Path,
    user: str,
    describer_tag: str,
    transcriber_tag: str,
    contributor_tag: str,
    metadata_tool: str,
    metadata_tool_path,
    result: CsvImportResult,
):
    if image_row is None:
        return None
    if image_row["width"] and image_row["height"] and image_row["preview"] is not None:
        return image_row
    if not image_path.exists():
        result.missing_images += 1
        logger.warning("Skipping CSV rows for missing image: %s", image_path)
        return None

    try:
        image = image_loader(os.fspath(image_path))
    except Exception as err:
        result.skipped_unreadable_images += 1
        logger.warning("Skipping unreadable CSV image file: %s (%s)", image_path, err)
        return None

    if image.isNull() or image.width() <= 0 or image.height() <= 0:
        result.skipped_unreadable_images += 1
        logger.warning("Skipping unreadable CSV image file: %s", image_path)
        return None

    store_preview(db, image_row["id"], image, image_path)
    if image_row["orig_exif_image_region"] is None or image_row["image_metadata"] is None:
        store_image_regions(
            db,
            image_row["id"],
            image_path,
            image.width(),
            image.height(),
            user,
            metadata_tool,
            metadata_tool_path,
            _metadata_tags(describer_tag, transcriber_tag, contributor_tag),
        )
    return db.db_load_image_record(image_row["id"])


def _metadata_tags(describer_tag: str, transcriber_tag: str, contributor_tag: str) -> dict[str, str]:
    return {
        "TAG_DESCRIBER": describer_tag,
        "TAG_TRANSCRIBER": transcriber_tag,
        "CONTRIBUTOR_TAG": contributor_tag,
    }


def _region_from_csv_row(
    row: Mapping[str, str],
    img_width: int,
    img_height: int,
    describer_tag: str,
    transcriber_tag: str,
    contributor_tag: str,
    region_creator_roles: Mapping[str, str],
    creator_identifier: str,
    creator_name: str,
) -> dict | None:
    try:
        object_type = (row.get("type") or row.get("Type") or "").strip().lower()
        coordinates = _coordinates_from_csv_row(row, object_type)
        boundary = create_region_boundary(img_width, img_height, object_type, coordinates)
    except (KeyError, TypeError, ValueError, IndexError):
        return None

    data = {"regionBoundary": boundary}
    data = put_text_to_dict_or_remove(data, "rId", row.get("RId", ""))
    data = put_struc_tag(
        data,
        contributor_tag,
        region_creator_roles.get(object_type, ""),
        creator_identifier,
        creator_name,
    )
    data = put_text_to_dict_or_remove(data, describer_tag, row.get(describer_tag, ""))
    data = put_text_to_dict_or_remove(data, transcriber_tag, row.get(transcriber_tag, ""))
    return data


def _coordinates_from_csv_row(row: Mapping[str, str], object_type: str):
    uplx = _float_field(row, "UpperLeftX")
    uply = _float_field(row, "UpperLeftY")
    width = _float_field(row, "Width")
    height = _float_field(row, "Height")

    if object_type == "rectangle":
        return [[uplx, uply], [uplx + width, uply], [uplx + width, uply + height], [uplx, uply + height]]

    if object_type == "circle":
        return [uplx + width / 2, uply + height / 2, width / 2]

    if object_type == "polygon":
        polygon = (row.get("Polygon") or row.get("polygon") or "").strip()
        if polygon:
            return _parse_polygon_points(polygon)
        return [[uplx, uply], [uplx + width, uply], [uplx + width, uply + height], [uplx, uply + height]]

    raise ValueError(f"Unsupported CSV object type: {object_type}")


def _float_field(row: Mapping[str, str], field: str) -> float:
    return float((row.get(field) or "").strip())


def _parse_polygon_points(value: str):
    try:
        points = json.loads(value)
    except json.JSONDecodeError:
        points = ast.literal_eval(value)

    if not isinstance(points, list) or len(points) < 3:
        raise ValueError("Polygon needs at least three points.")
    return points


def _geometry_keys_by_image(db: DBHandler) -> dict[int, set[tuple]]:
    keys = {}
    for image in db.db_load_images_list():
        keys[image["id"]] = _geometry_keys_for_image(db, image["id"])
    return keys


def _geometry_keys_for_image(db: DBHandler, image_id: int) -> set[tuple]:
    image = db.db_load_image_record(image_id)
    if not image:
        return set()
    keys = set()
    for obj in db.db_load_objects_image(image_id):
        try:
            keys.add(_geometry_key(json.loads(obj["data"]), image["width"], image["height"]))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return keys


def _geometry_key(region: dict, img_width: int, img_height: int) -> tuple:
    shape, coordinates = pixel_coordinates_from_region(region, img_width, img_height)
    if shape == "circle":
        return shape, tuple(_round_coordinate(value) for value in coordinates)
    return shape, tuple(tuple(_round_coordinate(value) for value in point) for point in coordinates)


def _round_coordinate(value) -> float:
    return round(float(value), 3)


def _image_rows_by_absolute_path(db: DBHandler, db_path: Path) -> dict[str, Any]:
    return {_path_key(resolved_image_path(Path(row["path"]), db_path)): row for row in db.db_load_images_list()}


def _image_row_for_path(db: DBHandler, image_path: Path, db_path: Path):
    key = _path_key(image_path)
    for row in db.db_load_images_list():
        if _path_key(resolved_image_path(Path(row["path"]), db_path)) == key:
            return row
    return None


def _path_key(path: Path) -> str:
    return os.path.normcase(os.path.normpath(os.fspath(path.resolve(strict=False))))
