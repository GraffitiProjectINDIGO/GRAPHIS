# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import sys
from pathlib import Path
from typing import Any

import numpy as np

from graphis.app.ki.backends import check_texturesam, texturesam_repo_candidates
from graphis.app.ki.base import BaseSegmenter, SegmentationPoint
from graphis.app.ki.devices import resolve_sam_device, torch_directml_device


class TextureSAMSegmenter(BaseSegmenter):
    backend_id = "texturesam"

    def __init__(
        self,
        model_path: str | Path | None = None,
        device: str = "auto",
        multimask_output: bool = False,
    ):
        check = check_texturesam(model_path)
        if not check.available or check.model_path is None:
            raise RuntimeError(check.message)

        self.model_path = check.model_path
        self.device = resolve_sam_device(device)
        self.multimask_output = bool(multimask_output)
        self._repo_path = self._resolve_repo_path()
        self._predictor = None
        self._image_rgb: np.ndarray | None = None
        self._image_shape: tuple[int, int] | None = None

    @property
    def is_ready(self) -> bool:
        return self._image_rgb is not None

    def load(self) -> None:
        self._ensure_predictor()

    def set_image(self, image: Any) -> None:
        self._image_rgb = self._image_to_rgb(image)
        self._image_shape = self._image_rgb.shape[:2]
        self._ensure_predictor().set_image(self._image_rgb)

    def predict_mask(self, points: list[SegmentationPoint]) -> np.ndarray:
        return self.predict_prompt_mask(points)

    def predict_prompt_mask(
        self,
        points: list[SegmentationPoint],
        box: tuple[float, float, float, float] | None = None,
    ) -> np.ndarray:
        if self._image_rgb is None or self._image_shape is None:
            raise RuntimeError("No image has been set for the TextureSAM backend.")
        if not points and box is None:
            return np.zeros(self._image_shape, dtype=bool)

        point_coords = None
        point_labels = None
        if points:
            point_coords = np.array([[float(point.x), float(point.y)] for point in points], dtype=np.float32)
            point_labels = np.array([int(point.label) for point in points], dtype=np.int32)

        box_arg = None if box is None else np.array(self._clamped_box(box), dtype=np.float32)
        masks, scores, _logits = self._ensure_predictor().predict(
            point_coords=point_coords,
            point_labels=point_labels,
            box=box_arg,
            multimask_output=self.multimask_output,
        )
        return self._best_mask(masks, scores)

    def predict_box_mask(self, box: tuple[float, float, float, float]) -> np.ndarray:
        return self.predict_prompt_mask([], box)

    def reset(self) -> None:
        return None

    def _ensure_predictor(self):
        if self._predictor is not None:
            return self._predictor

        repo_package_root = self._repo_path / "sam2"
        if repo_package_root.exists() and str(repo_package_root) not in sys.path:
            sys.path.insert(0, str(repo_package_root))

        try:
            import torch
            from sam2.build_sam import build_sam2
            from sam2.sam2_image_predictor import SAM2ImagePredictor
        except ImportError as err:
            raise RuntimeError(
                "Could not import TextureSAM/SAM2. Install it with pip install -e '.[texturesam]' and place the "
                "TextureSAM repository folder in the segmentation model folder (AI configuration)."
            ) from err

        model_cfg = self._model_config_name()
        model = build_sam2(model_cfg, str(self.model_path), device="cpu" if self.device == "dml" else self.device)
        if self.device == "dml":
            from graphis.app.ki.directml_sam import adapt_prompt_encoders

            device = torch_directml_device()
            model = model.train().float().to(device)
            adapt_prompt_encoders(model, device)
        model.eval()
        self._torch = torch
        self._predictor = SAM2ImagePredictor(model)
        return self._predictor

    def _model_config_name(self) -> str:
        config_path = self._repo_path / "sam2" / "sam2" / "configs" / "sam2.1" / "sam2.1_hiera_s.yaml"
        if not config_path.exists():
            raise RuntimeError(
                "TextureSAM config not found. Expected sam2/sam2/configs/sam2.1/sam2.1_hiera_s.yaml "
                "inside the TextureSAM repository."
            )
        return "configs/sam2.1/sam2.1_hiera_s.yaml"

    def _resolve_repo_path(self) -> Path:
        for path in texturesam_repo_candidates():
            if (path / "README.md").exists() and (path / "sam2").exists():
                return path
        raise RuntimeError(
            "TextureSAM repository folder 'TextureSAM' not found in the segmentation model folder. "
            "Select the folder in the AI configuration (see README, AI models)."
        )

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

    def _best_mask(self, masks, scores) -> np.ndarray:
        if self._image_shape is None:
            return np.zeros((0, 0), dtype=bool)

        mask_data = np.asarray(masks)
        if mask_data.ndim == 2:
            return mask_data.astype(bool)
        if mask_data.ndim != 3 or mask_data.shape[0] == 0:
            return np.zeros(self._image_shape, dtype=bool)

        if scores is None:
            return mask_data[0].astype(bool)
        score_data = np.asarray(scores).reshape(-1)
        if score_data.size == 0:
            return mask_data[0].astype(bool)
        return mask_data[int(np.argmax(score_data))].astype(bool)

    def _image_to_rgb(self, image: Any) -> np.ndarray:
        if isinstance(image, np.ndarray):
            if image.ndim != 3 or image.shape[2] < 3:
                raise ValueError("Expected an HWC RGB/BGR image array.")
            return np.ascontiguousarray(image[:, :, :3])

        if isinstance(image, (str, Path)):
            import cv2

            loaded = cv2.imread(str(image), cv2.IMREAD_COLOR)
            if loaded is None:
                raise ValueError(f"Could not read image: {image}")
            return np.ascontiguousarray(loaded[:, :, ::-1])

        try:
            from PIL import Image
        except ImportError:
            Image = None

        if Image is not None and isinstance(image, Image.Image):
            return np.ascontiguousarray(np.asarray(image.convert("RGB"), dtype=np.uint8))

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
            return np.ascontiguousarray(padded[:, : width * 3].reshape((height, width, 3)).copy())

        raise TypeError(f"Unsupported image type for TextureSAM backend: {type(image)!r}")
