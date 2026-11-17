# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from pathlib import Path
from typing import Any

import numpy as np

from graphis.app.ki.backends import check_ultralytics_mobile_sam, check_ultralytics_sam2, check_ultralytics_sam3
from graphis.app.ki.base import BaseSegmenter, SegmentationPoint
from graphis.app.ki.devices import resolve_sam_device


class UltralyticsSAMSegmenter(BaseSegmenter):
    backend_id = "ultralytics_mobile_sam"
    _check_backend = staticmethod(check_ultralytics_mobile_sam)

    def __init__(
        self,
        model_path: str | Path | None = None,
        conf: float = 0.25,
        pre_mask_points_stride: int = 64,
        device: str = "auto",
    ):
        check = self._check_backend(model_path)
        if not check.available or check.model_path is None:
            raise RuntimeError(check.message)

        self.model_path = check.model_path
        self.conf = float(conf)
        self.pre_mask_points_stride = int(pre_mask_points_stride)
        self.device = resolve_sam_device(device)
        if self.device == "dml" and self.backend_id == "ultralytics_sam3":
            raise RuntimeError("SAM3's complex tensors are unsupported by DirectML. Use CPU or select SAM2/MobileSAM.")
        self._predictor = None
        self._image_bgr: np.ndarray | None = None
        self._image_shape: tuple[int, int] | None = None

    @property
    def is_ready(self) -> bool:
        return self._image_bgr is not None

    def load(self) -> None:
        predictor = self._ensure_predictor()
        if predictor.model is None:
            predictor.setup_model(verbose=False)

    def set_image(self, image: Any) -> None:
        self._image_bgr = self._image_to_bgr(image)
        self._image_shape = self._image_bgr.shape[:2]
        self._ensure_predictor().set_image(self._image_bgr)

    def predict_mask(self, points: list[SegmentationPoint]) -> np.ndarray:
        if self._image_bgr is None or self._image_shape is None:
            raise RuntimeError("No image has been set for the Ultralytics SAM backend.")
        if not points:
            return np.zeros(self._image_shape, dtype=bool)

        return self.predict_prompt_mask(points)

    def predict_prompt_mask(
        self,
        points: list[SegmentationPoint],
        box: tuple[float, float, float, float] | None = None,
    ) -> np.ndarray:
        if self._image_bgr is None or self._image_shape is None:
            raise RuntimeError("No image has been set for the Ultralytics SAM backend.")
        if not points and box is None:
            return np.zeros(self._image_shape, dtype=bool)

        point_coords = [[float(point.x), float(point.y)] for point in points]
        point_labels = [int(point.label) for point in points]
        bboxes = None if box is None else [self._clamped_box(box)]
        points_arg = None if not point_coords else [point_coords]
        labels_arg = None if not point_labels else [point_labels]
        results = self._ensure_predictor()(
            source=self._image_bgr,
            bboxes=bboxes,
            points=points_arg,
            labels=labels_arg,
            multimask_output=False,
            verbose=False,
        )
        return self._first_result_mask(results)

    def predict_box_mask(self, box: tuple[float, float, float, float]) -> np.ndarray:
        if self._image_bgr is None or self._image_shape is None:
            raise RuntimeError("No image has been set for the Ultralytics SAM backend.")

        bbox = self._clamped_box(box)
        if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
            return np.zeros(self._image_shape, dtype=bool)

        results = self._ensure_predictor()(
            source=self._image_bgr,
            bboxes=[bbox],
            multimask_output=False,
            verbose=False,
        )
        return self._first_result_mask(results)

    def _clamped_box(self, box: tuple[float, float, float, float]) -> list[float]:
        if self._image_shape is None:
            return [0.0, 0.0, 0.0, 0.0]

        x1, y1, x2, y2 = box
        return [
            max(0.0, min(float(x1), float(x2))),
            max(0.0, min(float(y1), float(y2))),
            min(float(self._image_shape[1] - 1), max(float(x1), float(x2))),
            min(float(self._image_shape[0] - 1), max(float(y1), float(y2))),
        ]

    def predict_pre_masks(self) -> np.ndarray:
        if self._image_bgr is None or self._image_shape is None:
            raise RuntimeError("No image has been set for the Ultralytics SAM backend.")

        results = self._ensure_predictor()(
            source=self._image_bgr,
            points_stride=self.pre_mask_points_stride,
            points_batch_size=64,
            conf_thres=0.88,
            stability_score_thresh=0.95,
            crop_n_layers=0,
        )
        if not results:
            return np.zeros((0, *self._image_shape), dtype=bool)

        masks = getattr(results[0], "masks", None)
        if masks is None or getattr(masks, "data", None) is None:
            return np.zeros((0, *self._image_shape), dtype=bool)

        mask_data = masks.data.detach().cpu().numpy()
        if mask_data.ndim == 2:
            return mask_data[None].astype(bool)
        if mask_data.ndim == 3:
            return mask_data.astype(bool)
        return np.zeros((0, *self._image_shape), dtype=bool)

    def _first_result_mask(self, results) -> np.ndarray:
        if self._image_shape is None or not results:
            return np.zeros((0, 0), dtype=bool)

        masks = getattr(results[0], "masks", None)
        if masks is None or getattr(masks, "data", None) is None:
            return np.zeros(self._image_shape, dtype=bool)

        mask_data = masks.data.detach().cpu().numpy()
        if mask_data.ndim == 3 and mask_data.shape[0] > 0:
            return mask_data[0].astype(bool)
        if mask_data.ndim == 2:
            return mask_data.astype(bool)
        return np.zeros(self._image_shape, dtype=bool)

    def reset(self) -> None:
        if self._predictor is not None:
            self._predictor.prompts = {}

    def _ensure_predictor(self):
        if self._predictor is None:
            overrides = {
                "conf": self.conf,
                "task": "segment",
                "mode": "predict",
                "imgsz": 1024,
                "model": str(self.model_path),
                "device": "cpu" if self.device == "dml" else self.device,
                "save": False,
                "verbose": False,
            }
            overrides.update(self._predictor_overrides())
            predictor_class = self._predictor_class()
            if self.device == "dml":
                from graphis.app.ki.directml_sam import directml_predictor_class

                predictor_class = directml_predictor_class(predictor_class)
            self._predictor = predictor_class(overrides=overrides)
        return self._predictor

    def _predictor_overrides(self) -> dict[str, Any]:
        return {}

    def _predictor_class(self):
        from ultralytics.models.sam import Predictor as SAMPredictor

        return SAMPredictor

    def _image_to_bgr(self, image: Any) -> np.ndarray:
        if isinstance(image, np.ndarray):
            if image.ndim != 3 or image.shape[2] < 3:
                raise ValueError("Expected an HWC RGB/BGR image array.")
            return np.ascontiguousarray(image[:, :, :3])

        if isinstance(image, (str, Path)):
            import cv2

            loaded = cv2.imread(str(image), cv2.IMREAD_COLOR)
            if loaded is None:
                raise ValueError(f"Could not read image: {image}")
            return np.ascontiguousarray(loaded)

        try:
            from PIL import Image
        except ImportError:
            Image = None

        if Image is not None and isinstance(image, Image.Image):
            rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
            return np.ascontiguousarray(rgb[:, :, ::-1])

        try:
            from PySide6.QtGui import QImage
        except ImportError:
            QImage = None

        if QImage is not None and isinstance(image, QImage):
            converted = image.convertToFormat(QImage.Format.Format_RGB888)
            width = converted.width()
            height = converted.height()
            bytes_per_line = converted.bytesPerLine()
            buffer = converted.constBits()
            padded = np.frombuffer(buffer, dtype=np.uint8).reshape((height, bytes_per_line))
            rgb = padded[:, : width * 3].reshape((height, width, 3)).copy()
            return np.ascontiguousarray(rgb[:, :, ::-1])

        raise TypeError(f"Unsupported image type for Ultralytics SAM backend: {type(image)!r}")


class UltralyticsSAM2Segmenter(UltralyticsSAMSegmenter):
    backend_id = "ultralytics_sam2"
    _check_backend = staticmethod(check_ultralytics_sam2)

    def _predictor_class(self):
        from ultralytics.models.sam.predict import SAM2Predictor

        return SAM2Predictor


class UltralyticsSAM3Segmenter(UltralyticsSAMSegmenter):
    backend_id = "ultralytics_sam3"
    _check_backend = staticmethod(check_ultralytics_sam3)

    def _predictor_overrides(self) -> dict[str, Any]:
        return {"compile": None, "imgsz": 1036}

    def _predictor_class(self):
        from ultralytics.models.sam import SAM3Predictor

        return SAM3Predictor
