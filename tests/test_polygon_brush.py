import gc
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QGraphicsSceneContextMenuEvent, QGraphicsSceneMouseEvent, QMenu
from shapely.geometry import Polygon

from graphis.app.graphic.digitizerscene import DIGITIZERScene
from graphis.app.graphic.digitizerview import DIGITIZERView
from graphis.app.graphic.geometry_smoothing import reduce_vertices, smooth_vertices
from graphis.app.graphic.polygon_brush import brush_polygon_boundary
from graphis.app.var_classes import Instructions
from graphis.db.db_handler import DBHandler
from graphis.interface.imgregion_adapter import change_region_unit, pixel_coordinates_from_region, validate_region_data

OUTER = [[20, 20], [80, 20], [80, 80], [20, 80], [20, 20]]


def event(x, y, button=Qt.MouseButton.LeftButton):
    result = QGraphicsSceneMouseEvent()
    result.setScenePos(QPointF(x, y))
    result.setButton(button)
    result.setButtons(button)
    return result


class PolygonBrushTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = DBHandler()
        self.db.db_create(Path(self.temp.name) / "test.sqlite", "test")
        self.image_id = self.db.db_store_image(Path(self.temp.name) / "image.jpg")
        self.db.db_store_size(self.image_id, 100, 100)
        self.scene = DIGITIZERScene()
        self.scene.db.db_close()
        self.scene.db = self.db
        self.scene.image_id_db = self.image_id
        self.scene.image_width = self.scene.image_height = 100
        self.scene.color_polygon = QColor("#56b4e9")
        pixmap = QPixmap(100, 100)
        pixmap.fill(Qt.GlobalColor.white)
        self.scene.image_item.setPixmap(pixmap)
        self.scene.addItem(self.scene.image_item)
        self.scene.setSceneRect(0, 0, 100, 100)
        self.view = DIGITIZERView()
        self.view.setScene(self.scene)
        self.view.resize(500, 500)
        self.view.polygonBrushToggled.connect(self.scene.set_polygon_brush_enabled)
        self.view.polygonBrushModeChanged.connect(self.scene.set_polygon_brush_mode)
        self.view.polygonBrushSizeChanged.connect(self.scene.set_polygon_brush_size)
        self.scene.polygonBrushEnabledChanged.connect(self.view.set_polygon_brush_checked)
        self.scene.selection_changed.connect(self.view.sync_overlay_buttons)
        self.scene.operationStateChanged.connect(self.view.sync_polygon_brush_controls)
        self.load_polygon()

    def tearDown(self):
        self.scene.clear()
        self.view.close()
        self.db.db_close()
        gc.collect()
        self.temp.cleanup()

    def load_polygon(self, rings=None, shape="polygon", part_index=None):
        if hasattr(self, "object_id"):
            self.scene.delete_object(self.object_id)
        self.data = {
            "rId": f"region-{len(self.db.db_load_objects_image(self.image_id))}",
            "name": {"en": f"Keep metadata {len(self.db.db_load_objects_image(self.image_id))}"},
            "regionBoundary": {"rbShape": shape, "rbUnit": "pixel", "rbCoordinates": json.dumps(rings or [OUTER])},
        }
        self.object_id = self.db.db_store_object(self.image_id, shape, self.data)
        self.scene.add_object(shape, self.data, self.object_id, self.scene.color_polygon)
        if part_index is None:
            self.scene.activate_object(self.object_id)
        else:
            self.scene.activate_geometry_part(self.object_id, part_index)
        self.scene.set_polygon_brush_size(20)
        self.scene.set_polygon_brush_enabled(True)

    def test_expand_shrink_contact_and_topology_rules(self):
        original = Polygon(OUTER)
        expanded = brush_polygon_boundary(OUTER, (75, 50), 10, "expand", 100, 100)
        shrunk = brush_polygon_boundary(OUTER, (85, 50), 10, "shrink", 100, 100)
        self.assertGreater(Polygon(expanded).area, original.area)
        self.assertLess(Polygon(shrunk).area, original.area)
        for position in ((50, 50), (95, 50)):
            self.assertIsNone(brush_polygon_boundary(OUTER, position, 10, "expand", 100, 100))
        neck = [[10, 10], [40, 10], [40, 40], [60, 40], [60, 10], [90, 10],
                [90, 90], [60, 90], [60, 50], [40, 50], [40, 90], [10, 90]]
        self.assertIsNone(brush_polygon_boundary(neck, (50, 45), 10, "shrink", 100, 100))
        clipped = brush_polygon_boundary([[85, 30], [99, 30], [99, 70], [85, 70]], (98, 35), 10, "expand", 100, 100)
        self.assertIsNotNone(clipped)
        self.assertTrue(all(0 <= x <= 100 and 0 <= y <= 100 for x, y in clipped))

    def test_dense_stroke_does_not_accumulate_redundant_vertices(self):
        coordinates = OUTER
        for step in range(200):
            edited = brush_polygon_boundary(coordinates, (78, 22 + step * 0.28), 10, "expand", 100, 100)
            if edited is not None:
                coordinates = edited
        polygon = Polygon(coordinates)
        self.assertTrue(polygon.is_valid)
        self.assertFalse(polygon.interiors)
        self.assertLess(len(coordinates), 100)
        self.assertTrue(polygon.covers(Polygon(OUTER)))

    def test_smooth_polygon_is_one_undoable_edit(self):
        before = self.db.db_load_object(self.object_id)["data"]
        self.assertTrue(self.scene.smooth_selected_geometry())
        after = self.db.db_load_object(self.object_id)["data"]
        self.assertNotEqual(before, after)
        shape, coordinates = pixel_coordinates_from_region(json.loads(after), 100, 100)
        self.assertEqual(shape, "polygon")
        self.assertLess(Polygon(coordinates).area, Polygon(OUTER).area)
        self.assertEqual(json.loads(before)["name"], json.loads(after)["name"])
        self.db.undo(self.image_id)
        self.assertEqual(self.db.db_load_object(self.object_id)["data"], before)
        self.db.redo(self.image_id)
        self.assertEqual(self.db.db_load_object(self.object_id)["data"], after)

    def test_smooth_line_preserves_endpoints_and_selected_part(self):
        line = [[10, 10], [50, 80], [90, 10]]
        smoothed = smooth_vertices(line, closed=False)
        self.assertEqual(smoothed[0], line[0])
        self.assertEqual(smoothed[-1], line[-1])
        self.assertNotIn(line[1], smoothed)
        other = [[10, 90], [90, 90]]
        self.load_polygon(rings=[line, other], shape="multilinestring", part_index=0)
        self.assertTrue(self.scene.smooth_selected_geometry())
        _, coordinates = pixel_coordinates_from_region(
            json.loads(self.db.db_load_object(self.object_id)["data"]), 100, 100
        )
        self.assertEqual(coordinates[0][0], line[0])
        self.assertEqual(coordinates[0][-1], line[-1])
        self.assertEqual(coordinates[1], other)

    def test_smooth_rejects_cutting_across_existing_hole(self):
        hole = [[22, 22], [30, 22], [30, 30], [22, 30], [22, 22]]
        self.load_polygon(rings=[OUTER, hole], part_index=0)
        before = self.db.db_load_object(self.object_id)["data"]
        original = self.scene.active_geometry_item().polygon()
        self.assertFalse(self.scene.smooth_selected_geometry())
        self.assertEqual(self.db.db_load_object(self.object_id)["data"], before)
        self.assertEqual(self.scene.active_geometry_item().polygon(), original)

    def test_smooth_context_menu_requests_action_only_for_selection(self):
        self.scene.set_polygon_brush_enabled(False)
        requested = []
        self.scene.smoothGeometryRequested.connect(lambda: requested.append(True))
        with patch("graphis.app.graphic.digitizerscene.QtWidgets.QMenu") as menu_class:
            menu = menu_class.return_value
            menu.exec.return_value = menu.addAction.return_value
            context_event = QGraphicsSceneContextMenuEvent()
            self.scene.contextMenuEvent(context_event)
            menu.addAction.assert_any_call("Smooth")
            menu.addAction.assert_any_call("Reduce vertices (10%)")
            self.assertEqual(requested, [True])
            self.scene.clear_active_object()
            self.scene.contextMenuEvent(QGraphicsSceneContextMenuEvent())
            self.assertEqual(menu_class.call_count, 1)

    def test_context_menu_targets_clicked_geometry_and_supports_other_shapes(self):
        self.scene.set_polygon_brush_enabled(False)
        circle = {"regionBoundary": {"rbShape": "circle", "rbUnit": "pixel", "rbX": 50, "rbY": 50, "rbRx": 10}}
        self.scene.add_object("circle", circle, 987, QColor("orange"))
        targets, selected = [], []

        def populate(menu, item):
            targets.append(item.obj_id)
            menu.addAction("Zoom to").triggered.connect(lambda: selected.append(item.obj_id))

        self.scene.populateContextMenuRequested.connect(populate)

        menu = QMenu()

        def execute(position):
            actions = {action.text(): action for action in menu.actions()}
            self.assertNotIn("Smooth", actions)
            actions["Zoom to"].trigger()
            return actions["Zoom to"]

        context_event = QGraphicsSceneContextMenuEvent()
        context_event.setScenePos(QPointF(50, 50))
        proxy = SimpleNamespace(
            addAction=menu.addAction, addSeparator=menu.addSeparator, actions=menu.actions, exec=execute
        )
        with patch("graphis.app.graphic.digitizerscene.QtWidgets.QMenu", return_value=proxy):
            self.scene.contextMenuEvent(context_event)
        self.assertEqual(targets, [987])
        self.assertEqual(selected, [987])

    def test_creation_uses_left_click_and_right_click_finishes_only_lines_and_polygons(self):
        self.scene.set_polygon_brush_enabled(False)
        for kind in ("point", "rectangle", "circle", "linestring"):
            setattr(self.scene, f"color_{kind}", QColor("orange"))
        for shape, instruction, clicks in (
            ("point", Instructions.Point_Instruction, [(10, 10, Qt.MouseButton.LeftButton)]),
            ("rectangle", Instructions.Rectangle_Instruction,
             [(10, 10, Qt.MouseButton.LeftButton), (40, 40, Qt.MouseButton.LeftButton)]),
            ("circle", Instructions.Circle_Instruction,
             [(50, 50, Qt.MouseButton.LeftButton), (60, 55, Qt.MouseButton.LeftButton)]),
            ("polygon", Instructions.Polygon_Instruction,
             [(10, 10, Qt.MouseButton.LeftButton), (40, 10, Qt.MouseButton.LeftButton),
              (40, 40, Qt.MouseButton.LeftButton), (40, 40, Qt.MouseButton.RightButton)]),
            ("linestring", Instructions.Linestring_Instruction,
             [(10, 10, Qt.MouseButton.LeftButton), (30, 10, Qt.MouseButton.LeftButton),
              (30, 30, Qt.MouseButton.RightButton)]),
        ):
            with self.subTest(shape=shape):
                before = len(self.db.db_load_objects_image(self.image_id))
                self.scene.clear_current_operation()
                self.scene.current_instruction = instruction
                self.scene.mousePressEvent(event(10, 10, Qt.MouseButton.RightButton))
                with patch("graphis.app.graphic.digitizerscene.QtWidgets.QMenu") as menu:
                    self.scene.contextMenuEvent(QGraphicsSceneContextMenuEvent())
                    menu.assert_not_called()
                self.assertEqual(len(self.db.db_load_objects_image(self.image_id)), before)
                for x, y, button in clicks:
                    self.scene.mousePressEvent(event(x, y, button))
                self.assertFalse(self.scene.instruction_active)
                rows = self.db.db_load_objects_image(self.image_id)
                self.assertEqual(len(rows), before + 1)
                row = rows[-1]
                self.assertEqual(row["object_type"], shape)
                self.assertFalse([issue for issue in validate_region_data(json.loads(row["data"]), 100, 100)
                                  if issue.severity == "error"])
                if shape in {"polygon", "linestring"}:
                    # The main window may clear the tool before Windows delivers
                    # the right-button-release context menu event.
                    self.scene.clear_current_operation()
                    with patch("graphis.app.graphic.digitizerscene.QtWidgets.QMenu") as menu:
                        context = QGraphicsSceneContextMenuEvent()
                        self.scene.contextMenuEvent(context)
                        menu.assert_not_called()
                        self.assertTrue(context.isAccepted())

    def test_left_click_moves_geometry_and_right_click_cancels_without_context_menu(self):
        self.scene.set_polygon_brush_enabled(False)
        before = self.db.db_load_object(self.object_id)["data"]
        original = self.scene.active_geometry_item().polygon()
        self.scene.current_instruction = Instructions.Move_Instruction
        self.scene.mousePressEvent(event(50, 50))
        self.assertTrue(self.scene.instruction_active)
        self.scene.mouseMoveEvent(event(55, 55))
        self.scene.mousePressEvent(event(55, 55))
        self.assertFalse(self.scene.instruction_active)
        self.assertNotEqual(self.db.db_load_object(self.object_id)["data"], before)
        self.db.undo(self.image_id)
        self.assertEqual(self.db.db_load_object(self.object_id)["data"], before)
        self.scene.active_geometry_item().setPolygon(original)
        self.scene.current_instruction = Instructions.Move_Instruction
        self.scene.mousePressEvent(event(50, 50))
        self.scene.mouseMoveEvent(event(55, 55))
        self.scene.mousePressEvent(event(55, 55, Qt.MouseButton.RightButton))
        self.assertFalse(self.scene.instruction_active)
        self.assertEqual(self.scene.active_geometry_item().polygon(), original)
        self.assertEqual(self.db.db_load_object(self.object_id)["data"], before)
        with patch("graphis.app.graphic.digitizerscene.QtWidgets.QMenu") as menu:
            self.scene.contextMenuEvent(QGraphicsSceneContextMenuEvent())
            menu.assert_not_called()

    def test_left_click_adds_changes_and_removes_vertices(self):
        self.scene.set_polygon_brush_enabled(False)
        before = self.db.db_load_object(self.object_id)["data"]
        item = self.scene.active_geometry_item()
        self.scene.current_instruction = Instructions.Add_Point
        self.scene.mousePressEvent(event(80, 50))
        self.assertTrue(self.scene.instruction_active)
        self.scene.mouseMoveEvent(event(85, 50))
        self.scene.mousePressEvent(event(85, 50))
        self.assertFalse(self.scene.instruction_active)
        after_add = self.db.db_load_object(self.object_id)["data"]
        self.assertNotEqual(after_add, before)
        self.assertEqual(len(item.polygon()), 6)  # Four corners, closing point, new vertex.
        self.scene.current_instruction = Instructions.Change_Instruction
        self.scene.mousePressEvent(event(85, 50))
        self.assertTrue(self.scene.instruction_active)
        self.scene.mouseMoveEvent(event(90, 50))
        self.scene.mousePressEvent(event(90, 50))
        self.assertFalse(self.scene.instruction_active)
        self.assertNotEqual(self.db.db_load_object(self.object_id)["data"], after_add)
        self.scene.current_instruction = Instructions.Remove_Point
        self.scene.mousePressEvent(event(90, 50))
        self.assertEqual(len(item.polygon()), 5)
        self.db.undo(self.image_id)
        self.assertEqual(len(pixel_coordinates_from_region(
            json.loads(self.db.db_load_object(self.object_id)["data"]), 100, 100
        )[1]), 6)

    def test_reduce_vertices_preserves_endpoints_and_minimum_counts(self):
        line = [[i, i % 2] for i in range(20)]
        reduced = reduce_vertices(line, closed=False)
        self.assertEqual(len(reduced), 18)
        self.assertEqual(reduced[0], line[0])
        self.assertEqual(reduced[-1], line[-1])
        triangle = [[0, 0], [10, 0], [5, 10]]
        self.assertEqual(reduce_vertices(triangle + [triangle[0]], closed=True), triangle)

    def test_reduce_polygon_saves_ten_percent_fewer_vertices_and_supports_undo(self):
        points = ([[20 + i * 12, 20] for i in range(5)]
                  + [[80, 20 + i * 12] for i in range(5)]
                  + [[80 - i * 12, 80] for i in range(5)]
                  + [[20, 80 - i * 12] for i in range(5)])
        self.load_polygon(rings=[points + [points[0]]])
        before = self.db.db_load_object(self.object_id)["data"]
        self.assertTrue(self.scene.reduce_selected_vertices())
        after = self.db.db_load_object(self.object_id)["data"]
        _, coordinates = pixel_coordinates_from_region(json.loads(after), 100, 100)
        self.assertEqual(len(coordinates) - (coordinates[0] == coordinates[-1]), 18)
        self.assertTrue(Polygon(coordinates).equals(Polygon(points)))
        self.assertEqual(json.loads(before)["name"], json.loads(after)["name"])
        self.db.undo(self.image_id)
        self.assertEqual(self.db.db_load_object(self.object_id)["data"], before)
        self.db.redo(self.image_id)
        self.assertEqual(self.db.db_load_object(self.object_id)["data"], after)

    def test_drag_previews_then_commits_one_undoable_edit(self):
        before = self.db.db_load_object(self.object_id)["data"]
        self.scene.mousePressEvent(event(75, 50))
        self.scene.mouseMoveEvent(event(75, 60))
        self.assertEqual(self.db.db_load_object(self.object_id)["data"], before)
        self.assertTrue(self.scene.instruction_active)
        self.scene.mouseReleaseEvent(event(75, 60))
        after = self.db.db_load_object(self.object_id)["data"]
        self.assertNotEqual(before, after)
        self.assertFalse(self.scene.instruction_active)
        self.assertTrue(self.scene.polygon_brush_enabled)
        self.assertEqual(json.loads(after)["name"], self.data["name"])
        self.db.undo(self.image_id)
        self.assertEqual(self.db.db_load_object(self.object_id)["data"], before)
        self.db.redo(self.image_id)
        self.assertEqual(self.db.db_load_object(self.object_id)["data"], after)

    def test_no_contact_does_not_record_an_undo_step(self):
        self.scene.mousePressEvent(event(50, 50))
        self.scene.mouseReleaseEvent(event(50, 50))
        self.db.undo(self.image_id)
        self.assertIsNone(self.db.db_load_object(self.object_id))

    def test_cancel_restores_preview_without_database_changes(self):
        item = self.scene.active_geometry_item()
        original = item.polygon()
        before = self.db.db_load_object(self.object_id)["data"]
        self.scene.mousePressEvent(event(75, 50))
        self.assertNotEqual(item.polygon(), original)
        self.scene.mousePressEvent(event(75, 50, Qt.MouseButton.RightButton))
        self.assertEqual(item.polygon(), original)
        self.assertEqual(self.db.db_load_object(self.object_id)["data"], before)
        self.assertFalse(self.scene.instruction_active)
        self.assertFalse(self.scene.polygon_brush_enabled)

    def test_holes_and_other_parts_are_protected(self):
        hole = [[60, 40], [75, 40], [75, 60], [60, 60], [60, 40]]
        self.load_polygon([OUTER, hole], part_index=0)
        self.scene.set_polygon_brush_mode("shrink")
        before = self.db.db_load_object(self.object_id)["data"]
        self.scene.mousePressEvent(event(82, 50))
        self.scene.mouseReleaseEvent(event(82, 50))
        self.assertEqual(self.db.db_load_object(self.object_id)["data"], before)
        first = [[20, 20], [45, 20], [45, 80], [20, 80], [20, 20]]
        second = [[50, 20], [80, 20], [80, 80], [50, 80], [50, 20]]
        self.load_polygon([[first], [second]], shape="multipolygon", part_index=0)
        self.scene.set_polygon_brush_mode("expand")
        before = self.db.db_load_object(self.object_id)["data"]
        self.scene.mousePressEvent(event(43, 50))
        self.scene.mouseReleaseEvent(event(43, 50))
        self.assertEqual(self.db.db_load_object(self.object_id)["data"], before)
        self.scene.mousePressEvent(event(21, 50))
        self.scene.mouseReleaseEvent(event(21, 50))
        data = json.loads(self.db.db_load_object(self.object_id)["data"])
        self.assertEqual(pixel_coordinates_from_region(data, 100, 100)[1][1], [second])

    def test_controls_size_modes_visibility_and_real_view_drag(self):
        self.view.show()
        self.app.processEvents()
        self.scene.set_polygon_brush_enabled(False)
        self.view.sync_overlay_buttons()
        self.assertFalse(self.view.polygon_brush_controls.isHidden())
        self.assertTrue(self.view.polygon_brush_settings.isHidden())
        self.view.polygon_brush_button.click()
        self.assertTrue(self.scene.polygon_brush_enabled)
        self.assertFalse(self.view.polygon_brush_settings.isHidden())
        self.assertEqual((self.view.polygon_brush_slider.minimum(), self.view.polygon_brush_slider.maximum()), (4, 200))
        self.view.polygon_brush_slider.setValue(20)
        self.view.polygon_brush_shrink.click()
        self.assertEqual(self.scene.polygon_brush_mode, "shrink")
        self.view.polygon_brush_expand.click()
        self.assertEqual(self.scene.polygon_brush_mode, "expand")
        before = self.db.db_load_object(self.object_id)["data"]
        point = self.view.mapFromScene(QPointF(75, 50))
        QTest.mousePress(self.view.viewport(), Qt.MouseButton.LeftButton, pos=point)
        QTest.mouseRelease(self.view.viewport(), Qt.MouseButton.LeftButton, pos=point)
        self.assertNotEqual(self.db.db_load_object(self.object_id)["data"], before)
        self.scene.clear_active_object()
        self.assertTrue(self.view.polygon_brush_controls.isHidden())
        self.assertFalse(self.view.polygon_brush_button.isChecked())

    def test_relative_units_and_brush_stays_active_after_scene_rebuild(self):
        relative = change_region_unit(self.data, "relative", 100, 100)
        self.db.update_object(self.object_id, data=relative)

        def rebuild(object_id):
            data = json.loads(self.db.db_load_object(object_id)["data"])
            self.scene.delete_object(object_id)
            self.scene.add_object("polygon", data, object_id, self.scene.color_polygon)
            self.scene.clear_current_operation()
            self.scene.activate_object(object_id)

        self.scene.change_object.connect(rebuild)
        self.scene.mousePressEvent(event(75, 50))
        self.scene.mouseReleaseEvent(event(75, 50))
        data = json.loads(self.db.db_load_object(self.object_id)["data"])
        self.assertEqual(data["regionBoundary"]["rbUnit"], "relative")
        self.assertTrue(self.scene.polygon_brush_enabled)
        self.assertTrue(self.view.polygon_brush_button.isChecked())
        self.assertIsNotNone(self.scene.active_polygon_item())

    def test_inner_ring_is_not_a_brush_target(self):
        hole = [[40, 40], [60, 40], [60, 60], [40, 60], [40, 40]]
        self.load_polygon([OUTER, hole], part_index=0)
        self.scene.activate_geometry_part(self.object_id, 0, 1)
        self.view.sync_overlay_buttons()
        self.assertIsNone(self.scene.polygon_brush_target())
        self.assertTrue(self.view.polygon_brush_controls.isHidden())
        self.assertFalse(self.scene.polygon_brush_enabled)
