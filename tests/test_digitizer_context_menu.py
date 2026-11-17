import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtWidgets import QApplication, QMenu

from graphis.app.imgregion.region_editor import RegionEditorWidget
from graphis.interface.imgregion_adapter import boundary_from_pixel_coordinates
from graphis.main import MainWindow


class DigitizerContextMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.editor = RegionEditorWidget()
        self.rows = [
            {"id": 1, "object_type": "polygon", "data": json.dumps({
                "rId": "parent", "regionBoundary": boundary_from_pixel_coordinates(
                    "polygon", [[10, 10], [80, 10], [80, 80], [10, 80]]
                ),
            })},
            {"id": 2, "object_type": "multilinestring", "data": json.dumps({
                "rId": "child", "rMemberOf": "parent", "regionBoundary": boundary_from_pixel_coordinates(
                    "multilinestring", [[[10, 10], [20, 20]], [[30, 30], [40, 40]]]
                ),
            })},
        ]
        self.editor.load_graphis_objects(self.rows, image_width=100, image_height=100)
        self.harness = SimpleNamespace(
            region_editor=self.editor,
            digitizer_scene=SimpleNamespace(activate_geometry_part=Mock()),
            _request_object_selection=Mock(return_value=True),
            detach_geometry_part=Mock(),
        )

    def tearDown(self):
        self.editor.close()

    def menu(self, item):
        menu = QMenu()
        MainWindow._populate_digitizer_context_menu(self.harness, menu, item)
        return menu

    def test_shared_actions_exclude_geometry_assignment_and_dispatch_to_owner(self):
        menu = self.menu(SimpleNamespace(obj_id=1))
        actions = {action.text(): action for action in menu.actions()}
        self.assertFalse(any(text.startswith("Assign ") and text.endswith(" geometry") for text in actions))
        for text in ("Assign parent...", "Merge geometry into...", "Clear geometry", "Zoom to",
                     "Edit additional image region metadata...", "Delete image region", "Restore original image region"):
            self.assertIn(text, actions)
        self.assertNotIn("Detach from parent", actions)
        self.assertNotIn("Remove rMemberOf", actions)
        zooms, merges = [], []
        self.editor.zoomToRegionRequested.connect(zooms.append)
        self.editor.mergeTargetRequested.connect(lambda object_id, mode: merges.append((object_id, mode)))
        actions["Zoom to"].trigger()
        actions["Merge geometry into..."].menu().actions()[0].trigger()
        self.assertEqual(zooms, [1])
        self.assertEqual(merges, [(1, "inner_polygon")])

    def test_part_menu_detach_and_parent_actions(self):
        menu = self.menu(SimpleNamespace(obj_id=2, geometry_part_index=1, geometry_ring_index=0))
        actions = {action.text(): action for action in menu.actions()}
        self.harness.digitizer_scene.activate_geometry_part.assert_called_once_with(2, 1, 0)
        self.assertIn("Select whole image region", actions)
        actions["Detach as new image region"].trigger()
        self.harness.detach_geometry_part.assert_called_once_with(2, 1)
        detached = []
        self.editor.detachParentRequested.connect(detached.append)
        self.assertTrue(actions["Detach from parent"].isEnabled())
        actions["Detach from parent"].trigger()
        self.assertEqual(detached, [2])

    def test_invalid_membership_offers_removal_in_graph_and_digitizer(self):
        for value in ("missing", "child", 123, ""):
            with self.subTest(value=value):
                rows = [dict(row) for row in self.rows]
                region = json.loads(rows[1]["data"])
                region["rMemberOf"] = value
                rows[1]["data"] = json.dumps(region)
                self.editor.load_graphis_objects(rows, image_width=100, image_height=100)
                removed = []
                self.editor.detachParentRequested.connect(removed.append)
                menu = self.menu(SimpleNamespace(obj_id=2))
                actions = {action.text(): action for action in menu.actions()}
                self.assertNotIn("Detach from parent", actions)
                self.assertIn("Remove rMemberOf", actions)
                actions["Remove rMemberOf"].trigger()
                self.assertEqual(removed, [2])
                graph_menu = QMenu()
                graph = self.editor.graph_scene
                dispatch = graph.populate_region_context_menu(graph_menu, graph.node_items["2"])
                graph_actions = {action.text(): action for action in graph_menu.actions()}
                self.assertNotIn("Detach from parent", graph_actions)
                dispatch(graph_actions["Remove rMemberOf"])
                self.assertEqual(removed, [2, 2])
                self.editor.detachParentRequested.disconnect(removed.append)

    def test_cancelled_selection_does_not_populate_menu(self):
        self.harness._request_object_selection.return_value = False
        self.assertFalse(self.menu(SimpleNamespace(obj_id=1)).actions())

    def test_graph_offers_geometry_assignment_only_for_regions_without_geometry(self):
        self.editor.load_graphis_objects([{"id": 1, "data": json.dumps({"rId": "empty"})}])
        menu = QMenu()
        graph = self.editor.graph_scene
        dispatch = graph.populate_region_context_menu(menu, graph.node_items["1"])
        actions = {action.text(): action for action in menu.actions()}
        assigned = []
        self.editor.assignGeometryRequested.connect(lambda object_id, shape: assigned.append((object_id, shape)))
        dispatch(actions["Assign polygon geometry"])
        self.assertEqual(assigned, [(1, "polygon")])

    def test_graph_hides_geometry_assignment_for_existing_single_and_multi_geometries(self):
        graph = self.editor.graph_scene
        for object_id in ("1", "2"):
            with self.subTest(object_id=object_id):
                menu = QMenu()
                graph.populate_region_context_menu(menu, graph.node_items[object_id])
                self.assertFalse(any(
                    action.text().startswith("Assign ") and action.text().endswith(" geometry")
                    for action in menu.actions()
                ))

    def test_mixed_selection_is_preserved_but_has_no_grouping_action(self):
        graph = self.editor.graph_scene
        graph.set_group_selection(["1", "2"])
        self.harness._request_object_selection.side_effect = lambda object_id: (
            self.editor.select_object(object_id) or True
        )
        menu = self.menu(SimpleNamespace(obj_id=1))
        self.assertEqual(graph.selected_object_ids, {"1", "2"})
        self.assertNotIn("Group selected as", [action.text() for action in menu.actions()])


if __name__ == "__main__":
    unittest.main()
