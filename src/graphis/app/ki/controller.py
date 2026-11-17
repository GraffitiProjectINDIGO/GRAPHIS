# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import logging
from typing import Any

import numpy as np

from graphis.app.ki.base import BaseSegmenter, SegmentationPoint

logger = logging.getLogger(__name__)


class AISegmentationController:
    def __init__(self, segmenter: BaseSegmenter | None = None):
        self._segmenter = segmenter
        self._points: list[SegmentationPoint] = []
        self._box: tuple[float, float, float, float] | None = None
        self._image: Any = None

    @property
    def segmenter(self) -> BaseSegmenter | None:
        return self._segmenter

    @property
    def image(self) -> Any:
        return self._image

    @property
    def points(self) -> tuple[SegmentationPoint, ...]:
        return tuple(self._points)

    def set_segmenter(self, segmenter: BaseSegmenter | None) -> None:
        self._segmenter = segmenter

    def set_image(self, image: Any) -> None:
        self._image = image
        self.reset()

    def prepare_current_image(self) -> None:
        if self._image is not None and self._segmenter is not None:
            self._segmenter.set_image(self._image)

    def prompt_state(self) -> tuple[list[SegmentationPoint], tuple[float, float, float, float] | None]:
        return list(self._points), self._box

    def restore_prompt_state(
        self,
        state: tuple[list[SegmentationPoint], tuple[float, float, float, float] | None],
    ) -> None:
        points, box = state
        self._points = list(points)
        self._box = box

    def add_point(self, x: float, y: float, label: int) -> np.ndarray | None:
        self._points.append(SegmentationPoint(float(x), float(y), int(label)))
        return self.predict()

    def add_points(self, points: list[tuple[float, float]], label: int) -> np.ndarray | None:
        self._points.extend(SegmentationPoint(float(x), float(y), int(label)) for x, y in points)
        return self.predict()

    def predict(self) -> np.ndarray | None:
        if self._segmenter is None:
            return None
        if (not self._points and self._box is None) or not self._segmenter.is_ready:
            return None
        return self._segmenter.predict_prompt_mask(list(self._points), self._box)

    def predict_pre_masks(self) -> np.ndarray | None:
        if self._segmenter is None or not self._segmenter.is_ready:
            return None
        return self._segmenter.predict_pre_masks()

    def predict_box(self, box: tuple[float, float, float, float]) -> np.ndarray | None:
        if self._segmenter is None or not self._segmenter.is_ready:
            return None
        previous_state = self.prompt_state()
        self._points = []
        self._box = tuple(float(value) for value in box)
        try:
            mask = self.predict()
        except Exception:
            self.restore_prompt_state(previous_state)
            raise
        if mask is None:
            self.restore_prompt_state(previous_state)
        return mask

    def reset(self, reload_image: bool = False) -> None:
        self._points.clear()
        self._box = None
        if self._segmenter is not None:
            self._segmenter.reset()
            if reload_image and self._image is not None:
                self._segmenter.set_image(self._image)
