import gc
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import QPoint, QPointF
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QMenu

from graphis.app.graphic.digitizerscene import DIGITIZERScene
from graphis.app.imgregion.region_editor import RegionEditorWidget
from graphis.db.db_handler import DBHandler
from graphis.interface.imgregion_adapter import (
    boundary_from_pixel_coordinates,
    change_region_unit,
    detach_multigeometry_part,
    pixel_coordinates_from_region,
    validate_region_data,
)
from graphis.main import MainWindow


class DetachHarness:
    detach_geometry_part = MainWindow.detach_geometry_part
    detach_region_parent = MainWindow.detach_region_parent

    def _db_ready_for(self, action):
        return True

    def _guard_unsaved_region_metadata_changes(self, action):
        return True

    def _refresh_after_region_grouping(self, selected_id):
        self.selected_id = selected_id


class DetachGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = DBHandler()
        self.db.db_create(Path(self.temp.name) / "test.sqlite", "test")
        self.image_id = self.db.db_store_image(Path(self.temp.name) / "image.jpg")
        self.db.db_store_size(self.image_id, 200, 100)
        self.harness = DetachHarness()
        self.harness.db = self.db
        self.harness.image_loading_image_id_db = self.image_id

    def tearDown(self):
        self.db.db_close()
        gc.collect()
        self.temp.cleanup()

    def test_detach_each_multigeometry_type_and_units_preserves_coordinates(self):
        for shape, base_shape, parts in (
            ("multipoint", "point", [[10, 10], [60, 20]]),
            ("multilinestring", "linestring", [[[10, 10], [20, 20]], [[60, 10], [80, 20]]]),
            ("multipolygon", "polygon", [
                [[[10, 10], [40, 10], [40, 40], [10, 40], [10, 10]],
                 [[20, 20], [20, 30], [30, 30], [30, 20], [20, 20]]],
                [[[60, 10], [90, 10], [90, 40], [60, 40], [60, 10]]],
            ]),
        ):
            for unit in ("pixel", "relative"):
                with self.subTest(shape=shape, unit=unit):
                    original = {"rId": "source", "regionBoundary": boundary_from_pixel_coordinates(shape, parts)}
                    if unit == "relative":
                        original = change_region_unit(original, unit, 200, 100)
                    before = json.dumps(original)
                    remaining, boundary = detach_multigeometry_part(original, 200, 100, 0)
                    self.assertEqual(json.dumps(original), before)
                    self.assertEqual(boundary["rbShape"], base_shape)
                    self.assertEqual(boundary["rbUnit"], unit)
                    self.assertEqual(remaining["regionBoundary"]["rbShape"], base_shape)
                    actual = pixel_coordinates_from_region({"regionBoundary": boundary}, 200, 100)[1]
                    self.assertEqual(actual, parts[0])
                    for data in (remaining, {"regionBoundary": boundary}):
                        self.assertFalse([i for i in validate_region_data(data, 200, 100) if i.severity == "error"])

    def test_detach_persists_metadata_and_is_one_undoable_operation(self):
        self.db.db_store_object(self.image_id, "point", {
            "rId": "parent", "regionBoundary": boundary_from_pixel_coordinates("point", [100, 50])
        })
        original = {
            "rId": "source", "rMemberOf": "parent", "name": {"en": "Keep this name"},
            "regionBoundary": boundary_from_pixel_coordinates("multipoint", [[10, 10], [60, 20]]),
        }
        source_id = self.db.db_store_object(self.image_id, "multipoint", original)
        self.harness.detach_geometry_part(source_id, 0)
        new_id = self.harness.selected_id
        self.assertNotEqual(source_id, new_id)
        detached = json.loads(self.db.db_load_object(new_id)["data"])
        remaining = json.loads(self.db.db_load_object(source_id)["data"])
        self.assertEqual(detached["name"], original["name"])
        self.assertNotEqual(detached["rId"], original["rId"])
        self.assertNotIn("rMemberOf", detached)
        self.assertEqual(remaining["rMemberOf"], "parent")
        self.assertEqual(self.db.db_load_object(source_id)["object_type"], "point")
        self.db.undo(self.image_id)
        self.assertIsNone(self.db.db_load_object(new_id))
        self.assertEqual(json.loads(self.db.db_load_object(source_id)["data"]), original)
        self.db.redo(self.image_id)
        self.assertEqual(json.loads(self.db.db_load_object(new_id)["data"]), detached)

    def test_detach_parent_preserves_geometry_and_can_be_undone(self):
        original = {
            "rId": "child", "rMemberOf": "parent",
            "regionBoundary": boundary_from_pixel_coordinates("point", [10, 20]),
        }
        child_id = self.db.db_store_object(self.image_id, "point", original)
        self.harness.detach_region_parent(child_id)
        detached = json.loads(self.db.db_load_object(child_id)["data"])
        self.assertEqual(detached["regionBoundary"], original["regionBoundary"])
        self.assertNotIn("rMemberOf", detached)
        self.db.undo(self.image_id)
        self.assertEqual(json.loads(self.db.db_load_object(child_id)["data"]), original)

    def test_select_whole_region_after_part_without_deselecting_or_reloading(self):
        data = {"regionBoundary": boundary_from_pixel_coordinates("multipoint", [[10, 10], [60, 20]])}
        scene = DIGITIZERScene()
        scene.image_width, scene.image_height = 200, 100
        scene.color_point = QColor("blue")
        scene.add_object("multipoint", data, 1, QColor("blue"))
        editor = RegionEditorWidget()
        editor.load_graphis_objects([{"id": 1, "object_type": "multipoint", "data": json.dumps(data)}])
        scene.activate_geometry_part(1, 0)
        editor.select_geometry_part(1, 0)
        harness = SimpleNamespace(
            current_item={"id": 1, "data": data}, digitizer_scene=scene, region_editor=editor,
            _clear_geometry_operation=lambda: None, _graph_selection_active=False,
        )
        self.assertTrue(MainWindow._request_object_selection(harness, 1))
        self.assertIsNone(scene.active_item)
        self.assertEqual(editor.graph_scene.selected_object_id, "1")
        self.assertFalse(harness._graph_selection_active)

    def test_context_menus_offer_both_detach_actions(self):
        editor = RegionEditorWidget()
        multi = {"rId": "owner", "regionBoundary": boundary_from_pixel_coordinates("multipoint", [[10, 10], [60, 20]])}
        child = {"rMemberOf": "owner", "regionBoundary": boundary_from_pixel_coordinates("point", [80, 30])}
        editor.load_graphis_objects([
            {"id": 1, "data": json.dumps(multi)}, {"id": 2, "data": json.dumps(child)},
        ], image_width=200, image_height=100)
        detached_parts, detached_parents = [], []
        editor.detachGeometryPartRequested.connect(lambda owner, index: detached_parts.append((owner, index)))
        editor.detachParentRequested.connect(detached_parents.append)
        event = SimpleNamespace(scenePos=lambda: QPointF(), screenPos=lambda: QPoint(), accept=lambda: None)
        for node_id, title in (("1:point:0", "Detach as new image region"), ("2", "Detach from parent")):
            class ChooseMenu(QMenu):
                def exec(menu, *args, action_title=title):
                    action = next(action for action in menu.actions() if action.text() == action_title)
                    self.assertTrue(action.isEnabled())
                    return action

            editor.select_object(2)
            with (
                patch.object(editor.graph_scene, "_node_item_at", return_value=editor.graph_scene.node_items[node_id]),
                patch("graphis.app.imgregion.region_graph_scene.QMenu", ChooseMenu),
            ):
                editor.graph_scene.contextMenuEvent(event)
        self.assertEqual(detached_parts, [(1, 0)])
        self.assertEqual(detached_parents, [2])

    def test_detach_from_three_parts_keeps_multi_and_rejects_invalid_index(self):
        original = {"regionBoundary": boundary_from_pixel_coordinates("multipoint", [[10, 10], [60, 20], [80, 30]])}
        remaining, boundary = detach_multigeometry_part(original, 200, 100, 1)
        self.assertEqual(remaining["regionBoundary"]["rbShape"], "multipoint")
        self.assertEqual(json.loads(remaining["regionBoundary"]["rbCoordinates"]), [[10, 10], [80, 30]])
        self.assertEqual(json.loads(boundary["rbCoordinates"]), [60, 20])
        for index in (-1, 3):
            with self.assertRaises(ValueError):
                detach_multigeometry_part(original, 200, 100, index)
