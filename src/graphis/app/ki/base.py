# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class SegmentationPoint:
    x: float
    y: float
    label: int


class BaseSegmenter(ABC):
    def load(self) -> None:
        """Load model weights before an image is set, so later image changes only encode."""
        return None

    @abstractmethod
    def set_image(self, image: Any) -> None:
        """Prepare an image for later prompt-based mask prediction."""

    @abstractmethod
    def predict_mask(self, points: list[SegmentationPoint]) -> np.ndarray:
        """Return a boolean mask for the current image and prompt points."""

    def predict_prompt_mask(
        self,
        points: list[SegmentationPoint],
        box: tuple[float, float, float, float] | None = None,
    ) -> np.ndarray:
        """Return a boolean mask for combined point and optional box prompts."""
        if box is None:
            return self.predict_mask(points)
        if not points:
            return self.predict_box_mask(box)
        raise NotImplementedError("This backend does not support combined box and point prompts.")

    def predict_pre_masks(self) -> np.ndarray:
        """Return automatic whole-image mask proposals as N x H x W boolean masks."""
        return np.zeros((0, 0, 0), dtype=bool)

    def predict_box_mask(self, box: tuple[float, float, float, float]) -> np.ndarray:
        """Return a boolean mask for a box prompt in x1, y1, x2, y2 image coordinates."""
        raise NotImplementedError("This backend does not support box prompts.")

    def reset(self) -> None:
        """Clear backend state that belongs to the current interactive object."""
        return None

    @property
    def is_ready(self) -> bool:
        return True
