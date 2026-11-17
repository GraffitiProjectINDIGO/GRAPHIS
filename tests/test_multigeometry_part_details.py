"""Multiboundary Part Details stay coupled with their parts through combine, remove, and detach."""

import gc
import json
import tempfile
import unittest
from pathlib import Path

from iptc_iris import MultiboundaryPart
from PySide6.QtWidgets import QApplication

from graphis.db.db_handler import DBHandler
from graphis.interface.imgregion_adapter import (
    TAG_DESCRIBER,
    apply_part_details_to_region,
    boundary_from_pixel_coordinates,
    combine_multigeometry_regions,
    metadata_value,
    multigeometry_part,
    multigeometry_parts,
    put_metadata_value_to_dict_or_remove,
    remove_multigeometry_part,
    validate_region_data,
)
from graphis.main import MainWindow

WIDTH, HEIGHT = 200, 100


def square(x, y, size=10):
    return [[x, y], [x + size, y], [x + size, y + size], [x, y + size], [x, y]]


def named_region(identifier, shape, coordinates, name=None, description=None):
    region = {"rId": identifier, "regionBoundary": boundary_from_pixel_coordinates(shape, coordinates)}
    if name:
        region["name"] = {"x-default": name}
    if description:
        put_metadata_value_to_dict_or_remove(region, TAG_DESCRIBER, {"x-default": description})
    return region


def details(region):
    return region["regionBoundary"].get("rbMbPartDetails")


class PartDetailAdapterTests(unittest.TestCase):
    def test_combine_initialises_part_details_from_source_regions(self):
        first = named_region("left", "polygon", square(10, 10), "Left fragment", "Best part")
        second = named_region("right", "polygon", square(50, 10), "Right fragment")

        combined = combine_multigeometry_regions(first, [second], WIDTH, HEIGHT, "multipolygon")

        self.assertEqual(details(combined), [
            {"rbMbPdPartIndex": 0, "rbMbPdPartId": "left", "rbMbPdPartName": "Left fragment",
             "rbMbPdPartDescription": "Best part"},
            {"rbMbPdPartIndex": 1, "rbMbPdPartId": "right", "rbMbPdPartName": "Right fragment"},
        ])
        self.assertFalse(any(issue.severity == "error" for issue in validate_region_data(combined, WIDTH, HEIGHT)))

    def test_combining_into_a_multigeometry_keeps_existing_part_details(self):
        first = named_region("a", "point", [10, 10], "A")
        second = named_region("b", "point", [20, 20], "B")
        third = named_region("c", "point", [30, 30], "C")
        target = combine_multigeometry_regions(first, [second], WIDTH, HEIGHT, "multipoint")

        combined = combine_multigeometry_regions(target, [third], WIDTH, HEIGHT, "multipoint")

        self.assertEqual(
            [(part.part_id, part.part_name) for part in multigeometry_parts(combined["regionBoundary"])],
            [("a", "A"), ("b", "B"), ("c", "C")],
        )

    def test_removing_a_part_renumbers_part_index_and_keeps_details_with_their_parts(self):
        regions = [named_region(f"p{index}", "point", [10 + index * 20, 10], f"Point {index}") for index in range(3)]
        combined = combine_multigeometry_regions(regions[0], regions[1:], WIDTH, HEIGHT, "multipoint")

        remaining = remove_multigeometry_part(combined, WIDTH, HEIGHT, 0)

        self.assertEqual(json.loads(remaining["regionBoundary"]["rbCoordinates"]), [[30, 10], [50, 10]])
        self.assertEqual(details(remaining), [
            {"rbMbPdPartIndex": 0, "rbMbPdPartId": "p1", "rbMbPdPartName": "Point 1"},
            {"rbMbPdPartIndex": 1, "rbMbPdPartId": "p2", "rbMbPdPartName": "Point 2"},
        ])
        self.assertFalse(any(issue.severity == "error" for issue in validate_region_data(remaining, WIDTH, HEIGHT)))

    def test_removing_down_to_one_part_drops_part_details(self):
        combined = combine_multigeometry_regions(
            named_region("a", "point", [10, 10], "A"), [named_region("b", "point", [20, 20], "B")],
            WIDTH, HEIGHT, "multipoint",
        )

        remaining = remove_multigeometry_part(combined, WIDTH, HEIGHT, 0)

        self.assertEqual(remaining["regionBoundary"]["rbShape"], "point")
        self.assertIsNone(details(remaining))

    def test_removing_a_hole_keeps_part_details(self):
        holed = {"rId": "a", "regionBoundary": {
            "rbShape": "polygon", "rbUnit": "pixel", "rbCoordinates": json.dumps([square(10, 10, 40), square(20, 20)]),
        }, "name": {"x-default": "Holed"}}
        combined = combine_multigeometry_regions(
            holed, [named_region("b", "polygon", square(100, 10), "B")], WIDTH, HEIGHT, "multipolygon"
        )

        remaining = remove_multigeometry_part(combined, WIDTH, HEIGHT, 0, ring_index=1)

        self.assertEqual(len(json.loads(remaining["regionBoundary"]["rbCoordinates"])[0]), 1)
        self.assertEqual(details(remaining), details(combined))

    def test_apply_part_details_restores_identity_without_duplicate_ids(self):
        part = MultiboundaryPart([10, 10], part_id="left", part_name="Left", part_description="Best part")

        restored = apply_part_details_to_region({"rId": "new"}, part, used_region_ids={"other"})
        duplicate = apply_part_details_to_region({"rId": "new"}, part, used_region_ids={"left"})

        self.assertEqual(restored["rId"], "left")
        self.assertEqual(restored["name"], {"x-default": "Left"})
        self.assertEqual(metadata_value(restored, TAG_DESCRIBER), {"x-default": "Best part"})
        self.assertEqual(duplicate["rId"], "new")


class Harness:
    _create_multigeometry_container = MainWindow._create_multigeometry_container
    _absorb_multigeometry_sources = MainWindow._absorb_multigeometry_sources
    _region_parent_object_map = MainWindow._region_parent_object_map
    _regions_of = MainWindow._regions_of
    _assign_region_parent = MainWindow._assign_region_parent
    _assign_region_members = MainWindow._assign_region_members
    _would_create_parent_cycle = MainWindow._would_create_parent_cycle
    detach_geometry_part = MainWindow.detach_geometry_part

    def _new_multigeometry_region_data(self, shape):
        return {"regionBoundary": {"rbShape": shape, "rbUnit": "pixel", "rbCoordinates": "[]"}}

    def _db_ready_for(self, action):
        return True

    def _guard_unsaved_region_metadata_changes(self, action):
        return True

    def _refresh_after_region_grouping(self, object_id):
        self.selected_id = object_id


class CombineDetachWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "test.sqlite"
        self.db = DBHandler()
        self.db.db_create(self.db_path, "test")
        self.image_id = self.db.db_store_image(Path(self.temp.name) / "image.jpg")
        self.db.db_store_size(self.image_id, WIDTH, HEIGHT)
        self.harness = Harness()
        self.harness.db = self.db
        self.harness.image_loading_image_id_db = self.image_id

    def tearDown(self):
        self.db.db_close()
        gc.collect()
        self.temp.cleanup()

    def test_detach_after_reopening_restores_combined_region_identity(self):
        left = named_region("left", "point", [10, 10], "Left", "Left description")
        right = named_region("right", "point", [50, 20], "Right", "Right description")
        ids = [self.db.db_store_object(self.image_id, "point", region) for region in (left, right)]
        container_id = self.harness._create_multigeometry_container("multipoint", ids)

        # Undo history does not survive closing the database; the part details do.
        self.db.db_close()
        self.db = DBHandler()
        self.db.db_load(self.db_path, "test")
        self.harness.db = self.db
        self.assertFalse(self.db.can_undo(self.image_id))

        self.harness.detach_geometry_part(container_id, 1)

        detached = json.loads(self.db.db_load_object(self.harness.selected_id)["data"])
        remaining = json.loads(self.db.db_load_object(container_id)["data"])
        self.assertEqual(detached["rId"], "right")
        self.assertEqual(detached["name"], {"x-default": "Right"})
        self.assertEqual(metadata_value(detached, TAG_DESCRIBER), {"x-default": "Right description"})
        self.assertEqual(remaining["regionBoundary"]["rbShape"], "point")
        self.assertNotIn("rbMbPartDetails", remaining["regionBoundary"])

    def test_detaching_the_part_that_shares_the_container_id_gets_a_new_id(self):
        left = named_region("left", "point", [10, 10], "Left")
        right = named_region("right", "point", [50, 20], "Right")
        ids = [self.db.db_store_object(self.image_id, "point", region) for region in (left, right)]
        container_id = self.harness._create_multigeometry_container("multipoint", ids)
        container = json.loads(self.db.db_load_object(container_id)["data"])
        self.assertEqual(container["rId"], multigeometry_part(container, 0).part_id)

        self.harness.detach_geometry_part(container_id, 0)

        detached = json.loads(self.db.db_load_object(self.harness.selected_id)["data"])
        self.assertNotEqual(detached["rId"], "left")
        self.assertEqual(detached["name"], {"x-default": "Left"})

    def test_combine_and_detach_are_each_one_undo_step(self):
        left = named_region("left", "point", [10, 10], "Left")
        right = named_region("right", "point", [50, 20], "Right")
        ids = [self.db.db_store_object(self.image_id, "point", region) for region in (left, right)]
        container_id = self.harness._create_multigeometry_container("multipoint", ids)
        combined = json.loads(self.db.db_load_object(container_id)["data"])

        self.harness.detach_geometry_part(container_id, 1)
        self.db.undo(self.image_id)
        self.assertEqual(json.loads(self.db.db_load_object(container_id)["data"]), combined)

        self.db.undo(self.image_id)
        self.assertEqual(json.loads(self.db.db_load_object(ids[0])["data"]), left)
        self.assertEqual(json.loads(self.db.db_load_object(ids[1])["data"]), right)


if __name__ == "__main__":
    unittest.main()
