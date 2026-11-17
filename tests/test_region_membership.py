import gc
import json
import tempfile
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

from graphis.app.imgregion.region_editor import RegionEditorWidget
from graphis.db.db_handler import DBHandler
from graphis.interface.imgregion_adapter import boundary_from_pixel_coordinates
from graphis.interface.region_membership import (
    export_region_memberships,
    normalize_region_membership,
    parent_object_map,
)
from graphis.main import MainWindow


class MembershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_numeric_region_identifier_is_not_a_database_object_id(self):
        regions = [{"rId": "lead"}, {"rId": "12"}, {"rId": "child", "rMemberOf": "12"}]
        self.assertEqual(parent_object_map(regions, [12, 20, 30]), {"30": "20"})
        editor = RegionEditorWidget()
        editor.load_graphis_objects([
            {"id": object_id, "data": json.dumps(region)}
            for object_id, region in zip([12, 20, 30], regions, strict=True)
        ])
        self.assertEqual(editor.nodes_by_id["30"].parent_id, "20")

    def test_legacy_parent_is_removed_not_migrated(self):
        original = {"rId": "child", "rParent": "12", "RParent": "lead", "name": "Keep"}
        normalized = normalize_region_membership(original)
        self.assertEqual(normalized, {"rId": "child", "name": "Keep"})
        self.assertIn("rParent", original)
        self.assertEqual(parent_object_map([{"rId": "lead"}, original], [12, 30]), {})

    def test_unresolved_self_and_cyclic_links_do_not_remove_regions(self):
        regions = [
            {"rId": "a", "rMemberOf": "b"}, {"rId": "b", "rMemberOf": "a"},
            {"rId": "c", "rMemberOf": "missing"}, {"rId": "d", "rMemberOf": "d"},
        ]
        with self.assertLogs("graphis.interface.region_membership", level="WARNING"):
            result = parent_object_map(regions, range(4))
        self.assertEqual(result, {})
        with self.assertRaisesRegex(ValueError, "cycle"):
            export_region_memberships(regions)
        self.assertTrue(all("rMemberOf" in region for region in regions))

    def test_unresolved_membership_is_preserved_with_library_warning(self):
        region = {"rId": "child", "rMemberOf": "missing"}
        with self.assertLogs("graphis.interface.region_membership", level="WARNING") as messages:
            self.assertEqual(export_region_memberships([region]), [region])
        self.assertIn("UNRESOLVED_REGION_MEMBER_OF", messages.output[0])

    def test_native_aliases_and_type_validation_are_used(self):
        for key in ("rMemberOf", "RMemberOf", "Iptc4xmpExt:rMemberOf", "ImageRegionMemberOf"):
            with self.subTest(key=key):
                normalized = normalize_region_membership({key: "lead", "unrelated": "keep"})
                self.assertEqual(normalized, {"rMemberOf": "lead", "unrelated": "keep"})
        for value in (42, True, None, ["lead"], {}):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "single string"):
                export_region_memberships([{"rId": "child", "rMemberOf": value}])

    def test_deleting_a_lead_region_clears_member_links_in_one_undo_step(self):
        with tempfile.TemporaryDirectory() as directory:
            db = DBHandler()
            db.db_create(Path(directory) / "test.sqlite", "test")
            try:
                image_id = db.db_store_image(Path(directory) / "image.jpg")

                def store(identifier, member_of=None, x=10):
                    data = {"rId": identifier, "regionBoundary": boundary_from_pixel_coordinates("point", [x, 10])}
                    if member_of:
                        data["rMemberOf"] = member_of
                    return db.db_store_object(image_id, "point", data)

                lead_id = store("lead")
                member_id = store("member", "lead", 20)
                other_id = store("other", "keep", 30)
                store("keep", x=40)

                db.db_delete_geometry(lead_id)

                self.assertIsNone(db.db_load_object(lead_id))
                self.assertNotIn("rMemberOf", json.loads(db.db_load_object(member_id)["data"]))
                self.assertEqual(json.loads(db.db_load_object(other_id)["data"])["rMemberOf"], "keep")

                db.undo(image_id)
                self.assertIsNotNone(db.db_load_object(lead_id))
                self.assertEqual(json.loads(db.db_load_object(member_id)["data"])["rMemberOf"], "lead")
                db.redo(image_id)
                self.assertIsNone(db.db_load_object(lead_id))
                self.assertNotIn("rMemberOf", json.loads(db.db_load_object(member_id)["data"]))
            finally:
                db.db_close()
                gc.collect()

    def test_assignment_and_rename_update_links_and_undo_together(self):
        with tempfile.TemporaryDirectory() as directory:
            db = DBHandler()
            db.db_create(Path(directory) / "test.sqlite", "test")
            try:
                image_id = db.db_store_image(Path(directory) / "image.jpg")
                parent_data = {"rId": "lead", "regionBoundary": boundary_from_pixel_coordinates("point", [10, 10])}
                parent_id = db.db_store_object(image_id, "point", parent_data)
                child_id = db.db_store_object(image_id, "point", {
                    "rId": "child", "regionBoundary": boundary_from_pixel_coordinates("point", [20, 20])
                })

                class Harness:
                    _assign_region_parent = MainWindow._assign_region_parent
                    _assign_region_members = MainWindow._assign_region_members
                    _region_parent_object_map = MainWindow._region_parent_object_map
                    _regions_of = MainWindow._regions_of
                    _would_create_parent_cycle = MainWindow._would_create_parent_cycle

                harness = Harness()
                harness.db, harness.image_loading_image_id_db = db, image_id
                harness._assign_region_parent([child_id], parent_id, "Assign membership")
                self.assertEqual(json.loads(db.db_load_object(child_id)["data"])["rMemberOf"], "lead")
                db.update_object(parent_id, data={**parent_data, "rId": "renamed"})
                self.assertEqual(json.loads(db.db_load_object(child_id)["data"])["rMemberOf"], "renamed")
                db.undo(image_id)
                self.assertEqual(json.loads(db.db_load_object(parent_id)["data"])["rId"], "lead")
                self.assertEqual(json.loads(db.db_load_object(child_id)["data"])["rMemberOf"], "lead")
                db.redo(image_id)
                self.assertEqual(json.loads(db.db_load_object(child_id)["data"])["rMemberOf"], "renamed")
                before = db.db_load_objects_image(image_id)
                for invalid in ("", "child"):
                    with self.assertRaises(ValueError):
                        db.update_object(parent_id, data={**parent_data, "rId": invalid})
                    self.assertEqual(db.db_load_objects_image(image_id), before)
            finally:
                db.db_close()
                gc.collect()
