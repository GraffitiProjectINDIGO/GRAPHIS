import json
import unittest
from types import SimpleNamespace

from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from graphis.app.imgregion.region_editor import RegionEditorWidget
from graphis.app.imgregion.region_graph_items import RegionNodeItem
from graphis.app.imgregion.region_graph_model import RegionNode


class RegionGraphColorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_status_is_left_stripe_and_does_not_replace_geometry_fill(self):
        for severity, status_color in (("", "#24c768"), ("warning", "#d9a441"), ("error", "#e45b5b")):
            for selected in (False, True):
                with self.subTest(severity=severity, selected=selected):
                    node = RegionNode("1", None, {"regionBoundary": {"rbShape": "polygon"}}, [])
                    node.geometry_color = "#56b4e9"
                    if severity:
                        node.validation_issues = [SimpleNamespace(severity=severity, message="Example")]
                    item = RegionNodeItem(node)
                    item.set_active(selected)
                    image = QImage(
                        int(item.boundingRect().width()) + 8, int(item.HEIGHT) + 8, QImage.Format.Format_ARGB32
                    )
                    image.fill(QColor("black"))
                    painter = QPainter(image)
                    painter.translate(4, 4)
                    item.paint(painter, None)
                    painter.end()
                    self.assertEqual(image.pixelColor(24, 34).name(), "#3b6e8d")
                    self.assertEqual(image.pixelColor(7, 34).name(), status_color)
                    self.assertEqual(item.title_item.defaultTextColor().name(), "#ffffff")

    def test_configured_colors_update_multigeometry_parts_and_text_contrast(self):
        editor = RegionEditorWidget()
        region = {"regionBoundary": {"rbShape": "multipoint", "rbUnit": "pixel", "rbCoordinates": "[[10,10],[30,30]]"}}
        editor.set_geometry_color("point", QColor("#d55e00"))
        editor.load_graphis_objects([{"id": 1, "data": json.dumps(region)}])
        self.assertTrue(all(node.background_color == "#7a4319" for node in editor.nodes_by_id.values()))
        editor.set_geometry_color("point", QColor("#101010"))
        self.assertTrue(all(node.background_color == "#181c21" for node in editor.nodes_by_id.values()))
        self.assertTrue(all(
            item.title_item.defaultTextColor().name() == "#ffffff" for item in editor.graph_scene.node_items.values()
        ))
