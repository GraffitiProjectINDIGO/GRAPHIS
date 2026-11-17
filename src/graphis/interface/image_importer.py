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

from __future__ import annotations

import copy
import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import rawpy
from iptc_iris import standard_exif_json
from PIL import Image
from PySide6 import QtCore
from PySide6.QtGui import QImageReader

from graphis.app.var_classes import PREVIEW_HEIGHT
from graphis.db.db_handler import DBHandler
from graphis.interface.image_loader import image_loader
from graphis.interface.meta_exif import parse_img_region, read_image_region_metadata

logger = logging.getLogger(__name__)


@dataclass
class ImageImportResult:
    imported: int = 0
    duplicates: int = 0
    skipped_unreadable: int = 0


@dataclass
class SingleImageImportResult:
    image_id: int | None = None
    imported: bool = False
    duplicate: bool = False
    skipped_unreadable: bool = False


def supported_image_extensions() -> set[str]:
    """Return extensions supported by Qt/Pillow without the RAW probe."""

    Image.init()
    pillow_formats = {ext.lower() for ext in Image.registered_extensions()}
    qt_formats = {f".{fmt.data().decode('utf-8').lower()}" for fmt in QImageReader.supportedImageFormats()}
    return pillow_formats | qt_formats


def is_raw_supported(file_path: Path) -> bool:
    try:
        with rawpy.imread(os.fspath(file_path)):
            return True
    except rawpy.LibRawUnsupportedThumbnailError:
        return True
    except (rawpy.LibRawError, OSError, ValueError, TypeError):
        return False


def is_supported_image_file(file_path: Path, known_extensions: set[str] | None = None) -> bool:
    if not file_path.is_file():
        return False
    if known_extensions is None:
        known_extensions = supported_image_extensions()
    if file_path.suffix.lower() in known_extensions:
        return True
    return is_raw_supported(file_path)


def image_files_in_folder(folder: Path, recursive: bool = False) -> list[Path]:
    known_extensions = supported_image_extensions()
    iterator = folder.rglob("*") if recursive else folder.glob("*")
    return sorted(path for path in iterator if is_supported_image_file(path, known_extensions))


def import_images(
    image_paths: list[Path],
    db_path: Path,
    user: str,
    metadata_tool: str,
    metadata_tool_path,
    metadata_tags: Mapping[str, str] | None = None,
) -> ImageImportResult:
    result = ImageImportResult()

    db = DBHandler()
    db.db_load(db_path, user)
    db.db_user = user

    try:
        for image_path in image_paths:
            image_result = import_image(db, image_path, db_path, user, metadata_tool, metadata_tool_path, metadata_tags)
            if image_result.imported:
                result.imported += 1
            elif image_result.duplicate:
                result.duplicates += 1
            elif image_result.skipped_unreadable:
                result.skipped_unreadable += 1
    finally:
        db.con.close()

    return result


def import_image(
    db: DBHandler,
    image_path: Path,
    db_path: Path,
    user: str,
    metadata_tool: str,
    metadata_tool_path,
    metadata_tags: Mapping[str, str] | None = None,
) -> SingleImageImportResult:
    stored_path = stored_image_path(image_path, db_path)
    image_id = db.db_store_image(stored_path)
    assert image_id is not None
    if image_id < 0:
        return SingleImageImportResult(duplicate=True)

    new_path = resolved_image_path(stored_path, db_path)
    try:
        image = image_loader(os.fspath(new_path))
    except Exception as err:
        db.db_delete_image(image_id)
        logger.warning("Skipping unreadable image file: %s (%s)", new_path, err)
        return SingleImageImportResult(skipped_unreadable=True)

    if image.isNull() or image.width() <= 0 or image.height() <= 0:
        db.db_delete_image(image_id)
        logger.warning("Skipping unreadable image file: %s", new_path)
        return SingleImageImportResult(skipped_unreadable=True)

    store_preview(db, image_id, image, new_path)
    store_image_regions(
        db,
        image_id,
        image_path,
        image.width(),
        image.height(),
        user,
        metadata_tool,
        metadata_tool_path,
        metadata_tags,
    )
    return SingleImageImportResult(image_id=image_id, imported=True)


def stored_image_path(image_path: Path, db_path: Path) -> Path:
    try:
        return Path(os.path.relpath(image_path, db_path))
    except ValueError:
        return image_path.absolute()


def resolved_image_path(stored_path: Path, db_path: Path) -> Path:
    if stored_path.is_absolute():
        return stored_path
    return Path(os.path.normpath(os.path.join(db_path, stored_path)))


def store_preview(db: DBHandler, image_id: int, image, image_path: Path):
    scaled = image.scaledToHeight(PREVIEW_HEIGHT)
    ba = QtCore.QByteArray()
    buff = QtCore.QBuffer(ba)
    buff.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    ok = scaled.save(buff, "JPG")
    if ok:
        db.db_store_blob(image_id, ba.data(), image.width(), image.height())
    else:
        db.db_store_size(image_id, image.width(), image.height())
        logger.warning("Corrupt image present. Scaling for preview not possible: %s", image_path)


def store_image_regions(
    db: DBHandler,
    image_id: int,
    image_path: Path,
    img_width: int,
    img_height: int,
    user: str,
    metadata_tool: str,
    metadata_tool_path,
    metadata_tags: Mapping[str, str] | None = None,
):
    try:
        metadata = read_image_region_metadata(image_path.as_posix(), metadata_tool_path, metadata_tool)
        db.db_store_image_metadata(image_id, standard_exif_json(metadata))
        original_regions = copy.deepcopy(metadata.as_diagnostic_dict().get("imageRegion", []))
    except (FileNotFoundError, OSError) as err:
        logger.warning("Reading Image Region metadata skipped for %s: %s", image_path, err)
        db.db_store_image_metadata(image_id, {})
        original_regions = []
    except Exception as err:
        logger.exception("Reading Image Region metadata failed for %s: %s", image_path, err)
        db.db_store_image_metadata(image_id, {})
        original_regions = []

    db.db_store_original_image_region(image_id, orig_image_region=original_regions)
    if not original_regions:
        return

    for original_region in original_regions:
        if not original_region:
            continue
        try:
            object_type, data, region_user = parse_img_region(original_region, img_width, img_height, metadata_tags)
        except Exception:
            logger.exception("Could not parse Image Region metadata for: %s", image_path)
            continue

        db.db_store_object_imgregion(
            image_id,
            object_type,
            data,
            user=region_user or user,
            orig_img_region=original_region,
        )
