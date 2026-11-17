import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from graphis.interface.imgregion_adapter import boundary_from_pixel_coordinates
from graphis.interface.meta_exif import (
    parse_img_region,
    read_image_region_metadata,
    write_graphis_image_regions,
)

EXIFTOOL = os.environ.get("GRAPHIS_TEST_EXIFTOOL") or shutil.which("exiftool")
EXIV2 = os.environ.get("GRAPHIS_TEST_EXIV2") or shutil.which("exiv2")


class MetadataWriteTests(unittest.TestCase):
    def test_exiftool_warnings_are_reported_as_failures(self):
        result = subprocess.CompletedProcess([], 0, "", "Warning: field is not writable\n    1 image files updated")
        regions = [{"rId": "a", "regionBoundary": boundary_from_pixel_coordinates("point", [10, 10])}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.jpg"
            Image.new("RGB", (200, 100)).save(path)
            with patch("iptc_iris.io.subprocess.run", return_value=result):
                with self.assertRaisesRegex(RuntimeError, "field is not writable"):
                    write_graphis_image_regions(path, regions, executable="exiftool")

    def test_parent_references_are_normalized_on_import(self):
        _shape, region, _user = parse_img_region(
            {"RMemberOf": "lead", "regionBoundary": boundary_from_pixel_coordinates("point", [10, 10])}, 200, 100
        )
        self.assertEqual(region["rMemberOf"], "lead")
        self.assertNotIn("RMemberOf", region)

    def test_legacy_parent_is_not_imported_as_membership(self):
        _shape, region, _user = parse_img_region(
            {"RParent": "lead", "regionBoundary": boundary_from_pixel_coordinates("point", [10, 10])}, 200, 100
        )
        self.assertNotIn("rParent", region)
        self.assertNotIn("RParent", region)
        self.assertNotIn("rMemberOf", region)

    @unittest.skipUnless(EXIFTOOL and EXIV2, "Set GRAPHIS_TEST_EXIFTOOL and GRAPHIS_TEST_EXIV2")
    def test_membership_roundtrip_with_exiv2_and_no_legacy_parent(self):
        regions = [
            {"rId": "lead", "regionBoundary": boundary_from_pixel_coordinates("point", [10, 10])},
            {"rId": "member", "rMemberOf": "lead", "regionBoundary": boundary_from_pixel_coordinates("point", [30, 30])},
            {"rId": "old", "rParent": "lead", "regionBoundary": boundary_from_pixel_coordinates("point", [50, 50])},
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.jpg"
            Image.new("RGB", (200, 100)).save(path)
            write_graphis_image_regions(path, regions, executable=EXIV2, tool="exiv2")
            imported = read_image_region_metadata(path, EXIFTOOL).image_regions.as_diagnostic_dict_list()
            parsed = [parse_img_region(region, 200, 100)[1] for region in imported]
            self.assertEqual(parsed[1]["rMemberOf"], "lead")
            self.assertNotIn("rMemberOf", parsed[2])
            self.assertTrue(all("rParent" not in region and "RParent" not in region for region in parsed))


@unittest.skipUnless(EXIFTOOL, "Set GRAPHIS_TEST_EXIFTOOL or put ExifTool on PATH")
class ExifToolRoundtripTests(unittest.TestCase):
    def test_new_boundaries_and_part_details_survive_real_write_and_import(self):
        outer = [[10, 10], [80, 10], [80, 80], [10, 80], [10, 10]]
        inner = [[20, 20], [30, 20], [30, 30], [20, 30], [20, 20]]
        regions = []
        for index, (shape, coordinates) in enumerate((
            ("polygon", [outer, inner]),
            ("multipolygon", [[outer, inner], [[[100, 10], [130, 10], [130, 40], [100, 10]]]]),
            ("point", [10, 10]),
            ("multipoint", [[10, 10], [20, 20]]),
            ("linestring", [[10, 10], [20, 20]]),
            ("multilinestring", [[[10, 10], [20, 20]], [[30, 30], [40, 40]]]),
            ("rectangle", [[10, 10], [20, 20]]),
            ("circle", [40, 40, 10]),
        )):
            boundary = (
                {"rbShape": "polygon", "rbUnit": "pixel", "rbCoordinates": json.dumps(coordinates)}
                if shape == "polygon" else boundary_from_pixel_coordinates(shape, coordinates)
            )
            regions.append({"rId": f"region-{index}", "name": {"x-default": f"Name {index}"},
                            "regionBoundary": boundary})
        regions[1]["regionBoundary"]["rbMbPartDetails"] = [
            {"rbMbPdPartId": "1", "rbMbPdPartName": "Area", "rbMbPdPartDescription": "First area"}
        ]
        regions[2]["rMemberOf"] = "region-1"
        with tempfile.TemporaryDirectory(prefix="graphis-roundtrip-") as directory:
            path = Path(directory) / "test.jpg"
            exif = Image.Exif()
            exif[270] = "Existing image description"
            Image.new("RGB", (200, 100)).save(path, exif=exif)
            write_graphis_image_regions(path, regions, executable=EXIFTOOL, keep_original=True)
            self.assertTrue(path.with_name("test.jpg_original").exists())
            imported = read_image_region_metadata(path, EXIFTOOL).image_regions.as_diagnostic_dict_list()
            self.assertEqual(len(imported), len(regions))
            for before, after in zip(regions, imported, strict=True):
                with self.subTest(shape=before["regionBoundary"]["rbShape"]):
                    _shape, parsed, _user = parse_img_region(after, 200, 100)
                    expected_boundary = dict(before["regionBoundary"])
                    actual_boundary = dict(parsed["regionBoundary"])
                    for boundary in (expected_boundary, actual_boundary):
                        if "rbCoordinates" in boundary:
                            boundary["rbCoordinates"] = json.loads(boundary["rbCoordinates"])
                    self.assertEqual(actual_boundary, expected_boundary)
                    self.assertEqual(parsed["rId"], before["rId"])
                    self.assertEqual(parsed["name"], before["name"])
                    if "rMemberOf" in before:
                        self.assertEqual(parsed["rMemberOf"], before["rMemberOf"])
            with Image.open(path) as saved:
                self.assertEqual(saved.getexif()[270], "Existing image description")
            write_graphis_image_regions(path, [], executable=EXIFTOOL)
            self.assertEqual(read_image_region_metadata(path, EXIFTOOL).image_regions.as_diagnostic_dict_list(), [])


if __name__ == "__main__":
    unittest.main()
