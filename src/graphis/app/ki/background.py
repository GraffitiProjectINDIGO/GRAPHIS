"""Use background brush strokes as negative segmentation prompts."""

import numpy as np

from graphis.app.ki.base import SegmentationPoint


def predict_background(segmenter, coordinates, prompt_state):
    """Sample an open stroke by distance, retaining the current foreground and box prompts."""
    points, box = prompt_state
    stroke = np.asarray(coordinates, dtype=float)
    if stroke.ndim != 2 or stroke.shape[1] != 2 or len(stroke) == 0 or not np.isfinite(stroke).all():
        raise ValueError("Paint a stroke over the background.")
    distances = np.concatenate(([0.0], np.cumsum(np.linalg.norm(np.diff(stroke, axis=0), axis=1))))
    count = min(24, max(len(stroke), int(np.ceil(distances[-1] / 16)) + 1))
    samples = np.linspace(0, distances[-1], count)
    negatives = [
        SegmentationPoint(float(x), float(y), 0)
        for x, y in zip(
            np.interp(samples, distances, stroke[:, 0]), np.interp(samples, distances, stroke[:, 1]), strict=True
        )
    ]
    points = list(points) + negatives
    return segmenter.predict_prompt_mask(points, box), points, box
