import unittest
from types import SimpleNamespace

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtWidgets import QApplication, QGraphicsSceneMouseEvent

from graphis.app.graphic.digitizerscene import DIGITIZERScene
from graphis.app.graphic.digitizerview import DIGITIZERView
from graphis.app.ki.background import predict_background
from graphis.app.ki.base import SegmentationPoint
from graphis.main import MainWindow


class BackgroundBrushTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_stroke_samples_negative_points_and_preserves_existing_prompts(self):
        original = [SegmentationPoint(30, 30, 1), SegmentationPoint(70, 70, 0)]
        box = (10, 10, 60, 60)
        calls = []

        def predict(points, current_box):
            calls.append((points, current_box))
            return np.ones((100, 100), dtype=bool)

        coordinates = [[float(x), 80.0] for x in range(100)]
        _, points, returned_box = predict_background(
            SimpleNamespace(predict_prompt_mask=predict), coordinates, (original, box)
        )
        self.assertEqual(points[:2], original)
        self.assertEqual(len(points), 26)
        self.assertTrue(all(p.label == 0 and p.y == 80 for p in points[2:]))
        self.assertEqual(points[2].x, 0)
        self.assertEqual(points[-1].x, 99)
        self.assertEqual(returned_box, box)
        self.assertEqual(calls, [(points, box)])
        self.assertEqual(len(original), 2)

    def test_single_click_and_invalid_stroke(self):
        predictor = SimpleNamespace(predict_prompt_mask=lambda points, box: np.ones((20, 20), dtype=bool))
        _, points, _ = predict_background(predictor, [[5, 5]], ([], None))
        self.assertEqual(points, [SegmentationPoint(5, 5, 0)])
        with self.assertRaises(ValueError):
            predict_background(predictor, [], ([], None))

    def test_drag_can_cross_mask_and_background_and_cancel(self):
        scene = DIGITIZERScene()
        scene.image_width = scene.image_height = 100
        scene.set_ai_mode_enabled(True)
        scene.set_ai_tool("background")
        mask = np.zeros((100, 100), dtype=bool)
        mask[10:50, 10:50] = True
        scene._set_ai_display_mask(mask)
        received = []
        scene.aiBackgroundRequested.connect(received.append)

        def event(x, y, button=Qt.MouseButton.LeftButton):
            result = QGraphicsSceneMouseEvent()
            result.setScenePos(QPointF(x, y))
            result.setButton(button)
            return result

        scene._handle_ai_mouse_press(event(20, 20))
        scene._handle_ai_mouse_move(event(60, 60))
        path = scene._ai_background_item.path()
        self.assertEqual((path.elementAt(0).x, path.elementAt(0).y), (20, 20))
        self.assertEqual((path.elementAt(1).x, path.elementAt(1).y), (60, 60))
        scene._handle_ai_mouse_release(event(80, 80))
        self.assertEqual(received, [[[20, 20], [60, 60], [80, 80]]])
        self.assertIsNone(scene._ai_background_item)
        scene._handle_ai_mouse_press(event(70, 70))
        scene._handle_ai_mouse_press(event(70, 70, Qt.MouseButton.RightButton))
        self.assertIsNone(scene._ai_background_item)
        self.assertEqual(len(received), 1)

    def test_refinement_replaces_latest_mask_and_preserves_previous_parts(self):
        scene = DIGITIZERScene()
        scene.set_ai_mode_enabled(True)
        old = np.zeros((100, 100), dtype=bool)
        old[10:50, 10:50] = True
        old[70:90, 70:90] = True
        scene._set_ai_display_mask(old)
        base = np.zeros_like(old)
        base[70:90, 70:90] = True
        scene._ai_accumulated_mask = base
        context = (scene.ai_controller._image, scene._ai_current_mask)
        refined = np.zeros_like(old)
        refined[20:40, 20:40] = True
        prompts = [SegmentationPoint(15, 15, 0)]
        harness = SimpleNamespace(
            digitizer_scene=scene,
            _ai_background_context=context,
            _finish_ai_background_wait=lambda: None,
            statusBar=lambda: SimpleNamespace(showMessage=lambda *args: None),
        )
        MainWindow._ai_background_ready(harness, (refined, prompts, (10, 10, 50, 50)))
        self.assertFalse(scene._ai_current_mask[15, 15])
        self.assertTrue(scene._ai_current_mask[30, 30])
        self.assertTrue(scene._ai_current_mask[80, 80])
        self.assertEqual(scene.ai_controller.points, tuple(prompts))

    def test_toolbar_selects_background_brush(self):
        view = DIGITIZERView()
        received = []
        view.aiToolChanged.connect(received.append)
        view.ai_background_button.setEnabled(True)
        view.ai_background_button.click()
        self.assertEqual(received, ["background"])
