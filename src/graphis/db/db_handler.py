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
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from sqlite3 import DatabaseError, IntegrityError, dbapi2

from graphis.db.createDb import create, init
from graphis.db.undo_redo import (
    ImageSnapshot,
    ObjectDeleteCommand,
    ObjectInsertCommand,
    ObjectSnapshot,
    ObjectUpdateCommand,
    UndoRedoManager,
)
from graphis.interface.imgregion_adapter import (
    log_image_object_validation_issues,
    log_validation_issues,
    update_region_boundary_from_pixels,
    validate_region_data,
)
from graphis.interface.region_membership import (
    PARENT_KEYS,
    normalize_region_membership,
    parent_map_from_rows,
    region_identifier,
)

logger = logging.getLogger(__name__)


def db_json_dumps(value):
    return json.dumps(value, ensure_ascii=True)


@dataclass
class DBBusyState:
    active: bool = False
    action: str = ""
    detail: str = ""
    started_at: datetime | None = None


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class DBHandler:
    def __init__(self):
        self.con = dbapi2.Connection("")

        self.db_path: Path | None = None
        self.db_user = ""
        self.db_is_set = False
        self.busy = DBBusyState()
        self.undo_redo = UndoRedoManager()

    @property
    def is_busy(self):
        return self.busy.active

    def lock(self, action: str, detail: str = ""):
        self.busy = DBBusyState(
            active=True,
            action=action,
            detail=detail,
            started_at=datetime.now(),
        )
        self.undo_redo.notify_changed()

    def unlock(self):
        self.busy = DBBusyState()
        self.undo_redo.notify_changed()

    def blocked_message(self, requested_action: str, require_database: bool = True):
        if self.busy.active:
            blocking_action = self.busy.action or "another database action"
            detail = f" ({self.busy.detail})" if self.busy.detail else ""
            return f"Cannot {requested_action}: database is busy with {blocking_action}{detail}."

        if require_database and not self.db_is_set:
            return f"Cannot {requested_action}: no database is active."

        return ""

    def db_close(self):
        self.db_is_set = False
        self.undo_redo.clear()
        self.unlock()
        self.con.close()

    def db_create(self, db_path: Path, user):
        try:
            create(db_path.as_posix())
            self.con = dbapi2.connect(db_path.as_posix())
            init(self.con)
            self.con.row_factory = dict_factory
            self.db_path = db_path
            self.db_user = user
            self.db_is_set = True
            self.undo_redo.clear()
            return True
        except DatabaseError:
            logger.exception("Database can not be created, probably because it is locked: %s", db_path)
            return False

    def db_load(self, db_path: Path, user):
        self.con = dbapi2.connect(db_path.as_posix())
        init(self.con)
        self.con.row_factory = dict_factory
        self.db_path = db_path
        self.db_user = user
        self.db_is_set = True
        self.undo_redo.clear()

    def add_undo_listener(self, listener):
        self.undo_redo.add_listener(listener)

    def can_undo(self, image_id: int | None = None):
        return self.undo_redo.can_undo(image_id)

    def can_redo(self, image_id: int | None = None):
        return self.undo_redo.can_redo(image_id)

    def undo_label(self, image_id: int | None = None):
        return self.undo_redo.undo_label(image_id)

    def redo_label(self, image_id: int | None = None):
        return self.undo_redo.redo_label(image_id)

    def begin_undo_group(self, label: str):
        self.undo_redo.begin_group(label)

    def end_undo_group(self):
        self.undo_redo.end_group()

    def undo(self, image_id: int | None = None):
        return self.undo_redo.undo(self.con, image_id)

    def redo(self, image_id: int | None = None):
        return self.undo_redo.redo(self.con, image_id)

    def _load_object_snapshot(self, object_id: int):
        row = self.con.execute(
            """
            SELECT id, image, user, object_type, orig_img_region, changed, data
            FROM objects
            WHERE id = :id
            """,
            {"id": object_id},
        ).fetchone()
        return ObjectSnapshot.from_row(row)

    def _load_image_snapshot(self, image_id: int):
        row = self.con.execute(
            """
            SELECT id, deleted_orig_tag
            FROM images
            WHERE id = :id
            """,
            {"id": image_id},
        ).fetchone()
        return ImageSnapshot.from_row(row)

    def db_check_abs_path(self):
        abs_sqlite = self.db_path
        image_list = self.db_load_images_list()

        for x in image_list:
            # print(abs_sqlite)
            image = Path(x["path"])
            if not image.exists():
                logger.info("Try to relocate image path to relative path: %s", image)
                try:
                    rel = os.path.relpath(image, abs_sqlite)
                    new_path = os.path.normpath(os.path.join(abs_sqlite, rel))
                    if Path(new_path).exists():
                        self.db_update_path(image.as_posix(), new_path)
                except Exception:
                    logger.exception("Failed to relocate image path: %s", image)
                    return

    def db_update_path(self, path1, path2):
        query = r"""UPDATE
                        images
                    SET
                        path = REPLACE(path,:path_to_replace,:path_replace)"""
        self.con.execute(query, {"path_to_replace": path1, "path_replace": path2})
        self.con.commit()

    def db_store_image(self, image_path: Path):
        query = r"""Insert into images 
        (path,user,name)
        Values
        (:path,:user,:name)"""
        try:
            data = self.con.execute(query, {"path": image_path.as_posix(), "user": self.db_user, "name": image_path.name})
            self.con.commit()
        except IntegrityError:
            return -1
        return data.lastrowid

    def db_store_size(self, image_id, width, height):
        query = r"""Update images
        SET width = :width,
            height = :height
        where id=:id"""
        self.con.execute(query, {"id": image_id, "width": width, "height": height})
        self.con.commit()

    def db_store_blob(self, image_id, blob, width, height):
        query = r"""Update images
        SET preview = :blob,
            width = :width,
            height = :height
        where id=:id"""
        self.con.execute(query, {"blob": blob, "id": image_id, "width": width, "height": height})
        self.con.commit()

    def db_deleted_orig_tag(self, image_id):
        query = r"""Update images
        SET deleted_orig_tag = 1
        where id=:id"""
        self.con.execute(query, {"id": image_id})
        self.con.commit()

    def db_store_original_image_region(self, image_id, orig_image_region=None):
        if orig_image_region is None:
            orig_image_region = []
        query = r"""Update images
                SET orig_exif_image_region = :orig_exif_image_region
                where id=:id"""
        self.con.execute(query, {"id": image_id, "orig_exif_image_region": db_json_dumps(orig_image_region)})
        self.con.commit()

    def db_store_image_metadata(self, image_id, image_metadata=None):
        if image_metadata is None:
            image_metadata = {}
        query = r"""Update images
                SET image_metadata = :image_metadata
                where id=:id"""
        self.con.execute(query, {"id": image_id, "image_metadata": db_json_dumps(image_metadata)})
        self.con.commit()

    def db_load_image_record(self, image_id: int):
        query = r"""SELECT * FROM images WHERE id = :id"""
        return self.con.execute(query, {"id": image_id}).fetchone()

    def db_load_image_metadata(self, image_id: int):
        image = self.db_load_image_record(image_id)
        if not image or not image["image_metadata"]:
            return {}
        try:
            return json.loads(image["image_metadata"])
        except (TypeError, json.JSONDecodeError):
            return {}

    def db_load_original_image_region(self, image_id: int):
        image = self.db_load_image_record(image_id)
        if not image:
            return None

        if image["orig_exif_image_region"] is not None:
            return json.loads(image["orig_exif_image_region"])

        original_regions = []
        for obj in self.db_load_objects_image(image_id):
            if obj["orig_img_region"]:
                original_regions.append(json.loads(obj["orig_img_region"]))

        return original_regions if original_regions else None

    def _validation_rows_for_image(
        self,
        image_id: int,
        *,
        replacement_obj_id=None,
        replacement_data: dict | None = None,
        pending_data: dict | None = None,
    ):
        rows = [dict(obj) for obj in self.db_load_objects_image(image_id)]
        if replacement_data is not None:
            replacement_json = db_json_dumps(replacement_data)
            replaced = False
            for row in rows:
                if row.get("id") == replacement_obj_id:
                    row["data"] = replacement_json
                    replaced = True
                    break
            if not replaced:
                rows.append({"id": replacement_obj_id or "__pending__", "data": replacement_json})
        elif pending_data is not None:
            rows.append({"id": "__pending__", "data": db_json_dumps(pending_data)})
        return rows

    def _log_image_validation(
        self,
        image_id: int,
        context: str,
        *,
        replacement_obj_id=None,
        replacement_data: dict | None = None,
        pending_data: dict | None = None,
        only_object_id=None,
        rows=None,
    ):
        image = self.db_load_image_record(image_id)
        if not image:
            return []
        if rows is None:
            rows = self._validation_rows_for_image(
                image_id,
                replacement_obj_id=replacement_obj_id,
                replacement_data=replacement_data,
                pending_data=pending_data,
            )
        return log_image_object_validation_issues(
            rows,
            img_width=image["width"],
            img_height=image["height"],
            context=context,
            only_object_id=only_object_id,
        )

    def db_replace_image_objects(self, image_id: int, objects: list[dict]):
        validation_rows = [
            {"id": f"pending-{index}", "data": db_json_dumps(obj["data"])} for index, obj in enumerate(objects)
        ]
        self._log_image_validation(image_id, f"Image {image_id}", rows=validation_rows)

        with self.con:
            self.con.execute(r"""DELETE FROM objects WHERE image = :id """, {"id": image_id})
            self.con.execute(
                r"""Update images
                    SET deleted_orig_tag = 1
                    where id=:id""",
                {"id": image_id},
            )

            for obj in objects:
                self.con.execute(
                    r"""Insert into objects
                    (image,user,object_type,data,orig_img_region,changed)
                    Values
                    (:image,:user,:obj,:data,:orig_img_region,1)""",
                    {
                        "image": image_id,
                        "user": obj.get("user", self.db_user),
                        "obj": obj["object_type"],
                        "data": db_json_dumps(obj["data"]),
                        "orig_img_region": db_json_dumps(obj.get("orig_img_region")),
                    },
                )

        self.undo_redo.forget_image(image_id)

    def db_delete_image(self, image_id: int):
        with self.con:
            self.con.execute(r"""DELETE FROM objects WHERE image = :id """, {"id": image_id})
            self.con.execute(r"""DELETE FROM images WHERE id = :id """, {"id": image_id})
        self.undo_redo.forget_image(image_id)

    def db_load_images_list(self):
        query = r""" select images.*, Count(objects.image) as s_count from images
                left join objects on images.id = objects.image
                group by images.id
                order by images.id"""
        data = self.con.execute(query).fetchall()
        return data

    def db_delete_geometry(self, object_id: int):
        """Delete a region and clear rMemberOf references to it in the same undo operation.

        IPTC requires rMemberOf to reference an existing region, so members of
        the deleted region become independent regions.
        """
        row = self.db_load_object(object_id)
        members = self._region_members(row) if row is not None else []
        if not members:
            return self._delete_geometry(object_id)
        self.begin_undo_group("Delete image region and clear membership references")
        try:
            for member in members:
                member_data = json.loads(member["data"])
                for key in PARENT_KEYS:
                    member_data.pop(key, None)
                self._update_object(member["id"], data=member_data, log_validation=False)
            self._delete_geometry(object_id)
        finally:
            self.end_undo_group()

    def _region_members(self, row) -> list:
        """Rows whose rMemberOf references this region, unless another region shares its rId."""
        identifier = region_identifier(json.loads(row["data"]))
        if not identifier:
            return []
        rows = self.db_load_objects_image(row["image"])
        if any(
            other["id"] != row["id"] and region_identifier(json.loads(other["data"])) == identifier for other in rows
        ):
            return []
        parents = parent_map_from_rows(rows)
        return [other for other in rows if parents.get(other["id"]) == row["id"]]

    def _delete_geometry(self, object_id: int):
        # delete geometry but check if it is an original one to know if image changes

        data = self.db_load_object(object_id)
        object_before = self._load_object_snapshot(object_id)
        image_before = self._load_image_snapshot(data["image"]) if data else None
        if data["orig_img_region"] is not None:
            self.db_deleted_orig_tag(data["image"])

        self.con.execute(r"""DELETE FROM objects WHERE id = :id """, {"id": object_id})
        self.con.commit()
        image_after = self._load_image_snapshot(data["image"]) if data else None
        if object_before is not None:
            object_type = object_before.values["object_type"]
            self.undo_redo.record(ObjectDeleteCommand(f"Delete {object_type}", object_before, image_before, image_after))

    def db_load_object(self, obj_id: int):
        query = r"""SELECT objects.*, images.width as img_width, images.height as img_height FROM objects
                    join
                    images
                    where
                    images.id = objects.image and objects.id =:id"""

        data = self.con.execute(query, {"id": obj_id}).fetchone()
        return data

    def db_store_object(self, image_id: int, obj: str, data: dict, user=""):
        data = normalize_region_membership(data)
        query = r"""Insert into objects 
        (image,user,object_type,data,changed)
        Values
        (:image,:user, :obj, :data, 1)"""
        if not user:
            user = self.db_user
        self._log_image_validation(image_id, f"Image {image_id}", pending_data=data, only_object_id="__pending__")
        data = self.con.execute(query, {"image": image_id, "user": user, "obj": obj, "data": db_json_dumps(data)})
        self.con.commit()
        object_id = data.lastrowid
        snapshot = self._load_object_snapshot(object_id)
        if snapshot is not None:
            self.undo_redo.record(ObjectInsertCommand(f"Create {obj}", snapshot))
        return object_id

    def db_store_object_imgregion(self, image_id: int, obj: str, data: dict, user="", orig_img_region=None):
        query = r"""Insert into objects 
        (image,user,object_type,data, orig_img_region)
        Values
        (:image,:user, :obj, :data, :orig_img_region)"""
        if not user:
            user = self.db_user
        self._log_image_validation(image_id, f"Image {image_id}", pending_data=data)
        data = self.con.execute(
            query,
            {
                "image": image_id,
                "user": user,
                "obj": obj,
                "data": db_json_dumps(data),
                "orig_img_region": db_json_dumps(orig_img_region),
            },
        )
        self.con.commit()
        return data.lastrowid

    def update_object(
        self, obj_id, coordinates: list = None, data: dict = None, log_validation: bool = True,
        action_label: str | None = None, object_type: str | None = None,
    ):
        """Keep references to renamed Region Identifiers in the same undo operation."""
        if data is not None:
            data = normalize_region_membership(data)
        row = self.db_load_object(obj_id) if data is not None else None
        children = []
        if row is not None and region_identifier(json.loads(row["data"])) != region_identifier(data):
            rows = self.db_load_objects_image(row["image"])
            parents = parent_map_from_rows(rows)
            children = [child for child in rows if parents.get(child["id"]) == obj_id]
            if children:
                new_identifier = region_identifier(data)
                if not new_identifier:
                    raise ValueError("The Region Identifier cannot be empty while other regions are members of it.")
                if any(
                    child["id"] != obj_id and region_identifier(json.loads(child["data"])) == new_identifier
                    for child in rows
                ):
                    raise ValueError("The Region Identifier is already used by another region in this image.")
        if not children:
            return self._update_object(obj_id, coordinates, data, log_validation, action_label, object_type)
        self.begin_undo_group(action_label or "Rename Region Identifier and update membership references")
        try:
            self._update_object(obj_id, coordinates, data, log_validation, action_label, object_type)
            for child in children:
                child_data = json.loads(child["data"])
                for key in PARENT_KEYS:
                    child_data.pop(key, None)
                child_data["rMemberOf"] = region_identifier(data)
                self._update_object(child["id"], data=child_data, log_validation=False, action_label=action_label)
        finally:
            self.end_undo_group()

    def _update_object(
        self,
        obj_id,
        coordinates: list = None,
        data: dict = None,
        log_validation: bool = True,
        action_label: str | None = None,
        object_type: str | None = None,
    ):
        object_before = self._load_object_snapshot(obj_id)
        obj = self.db_load_object(obj_id)
        geometry_update = coordinates is not None

        if geometry_update and data is None:
            if obj:
                data = json.loads(obj["data"])
                update_object_type = object_type or obj["object_type"]
                data = update_region_boundary_from_pixels(
                    data,
                    obj["img_width"],
                    obj["img_height"],
                    update_object_type,
                    coordinates,
                )
        if data is None:
            return

        if obj and log_validation:
            if geometry_update:
                issues = validate_region_data(data, img_width=obj["img_width"], img_height=obj["img_height"])
                boundary_issues = [issue for issue in issues if ".regionBoundary" in issue.path]
                log_validation_issues(boundary_issues, context=f"Image {obj['image']} object {obj_id}")
            else:
                self._log_image_validation(
                    obj["image"],
                    f"Image {obj['image']}",
                    replacement_obj_id=obj_id,
                    replacement_data=data,
                    only_object_id=obj_id,
                )

        if object_type is None:
            query = r"""Update objects
            SET data = :data,
            changed = 1
            where id=:id"""
            self.con.execute(query, {"data": db_json_dumps(data), "id": obj_id})
        else:
            query = r"""Update objects
            SET data = :data,
            object_type = :object_type,
            changed = 1
            where id=:id"""
            self.con.execute(query, {"data": db_json_dumps(data), "object_type": object_type, "id": obj_id})
        self.con.commit()
        object_after = self._load_object_snapshot(obj_id)
        object_type = object_after.values["object_type"] if object_after is not None else "region"
        label = action_label or (
            f"Change {object_type} geometry" if coordinates is not None else f"Update {object_type} metadata"
        )
        self.undo_redo.record(ObjectUpdateCommand(label, object_before, object_after))

    def db_load_image(self, image_id: int):
        query = r"""SELECT id, image,data as data,object_type as object_type FROM objects 
        Where image = :id """

        data = self.con.execute(query, {"id": image_id}).fetchall()
        return data

    def db_load_objects_all(self):
        query = r"""select images.path as imgpath, images.name as image_name,
                images.width as img_width, images.height as img_height, objects.*  from objects
                join images where images.id = objects.image order by images.id"""
        data = self.con.execute(query).fetchall()
        return data

    def db_load_objects_image(self, image_id: int):
        query = r"""select *  from objects where image = :id"""
        data = self.con.execute(query, {"id": image_id}).fetchall()
        return data
