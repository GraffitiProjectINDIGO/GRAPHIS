import copy
import gc
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QGraphicsSceneMouseEvent, QMenu

from graphis.app.graphic.digitizerscene import DIGITIZERScene
from graphis.app.gui.region_operations_toolbar import RegionOperationsToolbar
from graphis.app.imgregion.region_editor import RegionEditorWidget
from graphis.db.db_handler import DBHandler
from graphis.interface.imgregion_adapter import (
    boundary_from_pixel_coordinates,
    change_region_unit,
    combine_multigeometry_regions,
    pixel_coordinates_from_region,
    remove_multigeometry_part,
    update_multigeometry_part_from_pixels,
    validate_region_data,
)
from graphis.main import MainWindow


def region(shape, coordinates, identifier="region"):
    return {"rId": identifier, "regionBoundary": boundary_from_pixel_coordinates(shape, coordinates)}


class GroupingHarness:
    _create_multigeometry_container = MainWindow._create_multigeometry_container
    _absorb_multigeometry_sources = MainWindow._absorb_multigeometry_sources
    _region_parent_object_map = MainWindow._region_parent_object_map
    _regions_of = MainWindow._regions_of
    _assign_region_parent = MainWindow._assign_region_parent
    _assign_region_members = MainWindow._assign_region_members
    _would_create_parent_cycle = MainWindow._would_create_parent_cycle
    _valid_group_child_ids = MainWindow._valid_group_child_ids
    _accepted_child_shapes = MainWindow._accepted_child_shapes
    group_image_regions_into_container = MainWindow.group_image_regions_into_container

    def _new_multigeometry_region_data(self, shape):
        return {"regionBoundary": {"rbShape": shape, "rbUnit": "pixel", "rbCoordinates": "[]"}}

    def _db_ready_for(self, action):
        return True

    def _current_image_ready_for_region_edit(self, action):
        return True

    def _guard_unsaved_region_metadata_changes(self, action):
        return True

    def _refresh_after_region_grouping(self, object_id):
        self.refreshed_id = object_id


class MultigeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = DBHandler()
        self.db.db_create(Path(self.temp.name) / "test.sqlite", "test")
        self.image_id = self.db.db_store_image(Path(self.temp.name) / "image.jpg")
        self.db.db_store_size(self.image_id, 200, 100)
        self.harness = GroupingHarness()
        self.harness.db = self.db
        self.harness.image_loading_image_id_db = self.image_id

    def tearDown(self):
        self.db.db_close()
        gc.collect()
        self.temp.cleanup()

    def store(self, shape, coordinates, identifier):
        return self.db.db_store_object(self.image_id, shape, region(shape, coordinates, identifier))

    def rows(self):
        return self.db.db_load_objects_image(self.image_id)

    def test_grouping_persists_one_json_and_undo_restores_sources(self):
        for shape, mode, first, second in (
            ("point", "multipoint", [10, 10], [50, 30]),
            ("linestring", "multilinestring", [[10, 10], [20, 20]], [[50, 10], [80, 20]]),
            ("polygon", "multipolygon", [[10, 10], [30, 10], [30, 30]], [[50, 10], [80, 10], [80, 30]]),
        ):
            with self.subTest(mode=mode):
                source_ids = [self.store(shape, first, "first"), self.store(shape, second, "second")]
                originals = {row["id"]: row["data"] for row in self.rows()}
                target_id = self.harness._create_multigeometry_container(mode, source_ids)
                self.assertIsNotNone(target_id)
                self.assertEqual(len(self.rows()), 1)
                data = json.loads(self.rows()[0]["data"])
                self.assertEqual(data["rId"], "first")
                self.assertEqual(len(json.loads(data["regionBoundary"]["rbCoordinates"])), 2)
                self.assertFalse([issue for issue in validate_region_data(data, 200, 100) if issue.severity == "error"])
                self.db.undo(self.image_id)
                self.assertEqual({row["id"]: row["data"] for row in self.rows()}, originals)
                self.db.redo(self.image_id)
                self.assertEqual([row["id"] for row in self.rows()], [target_id])
                self.db.db_delete_geometry(target_id)

    def test_ctrl_selection_in_digitizer_groups_each_type_and_undo_restores_sources(self):
        for shape, mode, first, second in (
            ("point", "multipoint", [10, 10], [150, 70]),
            ("linestring", "multilinestring", [[10, 10], [20, 20]], [[150, 50], [180, 70]]),
            ("polygon", "multipolygon", [[10, 10], [30, 10], [30, 30]], [[150, 50], [180, 50], [180, 70]]),
        ):
            with self.subTest(shape=shape):
                ids = [self.store(shape, first, "first"), self.store(shape, second, "second")]
                originals = {row["id"]: row["data"] for row in self.rows()}
                scene = DIGITIZERScene()
                scene.db.db_close()
                scene.db = self.db
                scene.image_width, scene.image_height = 200, 100
                setattr(scene, f"color_{shape}", QColor("orange"))
                for row in self.rows():
                    scene.add_object(shape, json.loads(row["data"]), row["id"], QColor("orange"))
                editor = RegionEditorWidget()
                editor.load_graphis_objects(self.rows(), image_width=200, image_height=100)
                graph = editor.graph_scene
                scene.groupSelectionToggled.connect(graph.toggle_group_selection)
                scene.groupSelectionCleared.connect(graph.clear_group_selection)
                graph.groupSelectionChanged.connect(scene.set_group_selection)
                editor.groupRegionsRequested.connect(lambda selected, kind: MainWindow.group_image_regions(
                    self.harness, selected, kind
                ))

                def select(object_id, scene=scene, editor=editor):
                    scene.activate_object(object_id)
                    editor.select_object(object_id)
                    return True

                self.harness._request_object_selection = select
                self.harness.digitizer_scene = scene
                self.harness.region_editor = editor
                for position in ((10, 10), (150, 70) if shape == "point" else (150, 50)):
                    click = QGraphicsSceneMouseEvent()
                    click.setScenePos(QPointF(*position))
                    click.setButton(Qt.MouseButton.LeftButton)
                    click.setModifiers(Qt.KeyboardModifier.ControlModifier)
                    scene.mousePressEvent(click)
                self.assertEqual(scene.group_selection_ids, set(ids))
                self.assertEqual(graph.selected_object_ids, {str(object_id) for object_id in ids})
                scene.mousePressEvent(click)
                self.assertEqual(scene.group_selection_ids, {ids[0]})
                scene.mousePressEvent(click)
                self.assertEqual(scene.group_selection_ids, set(ids))
                self.assertTrue(all(getattr(item, "group_selected", False) for item in scene.items()))
                item = next(item for item in scene.items() if item.obj_id == ids[0])
                menu = QMenu()
                MainWindow._populate_digitizer_context_menu(self.harness, menu, item)
                self.assertEqual(scene.group_selection_ids, set(ids))
                actions = {action.text(): action for action in menu.actions()}
                grouping = actions["Group selected as"].menu()
                self.assertEqual(grouping.actions()[0].text(), mode)
                grouping.actions()[0].trigger()
                self.assertEqual(len(self.rows()), 1)
                self.assertEqual(self.rows()[0]["object_type"], mode)
                self.db.undo(self.image_id)
                self.assertEqual({row["id"]: row["data"] for row in self.rows()}, originals)
                self.db.redo(self.image_id)
                self.db.db_delete_geometry(self.rows()[0]["id"])
                graph.clear_graph()
                self.assertFalse(scene.group_selection_ids)
                scene.clear()
                editor.close()

    def test_legacy_empty_container_can_absorb_linked_polygons(self):
        target_id = self.db.db_store_object(
            self.image_id, "multipolygon", self.harness._new_multigeometry_region_data("multipolygon")
        )
        ids = [
            self.store("rectangle", [[10, 10], [30, 30]], "first"),
            self.store("polygon", [[50, 10], [80, 10], [80, 30]], "second"),
        ]
        self.harness._assign_region_parent(ids, target_id, "Link regions")
        editor = RegionEditorWidget()
        editor.load_graphis_objects(self.rows())
        actions = editor.graph_scene._add_group_actions(QMenu(), (), str(target_id))
        self.assertIn("linked_parts", [value[0] for value in actions.values()])
        self.harness.group_image_regions_into_container(ids, target_id)
        self.assertEqual([row["id"] for row in self.rows()], [target_id])
        data = json.loads(self.rows()[0]["data"])
        self.assertEqual(len(json.loads(data["regionBoundary"]["rbCoordinates"])), 2)
        self.assertFalse([issue for issue in validate_region_data(data, 200, 100) if issue.severity == "error"])
        self.db.undo(self.image_id)
        self.assertEqual(len(self.rows()), 3)

    def test_invalid_source_does_not_modify_database(self):
        first = self.store("point", [10, 10], "first")
        second = self.db.db_store_object(
            self.image_id, "point", {"regionBoundary": {"rbShape": "point", "rbCoordinates": "broken"}}
        )
        before = copy.deepcopy(self.rows())
        self.assertIsNone(self.harness._create_multigeometry_container("multipoint", [first, second]))
        self.assertEqual(self.rows(), before)

    def test_append_preserves_existing_parts_and_parent_links(self):
        ids = [self.store("point", [10, 10], "first"), self.store("point", [50, 30], "second")]
        target_id = self.harness._create_multigeometry_container("multipoint", ids)
        source_id = self.store("point", [100, 50], "third")
        child_id = self.store("point", [120, 50], "ordinary-child")
        self.harness._assign_region_parent([child_id], source_id, "Link child")
        before = {row["id"]: row["data"] for row in self.rows()}
        self.harness.group_image_regions_into_container([source_id], target_id)
        data = json.loads(self.db.db_load_object(target_id)["data"])
        self.assertEqual(json.loads(data["regionBoundary"]["rbCoordinates"]), [[10, 10], [50, 30], [100, 50]])
        self.assertEqual(json.loads(self.db.db_load_object(child_id)["data"])["rMemberOf"], data["rId"])
        self.assertIsNone(self.db.db_load_object(source_id))
        self.db.undo(self.image_id)
        self.assertEqual({row["id"]: row["data"] for row in self.rows()}, before)

    def test_empty_container_rejects_single_part_without_database_changes(self):
        target_id = self.db.db_store_object(
            self.image_id, "multipoint", self.harness._new_multigeometry_region_data("multipoint")
        )
        source_id = self.store("point", [10, 10], "first")
        before = copy.deepcopy(self.rows())
        self.harness.group_image_regions_into_container([source_id], target_id)
        self.assertEqual(self.rows(), before)

    def test_polygon_holes_and_units_survive_combination(self):
        outer = [[10, 10], [40, 10], [40, 40], [10, 40], [10, 10]]
        hole = [[20, 20], [25, 20], [20, 25], [20, 20]]
        separate = [[50, 50], [60, 50], [60, 60], [50, 60], [50, 50]]
        first = region("multipolygon", [[outer, hole], [separate]], "first")
        second = {"regionBoundary": {"rbShape": "rectangle", "rbUnit": "relative", "rbX": 0.5,
                                     "rbY": 0.1, "rbW": 0.2, "rbH": 0.2}}
        original = copy.deepcopy(first)
        combined = combine_multigeometry_regions(first, [second], 200, 100, "multipolygon")
        parts = json.loads(combined["regionBoundary"]["rbCoordinates"])
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[0], [outer, hole])
        self.assertEqual(parts[2][0][0], [100, 10])
        self.assertEqual(first, original)

    def test_view_parts_are_not_separate_regions(self):
        for shape, coordinates in (
            ("multipoint", [[10, 10], [50, 30]]),
            ("multilinestring", [[[10, 10], [20, 20]], [[50, 10], [80, 20]]]),
            ("multipolygon", [[[[10, 10], [30, 10], [30, 30], [10, 10]]],
                              [[[50, 10], [80, 10], [80, 30], [50, 10]]]]),
        ):
            with self.subTest(shape=shape):
                objects = [{"id": 1, "data": region(shape, coordinates)}]
                original = copy.deepcopy(objects)
                editor = RegionEditorWidget()
                editor.load_graphis_objects(objects)
                parts = [node for node in editor.nodes_by_id.values() if node.geometry_owner_id is not None]
                self.assertEqual(len(parts), 2)
                self.assertEqual(len(editor.graph_scene.arrow_items), 2)
                selected = []
                editor.geometryPartSelected.connect(
                    lambda owner, index, ring, events=selected: events.append((owner, index))
                )
                editor.graph_scene.request_select_region(parts[0].object_id)
                self.assertEqual(selected, [(1, 0)])
                self.assertEqual(objects, original)

    def test_selecting_part_activates_its_geometry_tools_and_updates_only_that_part(self):
        for shape, coordinates, new_coordinates in (
            ("multipoint", [[10, 10], [50, 30]], [60, 35]),
            ("multilinestring", [[[10, 10], [20, 20]], [[50, 10], [80, 20]]], [[55, 10], [80, 20]]),
            ("multipolygon", [[[[10, 10], [30, 10], [30, 30], [10, 10]]],
                              [[[50, 10], [80, 10], [80, 30], [50, 10]]]],
             [[55, 10], [80, 10], [80, 30], [55, 10]]),
        ):
            with self.subTest(shape=shape):
                data = region(shape, coordinates, shape)
                object_id = self.db.db_store_object(self.image_id, shape, data)
                scene = DIGITIZERScene()
                scene.db.con.close()
                scene.db = self.db
                scene.image_width, scene.image_height = 200, 100
                scene.add_object(shape, data, object_id, QColor("green"))
                scene.activate_object(object_id)
                self.assertIsNone(scene.active_geometry_item(), "Parent selection must not edit an arbitrary part")
                editor = RegionEditorWidget()
                editor.load_graphis_objects([self.db.db_load_object(object_id)])
                ui = SimpleNamespace(
                    _request_object_selection=lambda owner: True,
                    _clear_geometry_operation=scene.clear_current_operation,
                    _center_image_view_on_active_geometry=lambda: None,
                    digitizer_scene=scene,
                    region_editor=editor,
                )
                editor.geometryPartSelected.connect(
                    lambda owner, index, ring, target=ui: MainWindow._select_geometry_part(target, owner, index, ring)
                )
                part = next(node for node in editor.nodes_by_id.values() if node.geometry_part_index == 1)
                editor.graph_scene.request_select_region(part.object_id)
                item = scene.active_geometry_item()
                self.assertEqual(item.geometry_part_index, 1)
                if shape == "multipolygon":
                    self.assertEqual(item.polygon().length(), 3, "Closing coordinate is not a separate editable vertex")
                self.assertEqual(editor.graph_scene.selected_object_id, part.object_id)
                toolbar = RegionOperationsToolbar()
                toolbar.set_action_availability(has_selection=True, selected_object_type=item.object_type)
                self.assertTrue(toolbar.operation_actions["move_geometry"].isEnabled())
                self.assertEqual(toolbar.operation_actions["add_point"].isEnabled(), shape != "multipoint")
                self.assertTrue(scene._commit_geometry_update(item, new_coordinates, "Change geometry"))
                changed = json.loads(self.db.db_load_object(object_id)["data"])
                _shape, changed_parts = pixel_coordinates_from_region(changed, 200, 100)
                self.assertEqual(changed_parts[0], coordinates[0])
                self.assertNotEqual(changed_parts[1], coordinates[1])
                self.assertEqual(len(changed_parts), 2)
                self.db.undo(self.image_id)
                self.assertEqual(json.loads(self.db.db_load_object(object_id)["data"]), data)

    def test_polygon_part_movement_preserves_holes_units_and_siblings(self):
        outer = [[10, 10], [40, 10], [40, 40], [10, 40], [10, 10]]
        hole = [[20, 20], [25, 20], [20, 25], [20, 20]]
        sibling = [[[100, 10], [130, 10], [130, 40], [100, 10]]]
        data = region("multipolygon", [[outer, hole], sibling])
        moved = [[x + 5, y + 5] for x, y in outer]
        changed = update_multigeometry_part_from_pixels(data, 200, 100, 0, moved, move_polygon=True)
        _shape, parts = pixel_coordinates_from_region(changed, 200, 100)
        self.assertEqual(parts[0][0], moved)
        self.assertEqual(parts[0][1], [[x + 5, y + 5] for x, y in hole])
        self.assertEqual(parts[1], sibling)
        self.assertEqual(data["regionBoundary"]["rbUnit"], changed["regionBoundary"]["rbUnit"])
        relative = change_region_unit(data, "relative", 200, 100)
        changed_relative = update_multigeometry_part_from_pixels(relative, 200, 100, 0, moved, move_polygon=True)
        self.assertEqual(changed_relative["regionBoundary"]["rbUnit"], "relative")
        _shape, relative_parts = pixel_coordinates_from_region(changed_relative, 200, 100)
        self.assertEqual(relative_parts, parts)
        with self.assertRaises(ValueError):
            update_multigeometry_part_from_pixels(data, 200, 100, 0, [[0, 0], [1, 1], [2, 2]])

    def test_deleting_part_preserves_remaining_geometry(self):
        for shape, coordinates in (
            ("multipoint", [[10, 10], [50, 30]]),
            ("multilinestring", [[[10, 10], [20, 20]], [[50, 10], [80, 20]]]),
            ("multipolygon", [[[[10, 10], [30, 10], [30, 30], [10, 10]]],
                              [[[50, 10], [80, 10], [80, 30], [50, 10]]]]),
        ):
            with self.subTest(shape=shape):
                data = region(shape, coordinates)
                changed = remove_multigeometry_part(data, 200, 100, 0)
                self.assertEqual(changed["rId"], data["rId"])
                self.assertEqual(changed["regionBoundary"]["rbShape"], shape.removeprefix("multi"))
                self.assertEqual(json.loads(changed["regionBoundary"]["rbCoordinates"]), coordinates[1])

    def test_outer_and_inner_polygon_nodes_select_the_correct_ring(self):
        outer = [[10, 10], [80, 10], [80, 80], [10, 80], [10, 10]]
        inner = [[20, 20], [30, 20], [30, 30], [20, 30], [20, 20]]
        for shape, coordinates in (
            ("polygon", [outer, inner]),
            ("multipolygon", [[outer, inner], [[[100, 10], [120, 10], [120, 30], [100, 10]]]]),
        ):
            with self.subTest(shape=shape):
                data = {"rId": "rings", "regionBoundary": {"rbShape": shape, "rbUnit": "pixel",
                                                            "rbCoordinates": json.dumps(coordinates)}}
                objects = [{"id": 1, "data": data}]
                original = copy.deepcopy(objects)
                editor = RegionEditorWidget()
                editor.load_graphis_objects(objects)
                scene = DIGITIZERScene()
                scene.image_width, scene.image_height = 200, 100
                scene.color_polygon = QColor("green")
                scene.add_object(shape, data, 1, QColor("green"))
                ui = SimpleNamespace(
                    _request_object_selection=lambda owner: True,
                    _clear_geometry_operation=scene.clear_current_operation,
                    _center_image_view_on_active_geometry=lambda: None,
                    digitizer_scene=scene, region_editor=editor,
                )
                editor.geometryPartSelected.connect(
                    lambda owner, part, ring, target=ui: MainWindow._select_geometry_part(target, owner, part, ring)
                )
                ring_nodes = [node for node in editor.nodes_by_id.values() if node.geometry_ring_index is not None]
                outer_node = editor.nodes_by_id["1"] if shape == "polygon" else editor.nodes_by_id["1:polygon:0"]
                self.assertEqual(ring_nodes[0], outer_node)
                self.assertEqual([node.title for node in outer_node.children], ["Inner polygon 1"])
                self.assertFalse(any(node.title == "Outer polygon" for node in editor.nodes_by_id.values()))
                for ring_index, node in enumerate(ring_nodes):
                    editor.graph_scene.request_select_region(node.object_id)
                    self.assertEqual(scene.active_geometry_item().geometry_ring_index, ring_index)
                    self.assertEqual(editor.graph_scene.selected_object_id, node.object_id)
                scene.clear_active_object()
                hole_item = next(item for item in scene.items() if getattr(item, "geometry_ring_index", 0) == 1)
                self.assertEqual(hole_item.color_no_Alpha.name(), QColor("green").name())
                self.assertEqual(hole_item.pen().style(), Qt.PenStyle.DotLine)
                scene.change_color("polygon", QColor("#56B4E9"))
                self.assertEqual(hole_item.color_no_Alpha.name(), "#56b4e9")
                self.assertEqual(hole_item.pen().style(), Qt.PenStyle.DotLine)
                self.assertEqual(QColor(ring_nodes[1].background_color).name(), "#3b6e8d")
                self.assertEqual(ring_nodes[0].background_color, ring_nodes[1].background_color)
                self.assertEqual(objects, original)
                scene.db.db_close()

    def test_plain_polygon_ring_editing_and_deletion_preserve_the_region(self):
        outer = [[10, 10], [80, 10], [80, 80], [10, 80], [10, 10]]
        inner = [[20, 20], [30, 20], [30, 30], [20, 30], [20, 20]]
        data = {"rId": "rings", "regionBoundary": {"rbShape": "polygon", "rbUnit": "pixel",
                                                    "rbCoordinates": json.dumps([outer, inner])}}
        moved = [[x + 5, y + 5] for x, y in inner]
        changed = update_multigeometry_part_from_pixels(data, 200, 100, 0, moved, ring_index=1)
        self.assertEqual(json.loads(changed["regionBoundary"]["rbCoordinates"]), [outer, moved])
        changed = update_multigeometry_part_from_pixels(
            data, 200, 100, 0, [[x + 5, y + 5] for x, y in outer], move_polygon=True
        )
        self.assertEqual(json.loads(changed["regionBoundary"]["rbCoordinates"])[1], moved)
        deleted_inner = remove_multigeometry_part(data, 200, 100, 0, ring_index=1)
        self.assertEqual(json.loads(deleted_inner["regionBoundary"]["rbCoordinates"]), [outer])
        deleted_outer = remove_multigeometry_part(data, 200, 100, 0)
        self.assertEqual(deleted_outer, {"rId": "rings"})

    def test_rejected_inner_polygon_move_reports_the_validation_reason(self):
        outer = [[10, 10], [80, 10], [80, 80], [10, 80], [10, 10]]
        inner = [[20, 20], [30, 20], [30, 30], [20, 30], [20, 20]]
        data = {"regionBoundary": {"rbShape": "polygon", "rbUnit": "pixel",
                                    "rbCoordinates": json.dumps([outer, inner])}}
        object_id = self.db.db_store_object(self.image_id, "polygon", data)
        scene = DIGITIZERScene()
        scene.db.con.close()
        scene.db = self.db
        scene.image_width, scene.image_height = 200, 100
        scene.add_object("polygon", data, object_id, QColor("green"))
        scene.activate_geometry_part(object_id, 0, 1)
        item = scene.active_geometry_item()
        scene._begin_operation(item)
        original_polygon = item.polygon()
        item.move([100, 0])
        coordinates, valid = item.get_coords(200, 100)
        self.assertTrue(valid)
        messages = []
        scene.message_no_valid.connect(messages.append)
        self.assertFalse(scene._commit_geometry_update(item, coordinates, "Move geometry"))
        reason = scene._geometry_update_error
        self.assertIn("inner", reason.lower())
        scene._reject_active_geometry_operation()
        self.assertEqual(messages, [reason])
        self.assertNotIn("not enough points", messages[0])
        self.assertEqual(item.polygon(), original_polygon)
        self.assertEqual(json.loads(self.db.db_load_object(object_id)["data"]), data)
        self.assertIsNone(scene._geometry_update_error)

    def test_inner_polygon_merge_into_multipolygon_is_undoable(self):
        data = region("multipolygon", [
            [[[10, 10], [80, 10], [80, 80], [10, 80], [10, 10]]],
            [[[100, 10], [180, 10], [180, 80], [100, 80], [100, 10]]],
        ], "multi")
        target_id = self.db.db_store_object(self.image_id, "multipolygon", data)
        source_id = self.store("rectangle", [[120, 20], [140, 40]], "inner")
        before = {row["id"]: row["data"] for row in self.rows()}
        ui = SimpleNamespace(
            db=self.db,
            _db_ready_for=lambda action: True,
            _guard_unsaved_region_metadata_changes=lambda action: True,
            digitizer_scene=SimpleNamespace(delete_object=lambda object_id: None),
            _refresh_after_region_geometry_merge=lambda *args: None,
        )
        MainWindow.merge_image_regions(ui, source_id, target_id, "inner_polygon", target_part_index=1)
        self.assertEqual(len(self.rows()), 1)
        changed = json.loads(self.db.db_load_object(target_id)["data"])
        polygons = json.loads(changed["regionBoundary"]["rbCoordinates"])
        self.assertEqual(polygons[0], json.loads(data["regionBoundary"]["rbCoordinates"])[0])
        self.assertEqual(len(polygons[1]), 2)
        editor = RegionEditorWidget()
        editor.load_graphis_objects(self.rows())
        inner = next(node for node in editor.nodes_by_id.values() if node.geometry_ring_index == 1)
        self.assertEqual(inner.geometry_part_index, 1)
        self.assertEqual(QColor(inner.background_color).name(), "#3b6e8d")
        self.db.undo(self.image_id)
        self.assertEqual({row["id"]: row["data"] for row in self.rows()}, before)


if __name__ == "__main__":
    unittest.main()
