import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication
from shapely.geometry import Polygon

from graphis.app.graphic.digitizerscene import DIGITIZERScene
from graphis.app.graphic.digitizerview import DIGITIZERView
from graphis.app.ki.controller import AISegmentationController
from graphis.app.ki.mask_polygon import mask_to_polygons
from graphis.db.db_handler import DBHandler
from graphis.main import MainWindow


class MaskPolygonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_conversion_draws_immediately_clears_mask_and_can_undo(self):
        with tempfile.TemporaryDirectory() as directory:
            db = DBHandler()
            db.db_create(Path(directory) / "test.sqlite", "test")
            try:
                image_id = db.db_store_image(Path(directory) / "image.jpg")
                db.db_store_size(image_id, 100, 100)
                scene = DIGITIZERScene()
                scene.db = db
                scene.image_id_db = image_id
                scene.image_width = scene.image_height = 100
                for shape in ("polygon", "rectangle", "circle", "point", "linestring"):
                    setattr(scene, f"color_{shape}", QColor("blue"))
                view = DIGITIZERView()
                view.setScene(scene)
                view.aiModeChanged.connect(scene.set_ai_mode_enabled)
                view.aiPreclassificationChanged.connect(scene.set_ai_preclassification_visible)
                view.ai_mode_button.setChecked(True)
                mask = np.zeros((100, 100), dtype=bool)
                mask[10:40, 10:40] = True
                mask[55:95, 55:95] = True  # larger part
                scene._set_ai_display_mask(mask)
                harness = SimpleNamespace(
                    digitizer_scene=scene,
                    view_digizizer=view,
                    color_polygon=QColor("blue"),
                    _ai_polygon_context=(image_id, scene._ai_current_mask),
                    _ensure_object_type_visible=lambda shape: None,
                    statusBar=lambda: SimpleNamespace(showMessage=lambda *args: None),
                )
                self.assertEqual(len(mask_to_polygons(mask)), 2)
                MainWindow._ai_mask_polygons_ready(harness, mask_to_polygons(mask, largest_only=True))
                items = [item for item in scene.items() if getattr(item, "object_type", None) == "polygon"]
                self.assertEqual(len(items), 1)
                self.assertTrue(items[0].isVisible() and items[0].is_valid())
                self.assertGreater(items[0].polygon().boundingRect().left(), 30)
                self.assertEqual(len(db.db_load_objects_image(image_id)), 1)
                self.assertIsNone(scene._ai_current_mask)
                self.assertIsNone(scene._ai_mask_item)
                self.assertFalse(scene.ai_mode_enabled)
                self.assertFalse(view.ai_mode_button.isChecked())
                db.undo(image_id)
                self.assertEqual(len(db.db_load_objects_image(image_id)), 0)
                db.redo(image_id)
                self.assertEqual(len(db.db_load_objects_image(image_id)), 1)
            finally:
                db.db_close()

    def test_pixel_threshold_holes_and_image_edge(self):
        mask = np.zeros((100, 100), dtype=bool)
        mask[:30, :30] = True
        mask[10:20, 10:20] = False
        mask[50:65, 50:70] = True  # Exactly 300 pixels: excluded.
        mask[75:90, 50:71] = True  # 315 pixels: included.
        polygons = [Polygon(points) for points in mask_to_polygons(mask, buffer_pixels=0, smoothing_pixels=0)]
        self.assertEqual(len(polygons), 2)
        self.assertTrue(all(p.is_valid and not p.interiors for p in polygons))
        self.assertTrue(np.allclose(polygons[0].bounds, (0, 0, 29, 29)))
        self.assertGreater(polygons[0].area, 29 * 29 * 0.98)
        self.assertAlmostEqual(polygons[0].area, 29 * 29, delta=1)

    def test_default_buffer_expands_twenty_pixels_and_clips_at_image_edges(self):
        mask = np.zeros((200, 200), dtype=bool)
        mask[60:140, 60:140] = True
        polygon = Polygon(mask_to_polygons(mask)[0])
        self.assertTrue(np.allclose(polygon.bounds, (40, 40, 159, 159), atol=0.2))
        self.assertTrue(polygon.is_valid and not polygon.interiors)
        mask[:80, :80] = True
        for points in mask_to_polygons(mask):
            self.assertTrue(all(0 <= x <= 199 and 0 <= y <= 199 for x, y in points))

    def test_stronger_smoothing_reduces_boundary_roughness(self):
        mask = np.zeros((200, 200), dtype=bool)
        mask[50:150, 50:150] = True
        for x in range(50, 150, 4):
            mask[45:50, x:x + 2] = True
        raw = Polygon(mask_to_polygons(mask, buffer_pixels=0, smoothing_pixels=0)[0])
        smooth = Polygon(mask_to_polygons(mask, buffer_pixels=0)[0])
        self.assertLess(smooth.length, raw.length * 0.9)
        self.assertTrue(smooth.is_valid)

    def test_complex_boundary_point_budget(self):
        mask = np.zeros((200, 1200), dtype=bool)
        mask[80:180, 10:1190] = True
        for x in range(10, 1190, 4):
            mask[20:80, x:x + 2] = True
        polygons = mask_to_polygons(mask)
        self.assertEqual(len(polygons), 1)
        self.assertLessEqual(len(polygons[0]), 400)
        self.assertTrue(Polygon(polygons[0]).is_valid)

    def test_empty_and_invalid_masks(self):
        self.assertEqual(mask_to_polygons(np.zeros((20, 20), dtype=bool)), [])
        with self.assertRaises(ValueError):
            mask_to_polygons(np.zeros((2, 2, 2)))

    def test_rectangles_accumulate_and_point_edits_preserve_earlier_parts(self):
        calls = []

        def predict(points, box):
            calls.append((points, box))
            mask = np.zeros((100, 100), dtype=bool)
            x1, y1, x2, y2 = map(int, box)
            mask[y1:y2, x1:x2] = True
            if points:
                mask[y1:y1 + 5, x1:x1 + 5] = False
            return mask

        scene = DIGITIZERScene()
        scene.image_width = scene.image_height = 100
        scene.ai_controller = AISegmentationController(
            SimpleNamespace(is_ready=True, predict_prompt_mask=predict, reset=lambda: None)
        )
        for start, end in ((10, 40), (60, 90)):
            scene._start_ai_rectangle_prompt(QPointF(start, start))
            scene._finish_ai_rectangle_prompt(QPointF(end, end))
            if start == 10:
                scene._add_ai_prompt(QPointF(12, 12), 0)
        self.assertEqual(len(calls[-1][0]), 0)  # Prior clicks do not constrain the new rectangle.
        self.assertTrue(scene._ai_current_mask[20, 20])
        self.assertFalse(scene._ai_current_mask[12, 12])
        self.assertTrue(scene._ai_current_mask[70, 70])
        scene._add_ai_prompt(QPointF(62, 62), 0)
        self.assertTrue(scene._ai_current_mask[20, 20])
        self.assertFalse(scene._ai_current_mask[62, 62])
        self.assertTrue(scene._ai_current_mask[70, 70])
        scene.reset_ai_segmentation(reload_backend=False)
        self.assertIsNone(scene._ai_current_mask)
        self.assertIsNone(scene._ai_accumulated_mask)
        self.assertEqual(scene.ai_controller.points, ())

    def test_failed_rectangle_restores_previous_prompts(self):
        def fail(points, box):
            raise RuntimeError("Prediction failed")

        controller = AISegmentationController(SimpleNamespace(is_ready=True, predict_prompt_mask=fail))
        controller._box = (1, 2, 20, 30)
        previous = controller.prompt_state()
        with self.assertRaises(RuntimeError):
            controller.predict_box((40, 40, 80, 80))
        self.assertEqual(controller.prompt_state(), previous)
