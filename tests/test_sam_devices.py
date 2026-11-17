import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np
from PySide6.QtWidgets import QApplication

from graphis.app.ki.base import SegmentationPoint
from graphis.app.ki.controller import AISegmentationController
from graphis.app.ki.device_fallback import DeviceFallbackSegmenter
from graphis.app.ki.devices import resolve_sam_device, sam_device_options, torch_device_options
from graphis.app.ki.factory import create_segmenter
from graphis.app.var_classes import Instructions
from graphis.main import MainWindow


class FakeSegmenter:
    backend_id = "test_sam"
    model_path = Path("model.pt")

    def __init__(self, device):
        self.device = device
        self.image = None
        self.prompts = []
        self.fail_image = False
        self.fail_prediction = False

    @property
    def is_ready(self):
        return self.image is not None

    def set_image(self, image):
        if self.fail_image:
            raise RuntimeError("Unsupported GPU image operation")
        self.image = image

    def predict_prompt_mask(self, points, box=None):
        if self.fail_prediction:
            raise RuntimeError("Unsupported GPU mask operation")
        self.prompts.append((points, box))
        return np.ones(self.image.shape[:2], dtype=bool)

    def reset(self):
        self.prompts.clear()


class InitializationHarness:
    _ensure_ai_segmenter = MainWindow._ensure_ai_segmenter
    _finish_ai_initialization = MainWindow._finish_ai_initialization
    _ai_segmenter_ready = MainWindow._ai_segmenter_ready
    _ai_segmenter_failed = MainWindow._ai_segmenter_failed
    _activate_ai_segmenter = MainWindow._activate_ai_segmenter
    _ai_active_or_requested = MainWindow._ai_active_or_requested
    _prepare_ai_for_current_image = MainWindow._prepare_ai_for_current_image
    _release_ai_segmenter = MainWindow._release_ai_segmenter
    _reload_ai_model = MainWindow._reload_ai_model
    _set_ai_segmentation_mode = MainWindow._set_ai_segmentation_mode

    def __init__(self):
        self.ki_backend_id = "test_sam"
        self.ki_model_path = None
        self.ki_device = "dml"
        self._ki_backend_user_selected = True
        self._ai_initialization_request = None
        self._ai_initialization_worker = None
        self._ai_initialization_activate = False
        self._ai_reload_pending = False
        self._ai_prepared_image = None
        self._ai_keep_model_on_image_change = False
        controller = AISegmentationController(FakeSegmenter("dml"))
        controller.set_image(np.zeros((8, 8, 3), dtype=np.uint8))
        self.digitizer_scene = SimpleNamespace(
            ai_controller=controller, set_ai_mode_enabled=Mock(), instruction_active=False, ai_mode_enabled=False,
            polygon_brush_enabled=False, current_instruction=Instructions.No_Instruction,
            reset_ai_segmentation=Mock(), set_ai_preclassification_visible=Mock(), ai_background_busy=False,
        )
        self.view_digizizer = SimpleNamespace(
            set_ai_initializing=Mock(), set_ai_mode_checked=Mock(), set_ai_backend_options=Mock(),
            set_ai_preclassification_checked=Mock(),
        )
        self._sync_ai_device_combo = Mock()
        self._scan_ai_devices = Mock()
        self.thread_pool = SimpleNamespace(start=Mock())
        self.start_waiting = Mock()
        self.stop_waiting = Mock()
        self._clear_geometry_operation = Mock()
        self._sync_geometry_action_availability = Mock()


class SAMDeviceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_directml_is_explicit_and_sam3_option_is_hidden(self):
        with patch("graphis.app.ki.devices.torch_directml_available", return_value=True):
            self.assertEqual(resolve_sam_device("directml"), "dml")
        with patch("graphis.app.ki.devices.torch_directml_available", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "no DirectML device"):
                resolve_sam_device("dml")
        with patch("graphis.app.ki.devices.torch_device_options", return_value=[
            ("auto", "Auto"), ("cpu", "CPU"), ("dml", "DirectML (experimental)")
        ]):
            self.assertIn(("dml", "DirectML (experimental)"), sam_device_options("texturesam"))
            self.assertEqual(sam_device_options("ultralytics_sam3"), [("auto", "Auto"), ("cpu", "CPU")])
        with self.assertRaises(ValueError):
            resolve_sam_device("invalid-device")

    def test_image_failure_falls_back_once_and_preserves_image(self):
        created = []

        def factory(device):
            segmenter = FakeSegmenter(device)
            segmenter.fail_image = device == "dml"
            created.append(segmenter)
            return segmenter

        segmenter = DeviceFallbackSegmenter(factory)
        image = np.zeros((12, 16, 3), dtype=np.uint8)
        segmenter.set_image(image)
        self.assertEqual(segmenter.device, "cpu")
        self.assertIs(created[-1].image, image)
        self.assertTrue(segmenter.is_ready)
        self.assertIn("GPU image", segmenter.fallback_reason)
        segmenter.set_image(image)
        self.assertEqual([s.device for s in created], ["dml", "cpu"])

    def test_prediction_failure_preserves_combined_box_and_point_prompts(self):
        created = []

        def factory(device):
            segmenter = FakeSegmenter(device)
            segmenter.fail_prediction = device == "dml"
            created.append(segmenter)
            return segmenter

        segmenter = DeviceFallbackSegmenter(factory)
        image = np.zeros((12, 16, 3), dtype=np.uint8)
        points = [SegmentationPoint(5, 5, 1), SegmentationPoint(0, 0, 0)]
        box = (2, 2, 10, 10)
        segmenter.set_image(image)
        mask = segmenter.predict_prompt_mask(points, box)
        self.assertEqual(mask.shape, (12, 16))
        self.assertEqual(created[-1].prompts, [(points, box)])
        self.assertIs(created[-1].image, image)
        created[-1].fail_prediction = True
        with self.assertRaisesRegex(RuntimeError, "mask operation"):
            segmenter.predict_prompt_mask(points, box)
        self.assertEqual(len(created), 2)

    def test_sam3_never_attempts_unsupported_gpu_complex_tensors(self):
        with patch(
            "graphis.app.ki.factory._create_segmenter", side_effect=lambda _, __, device: FakeSegmenter(device)
        ) as make:
            segmenter = create_segmenter("ultralytics_sam3", device="dml")
        make.assert_called_once_with("ultralytics_sam3", None, "cpu")
        self.assertEqual(segmenter.device, "cpu")
        self.assertIn("complex tensors", segmenter.fallback_reason)

    def test_preparation_runs_in_worker_and_commits_only_for_current_image(self):
        harness = InitializationHarness()
        controller = harness.digitizer_scene.ai_controller
        prepared = FakeSegmenter("dml")
        with patch("graphis.app.ki.factory.prepare_segmenter", return_value=prepared) as prepare:
            harness._ensure_ai_segmenter()
            prepare.assert_not_called()
            self.assertIsNone(controller.segmenter)
            worker = harness.thread_pool.start.call_args.args[0]
            worker.run()
        self.assertIs(controller.segmenter, prepared)
        harness.digitizer_scene.set_ai_mode_enabled.assert_called_with(True)
        harness.view_digizizer.set_ai_mode_checked.assert_called_with(True)
        self.assertIsNone(harness._ai_initialization_request)

        # The model is kept when the image changes during encoding; the new image is encoded next.
        harness = InitializationHarness()
        controller = harness.digitizer_scene.ai_controller
        with patch("graphis.app.ki.factory.prepare_segmenter", return_value=prepared) as prepare:
            harness._ensure_ai_segmenter()
            new_image = np.zeros((4, 4, 3), dtype=np.uint8)
            controller.set_image(new_image)
            harness.thread_pool.start.call_args.args[0].run()
            self.assertEqual(harness.thread_pool.start.call_count, 2)
            self.assertIsNone(controller.segmenter)
            self.assertNotIn(unittest.mock.call(True), harness.digitizer_scene.set_ai_mode_enabled.call_args_list)
            harness.thread_pool.start.call_args.args[0].run()
        self.assertIs(prepare.call_args.args[4], prepared)
        self.assertEqual(prepare.call_args.args[3].shape, new_image.shape)
        self.assertIs(controller.segmenter, prepared)
        harness.digitizer_scene.set_ai_mode_enabled.assert_called_with(True)

    def test_active_ai_stays_active_on_image_change_without_reloading_the_model(self):
        harness = InitializationHarness()
        controller = harness.digitizer_scene.ai_controller
        model = FakeSegmenter("cpu")
        with patch("graphis.app.ki.factory.prepare_segmenter", return_value=model) as prepare:
            harness._ensure_ai_segmenter(activate=True)
            harness.thread_pool.start.call_args.args[0].run()
            harness.digitizer_scene.ai_mode_enabled = True
            self.assertTrue(harness._ai_active_or_requested())

            # The next image is shown; the loader resets the AI controls while keeping the model.
            harness._ai_keep_model_on_image_change = True
            harness._set_ai_segmentation_mode(False)
            harness._ai_keep_model_on_image_change = False
            harness.digitizer_scene.ai_mode_enabled = False
            self.assertIs(controller.segmenter, model)
            new_image = np.ones((6, 6, 3), dtype=np.uint8)
            controller.set_image(new_image)
            harness._prepare_ai_for_current_image(activate=True)
            harness.view_digizizer.set_ai_mode_checked.assert_called_with(True)
            harness.thread_pool.start.call_args.args[0].run()
        self.assertIs(prepare.call_args.args[4], model)
        self.assertEqual(prepare.call_args.args[3].shape, new_image.shape)
        self.assertIs(controller.segmenter, model)
        harness.digitizer_scene.set_ai_mode_enabled.assert_called_with(True)

    def test_nothing_is_loaded_while_ai_is_off(self):
        harness = InitializationHarness()
        harness.digitizer_scene.ai_controller.set_segmenter(None)
        with patch("graphis.app.ki.factory.prepare_segmenter") as prepare:
            harness._prepare_ai_for_current_image(activate=False)  # new image, AI off
            harness.ki_backend_id = "other_sam"
            harness._reload_ai_model()  # model changed in the toolbox, AI off
        harness.thread_pool.start.assert_not_called()
        prepare.assert_not_called()
        harness._scan_ai_devices.assert_not_called()
        harness.start_waiting.assert_not_called()

    def test_switching_ai_off_removes_masks_and_releases_the_model(self):
        harness = InitializationHarness()
        controller = harness.digitizer_scene.ai_controller
        with patch("graphis.app.ki.factory.prepare_segmenter", return_value=FakeSegmenter("cpu")):
            harness._ensure_ai_segmenter(activate=True)
            harness.thread_pool.start.call_args.args[0].run()
        self.assertIsNotNone(controller.segmenter)
        with patch("graphis.app.ki.devices.release_ai_memory") as release:
            harness._set_ai_segmentation_mode(False)
        self.assertIsNone(controller.segmenter)
        self.assertIsNone(harness._ai_prepared_image)
        release.assert_called_once()
        harness.digitizer_scene.reset_ai_segmentation.assert_called_with(reload_backend=False)
        harness.digitizer_scene.set_ai_preclassification_visible.assert_called_with(False)
        harness.view_digizizer.set_ai_preclassification_checked.assert_called_with(False)
        harness.digitizer_scene.set_ai_mode_enabled.assert_called_with(False)

    def test_prepared_image_activates_without_reencoding(self):
        harness = InitializationHarness()
        prepared = FakeSegmenter("cpu")
        with patch("graphis.app.ki.factory.prepare_segmenter", return_value=prepared) as prepare:
            harness._ensure_ai_segmenter(activate=True)
            harness.thread_pool.start.call_args.args[0].run()
            harness.digitizer_scene.set_ai_mode_enabled.reset_mock()
            harness._ensure_ai_segmenter(activate=True)
        prepare.assert_called_once()
        harness.digitizer_scene.set_ai_mode_enabled.assert_called_with(True)
        harness.view_digizizer.set_ai_mode_checked.assert_called_with(True)

    def test_model_change_while_loading_discards_old_model_and_loads_new_one(self):
        harness = InitializationHarness()
        old_model = FakeSegmenter("cpu")
        with patch("graphis.app.ki.factory.prepare_segmenter", return_value=old_model) as prepare, \
                patch("graphis.app.ki.devices.release_ai_memory") as release:
            harness._ensure_ai_segmenter(activate=True)
            harness.ki_backend_id = "other_sam"
            harness._reload_ai_model()
            self.assertTrue(harness._ai_reload_pending)
            harness.thread_pool.start.call_args.args[0].run()
            self.assertIsNone(harness.digitizer_scene.ai_controller.segmenter)
            release.assert_called()
            self.assertEqual(prepare.call_count, 1)
            harness.thread_pool.start.call_args.args[0].run()
        self.assertEqual(prepare.call_args.args[0], "other_sam")
        self.assertIsNone(prepare.call_args.args[4])
        self.assertIs(harness.digitizer_scene.ai_controller.segmenter, old_model)

    def test_switching_off_while_loading_discards_the_model(self):
        harness = InitializationHarness()
        with patch("graphis.app.ki.factory.prepare_segmenter", return_value=FakeSegmenter("cpu")), \
                patch("graphis.app.ki.devices.release_ai_memory") as release:
            harness._ensure_ai_segmenter()
            harness._set_ai_segmentation_mode(False)  # user switches AI off while it loads
            self.assertFalse(harness._ai_initialization_activate)
            harness.thread_pool.start.call_args.args[0].run()
        self.assertIsNone(harness.digitizer_scene.ai_controller.segmenter)
        release.assert_called_once()
        self.assertNotIn(unittest.mock.call(True), harness.digitizer_scene.set_ai_mode_enabled.call_args_list)

    def test_initialization_does_not_interrupt_an_operation_started_while_waiting(self):
        harness = InitializationHarness()
        prepared = FakeSegmenter("dml")
        with patch("graphis.app.ki.factory.prepare_segmenter", return_value=prepared):
            harness._ensure_ai_segmenter()
            harness.digitizer_scene.instruction_active = True
            harness.thread_pool.start.call_args.args[0].run()
        harness._clear_geometry_operation.assert_not_called()
        harness.view_digizizer.set_ai_mode_checked.assert_called_with(False)

    def test_failed_initialization_restores_controls(self):
        harness = InitializationHarness()
        with (
            patch("graphis.app.ki.factory.prepare_segmenter", side_effect=RuntimeError("Model failed")),
            patch("graphis.main.message_box.warning") as warning,
        ):
            harness._ensure_ai_segmenter()
            harness.thread_pool.start.call_args.args[0].run()
        self.assertIsNone(harness._ai_initialization_request)
        self.assertIsNone(harness.digitizer_scene.ai_controller.segmenter)
        harness.view_digizizer.set_ai_initializing.assert_called_with(False)
        harness.view_digizizer.set_ai_mode_checked.assert_called_with(False)
        self.assertEqual(warning.call_args.args[2], "Model failed")

    def test_gpu_failure_at_creation_falls_back_to_cpu(self):
        def factory(device):
            if device != "cpu":
                raise RuntimeError("CUDA driver too old")
            return FakeSegmenter(device)

        segmenter = DeviceFallbackSegmenter(factory, device="cuda")
        self.assertEqual(segmenter.device, "cpu")
        self.assertIn("driver", segmenter.fallback_reason)

    def test_cuda_and_rocm_and_mps_are_detected(self):
        cuda = SimpleNamespace(is_available=lambda: True, device_count=lambda: 1, get_device_name=lambda i: "GPU X")
        mps = SimpleNamespace(is_available=lambda: False)
        nvidia = SimpleNamespace(cuda=cuda, version=SimpleNamespace(hip=None), backends=SimpleNamespace(mps=mps))
        rocm = SimpleNamespace(cuda=cuda, version=SimpleNamespace(hip="6.4"), backends=SimpleNamespace(mps=mps))
        apple = SimpleNamespace(
            cuda=SimpleNamespace(is_available=lambda: False), version=SimpleNamespace(hip=None),
            backends=SimpleNamespace(mps=SimpleNamespace(is_available=lambda: True)),
        )
        with patch("graphis.app.ki.devices.torch_directml_available", return_value=False):
            with patch("graphis.app.ki.devices._import_torch", return_value=nvidia):
                self.assertIn(("cuda:0", "NVIDIA CUDA 0: GPU X"), torch_device_options())
                self.assertEqual(resolve_sam_device("auto"), "cuda")
            with patch("graphis.app.ki.devices._import_torch", return_value=rocm):
                self.assertIn(("cuda:0", "AMD ROCm 0: GPU X"), torch_device_options())
            with patch("graphis.app.ki.devices._import_torch", return_value=apple):
                self.assertIn(("mps", "Apple GPU (MPS)"), torch_device_options())
                self.assertEqual(resolve_sam_device("auto"), "mps")
            with patch("graphis.app.ki.devices._import_torch", return_value=None):
                self.assertEqual(torch_device_options(), [("auto", "Auto"), ("cpu", "CPU")])
                self.assertEqual(resolve_sam_device("auto"), "cpu")

    def test_gpu_requests_are_wrapped_with_cpu_fallback(self):
        with patch(
            "graphis.app.ki.factory._create_segmenter", side_effect=lambda _, __, device: FakeSegmenter(device)
        ):
            self.assertIsInstance(create_segmenter("ultralytics_sam2", device="cuda:0"), DeviceFallbackSegmenter)
            self.assertNotIsInstance(create_segmenter("ultralytics_sam2", device="cpu"), DeviceFallbackSegmenter)


if __name__ == "__main__":
    unittest.main()
