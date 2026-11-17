import gc
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from graphis.db.db_handler import DBHandler
from graphis.interface import image_regions
from graphis.interface.image_regions import OpenImageRegions
from graphis.interface.imgregion_adapter import boundary_from_pixel_coordinates


def polygon(identifier, points, **extra):
    return {"rId": identifier, "regionBoundary": boundary_from_pixel_coordinates("polygon", points), **extra}


SQUARE = [[10, 10], [60, 10], [60, 60], [10, 60], [10, 10]]
BOW_TIE = [[10, 10], [60, 60], [60, 10], [10, 60], [10, 10]]


class OpenImageRegionsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db = DBHandler()
        self.db.db_create(Path(self.directory.name) / "test.sqlite", "test")
        self.image_id = self.db.db_store_image(Path(self.directory.name) / "image.jpg")
        self.db.db_store_size(self.image_id, 100, 100)
        self.lead_id = self.db.db_store_object(self.image_id, "polygon", polygon("lead", SQUARE))
        self.child_id = self.db.db_store_object(
            self.image_id, "polygon", polygon("child", [[20, 20], [40, 20], [40, 40], [20, 20]], rMemberOf="lead")
        )

    def tearDown(self):
        self.db.db_close()
        gc.collect()
        self.directory.cleanup()

    def test_validates_once_while_unchanged_and_again_after_a_change(self):
        regions = OpenImageRegions(self.db, self.image_id)
        real = image_regions.validate_image_object_result
        with patch.object(image_regions, "validate_image_object_result", side_effect=real) as validate:
            # Info hints (deprecated rbVertices) are not problems.
            self.assertEqual([issue for issue in regions.validation_issues if issue.severity != "info"], [])
            regions.issues_by_object()
            self.assertIsNotNone(regions.validation_result)
            self.assertEqual(validate.call_count, 1)

            data = json.loads(self.db.db_load_object(self.lead_id)["data"])
            bow_tie = polygon("lead", BOW_TIE)["regionBoundary"]
            self.db.update_object(self.lead_id, data={**data, "regionBoundary": bow_tie})
            codes = {issue.code for issue in regions.validation_issues}
            self.assertEqual(validate.call_count, 2)
            self.assertIn("SELF_INTERSECTING_POLYGON", codes)
            self.assertIn(str(self.lead_id), regions.issues_by_object())

    def test_only_changed_regions_are_parsed_again_for_drawing(self):
        regions = OpenImageRegions(self.db, self.image_id)
        real = image_regions.pixel_coordinates_from_region
        with patch.object(image_regions, "pixel_coordinates_from_region", side_effect=real) as parse:
            drawn = list(regions.drawable_regions())
            self.assertEqual([row["id"] for row, *_ in drawn], [self.lead_id, self.child_id])
            self.assertEqual(drawn[0][2], "polygon")
            self.assertEqual(drawn[0][3][0], [10, 10])
            list(regions.drawable_regions())
            self.assertEqual(parse.call_count, 2)

            data = json.loads(self.db.db_load_object(self.child_id)["data"])
            self.db.update_object(self.child_id, data={**data, "rId": "child-renamed"})
            list(regions.drawable_regions())
            self.assertEqual(parse.call_count, 3)

    def test_parent_links_and_undo_are_reflected(self):
        regions = OpenImageRegions(self.db, self.image_id)
        self.assertEqual(regions.parent_map(), {self.child_id: self.lead_id})
        data = json.loads(self.db.db_load_object(self.child_id)["data"])
        data.pop("rMemberOf")
        self.db.update_object(self.child_id, data=data)
        self.assertEqual(regions.parent_map(), {})
        self.db.undo(self.image_id)
        self.assertEqual(regions.parent_map(), {self.child_id: self.lead_id})

    def test_malformed_region_is_skipped_for_drawing_but_reported(self):
        broken = {"rId": "broken", "regionBoundary": {"rbShape": "polygon", "rbUnit": "pixel", "rbVertices": "x"}}
        broken_id = self.db.db_store_object(self.image_id, "polygon", broken)
        regions = OpenImageRegions(self.db, self.image_id)
        self.assertNotIn(broken_id, [row["id"] for row, *_ in regions.drawable_regions()])
        self.assertIn(str(broken_id), regions.issues_by_object())


if __name__ == "__main__":
    unittest.main()
