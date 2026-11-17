import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QMenu

from graphis.app.imgregion.region_editor import RegionEditorWidget
from graphis.interface.imgregion_adapter import (
    boundary_from_pixel_coordinates,
    combine_multigeometry_regions,
    create_region_boundary,
    merge_region_geometries,
    valid_region_geometry_merge_modes,
)
from graphis.main import MainWindow


def region(shape, coordinates):
    return {"regionBoundary": boundary_from_pixel_coordinates(shape, coordinates)}


class MergePickerHarness:
    _begin_merge_target_selection = MainWindow._begin_merge_target_selection
    _begin_parent_assignment = MainWindow._begin_parent_assignment
    _cancel_parent_assignment = MainWindow._cancel_parent_assignment
    _pick_merge_target = MainWindow._pick_merge_target

    def __init__(self, editor, objects):
        self.region_editor = editor
        self.view_digizizer = QGraphicsView()
        self.image_loading_image_id_db = 1
        self.db = SimpleNamespace(db_load_object=objects.get)
        self.merges = []
        self.message = ""

    def statusBar(self):
        return SimpleNamespace(showMessage=lambda message: setattr(self, "message", message), clearMessage=lambda: None)

    def _db_ready_for(self, action):
        return True

    def _current_image_ready_for_region_edit(self, action):
        return True

    def _guard_unsaved_region_metadata_changes(self, action):
        return True

    def _clear_geometry_operation(self):
        pass

    def merge_image_regions(self, source, target, mode, target_part_index=None):
        result = (source, target, mode)
        self.merges.append(result if target_part_index is None else (*result, target_part_index))


class MergeTargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.source = region("rectangle", [[20, 20], [30, 30]])
        self.target = region("rectangle", [[10, 10], [80, 80]])
        self.multi = region("multipolygon", [
            [[[100, 10], [120, 10], [120, 30], [100, 10]]],
            [[[140, 10], [160, 10], [160, 30], [140, 10]]],
        ])
        self.objects = {
            index: {"id": index, "image": 1, "img_width": 200, "img_height": 100, "data": json.dumps(data)}
            for index, data in enumerate((self.source, self.target, self.multi), start=1)
        }
        self.editor = RegionEditorWidget()
        self.editor.load_graphis_objects(list(self.objects.values()), image_width=200, image_height=100)
        self.picker = MergePickerHarness(self.editor, self.objects)

    def test_menu_has_modes_without_target_name_submenus(self):
        self.editor.select_object(1)
        observed = []

        class InspectMenu(QMenu):
            def exec(menu, *args):
                children = menu.findChildren(QMenu)
                merge = next(child for child in children if child.title() == "Merge geometry into...")
                observed.extend(action.text() for action in merge.actions())
                self.assertTrue(all(action.menu() is None for action in merge.actions()))
                return merge.actions()[0]

        requested = []
        self.editor.mergeTargetRequested.connect(lambda owner, mode: requested.append((owner, mode)))
        node = self.editor.graph_scene.node_items["1"]
        event = SimpleNamespace(scenePos=lambda: node.sceneBoundingRect().center(), screenPos=lambda: QPoint(),
                                accept=lambda: None)
        with patch("graphis.app.imgregion.region_graph_scene.QMenu", InspectMenu):
            self.editor.graph_scene.contextMenuEvent(event)
        self.assertEqual(observed, ["As inner polygon", "As multigeometry"])
        self.assertEqual(requested, [(1, "inner_polygon")])

    def test_multigeometry_picker_rejects_normal_target_and_accepts_existing_multi(self):
        self.picker._begin_merge_target_selection(1, "multigeometry")
        self.assertIn("Choose", self.editor.ui.selection_guidance.text())
        self.assertFalse(self.editor.ui.selection_guidance.isHidden())
        self.picker._pick_merge_target(2)
        self.assertEqual(self.picker.merges, [])
        self.assertIsNotNone(self.picker._merge_target_selection)
        self.picker._pick_merge_target(1)
        self.assertEqual(self.picker.merges, [])
        self.picker._pick_merge_target(3)
        self.assertEqual(self.picker.merges, [(1, 3, "multipolygon")])
        self.assertIsNone(self.picker._merge_target_selection)
        self.assertTrue(self.editor.ui.selection_guidance.isHidden())

    def test_rectangle_can_be_merged_as_inner_polygon(self):
        self.assertEqual(valid_region_geometry_merge_modes(self.source, self.target, 200, 100), ["inner_polygon"])
        self.picker._begin_merge_target_selection(1, "inner_polygon")
        self.picker._pick_merge_target(2)
        self.assertEqual(self.picker.merges, [(1, 2, "inner_polygon")])
        merged = merge_region_geometries(self.target, self.source, 200, 100, "inner_polygon")
        self.assertEqual(len(json.loads(merged["regionBoundary"]["rbCoordinates"])), 2)

    def test_add_third_rectangle_after_grouping_first_two(self):
        for unit in ("pixel", "relative"):
            with self.subTest(unit=unit):
                rectangles = [
                    {"regionBoundary": create_region_boundary(
                        200, 100, "rectangle", [[x, 10], [x + 20, 30]], unit=unit
                    )}
                    for x in (10, 60, 110)
                ]
                container = {"regionBoundary": {"rbShape": "multipolygon", "rbUnit": unit, "rbCoordinates": "[]"}}
                target = combine_multigeometry_regions(container, rectangles[:2], 200, 100, "multipolygon")
                self.assertIn("multipolygon", valid_region_geometry_merge_modes(rectangles[2], target, 200, 100))
                merged = merge_region_geometries(target, rectangles[2], 200, 100, "multipolygon")
                self.assertEqual(merged["regionBoundary"]["rbShape"], "multipolygon")
                self.assertEqual(len(json.loads(merged["regionBoundary"]["rbCoordinates"])), 3)
                self.assertEqual(merged["regionBoundary"]["rbUnit"], unit)

    def test_overlapping_rectangle_reports_reason_and_keeps_target_picker_active(self):
        self.objects[1]["data"] = json.dumps(region("rectangle", [[105, 12], [115, 22]]))
        self.picker._begin_merge_target_selection(1, "multigeometry")
        with self.assertLogs("graphis.main", level="WARNING") as messages:
            self.picker._pick_merge_target(3)
        self.assertEqual(self.picker.merges, [])
        self.assertIsNotNone(self.picker._merge_target_selection)
        self.assertIn("overlap", " ".join(messages.output).lower())
        self.assertEqual(self.picker.message, "")

    def test_merge_backend_requires_existing_multi(self):
        for shape, coordinates, mode in (
            ("point", [10, 10], "multipoint"),
            ("linestring", [[10, 10], [20, 20]], "multilinestring"),
            ("rectangle", [[10, 10], [20, 20]], "multipolygon"),
        ):
            with self.subTest(shape=shape):
                data = region(shape, coordinates)
                self.assertNotIn(mode, valid_region_geometry_merge_modes(data, data, 200, 100))
                with self.assertRaises(ValueError):
                    merge_region_geometries(data, data, 200, 100, mode)

    def test_escape_image_change_and_switching_to_parent_cancel_merge_picking(self):
        self.picker._begin_merge_target_selection(1, "multigeometry")
        escape = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        self.assertTrue(MainWindow.eventFilter(self.picker, self.editor.ui.graphicsView.viewport(), escape))
        self.assertIsNone(self.picker._merge_target_selection)
        self.picker._begin_merge_target_selection(1, "multigeometry")
        self.picker.image_loading_image_id_db = 2
        self.picker._pick_merge_target(3)
        self.assertEqual(self.picker.merges, [])
        self.assertIsNone(self.picker._merge_target_selection)
        self.picker._begin_merge_target_selection(1, "multigeometry")
        self.picker._begin_parent_assignment(1)
        self.assertIsNone(self.picker._merge_target_selection)
        self.assertIsNotNone(self.picker._parent_assignment)

    def test_clicking_part_of_multigeometry_picks_its_owner(self):
        self.picker._begin_merge_target_selection(1, "multigeometry")
        view = self.editor.ui.graphicsView
        part = self.editor.graph_scene.node_items["3:polygon:0"]
        position = QPointF(view.mapFromScene(part.sceneBoundingRect().center()))
        event = QMouseEvent(QEvent.Type.MouseButtonRelease, position, position,
                            Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
        self.assertTrue(MainWindow.eventFilter(self.picker, view.viewport(), event))
        self.assertEqual(self.picker.merges, [(1, 3, "multipolygon")])

    def test_clicking_digitizer_geometry_picks_merge_target(self):
        self.picker._begin_merge_target_selection(1, "multigeometry")
        view = self.picker.view_digizizer
        scene = QGraphicsScene(view)
        view.setScene(scene)
        item = scene.addRect(0, 0, 30, 30)
        item.obj_id = 3
        position = QPointF(view.mapFromScene(item.sceneBoundingRect().center()))
        event = QMouseEvent(QEvent.Type.MouseButtonRelease, position, position,
                            Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
        self.assertTrue(MainWindow.eventFilter(self.picker, view.viewport(), event))
        self.assertEqual(self.picker.merges, [(1, 3, "multipolygon")])

    def test_inner_polygon_picker_preserves_clicked_part_in_both_views(self):
        source = region("rectangle", [[150, 12], [155, 16]])
        self.objects[1]["data"] = json.dumps(source)
        for digitizer in (False, True):
            with self.subTest(digitizer=digitizer):
                self.picker._begin_merge_target_selection(1, "inner_polygon")
                self.picker._pick_merge_target(3)
                self.assertIsNotNone(self.picker._merge_target_selection)
                self.picker._pick_merge_target(3, 0)
                self.assertIsNotNone(self.picker._merge_target_selection)
                self.picker._pick_merge_target(3, 1, 1)
                self.assertIsNotNone(self.picker._merge_target_selection)
                if digitizer:
                    view = self.picker.view_digizizer
                    scene = QGraphicsScene(view)
                    view.setScene(scene)
                    item = scene.addRect(0, 0, 30, 30)
                    item.obj_id = 3
                    item.geometry_part_index = 1
                    item.geometry_ring_index = 0
                else:
                    view = self.editor.ui.graphicsView
                    item = self.editor.graph_scene.node_items["3:polygon:1"]
                position = QPointF(view.mapFromScene(item.sceneBoundingRect().center()))
                event = QMouseEvent(QEvent.Type.MouseButtonRelease, position, position,
                                    Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
                self.assertTrue(MainWindow.eventFilter(self.picker, view.viewport(), event))
                self.assertEqual(self.picker.merges[-1], (1, 3, "inner_polygon", 1))
                self.assertIsNone(self.picker._merge_target_selection)
        merged = merge_region_geometries(self.multi, source, 200, 100, "inner_polygon", target_part_index=1)
        original_parts = json.loads(self.multi["regionBoundary"]["rbCoordinates"])
        merged_parts = json.loads(merged["regionBoundary"]["rbCoordinates"])
        self.assertEqual(merged_parts[0], original_parts[0])
        self.assertEqual(merged_parts[1][0], original_parts[1][0])
        self.assertEqual(len(merged_parts[1]), 2)
        self.assertEqual(merged["regionBoundary"]["rbShape"], "multipolygon")


if __name__ == "__main__":
    unittest.main()
