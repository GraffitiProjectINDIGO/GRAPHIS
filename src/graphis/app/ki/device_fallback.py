"""Retry failed GPU operations on CPU, retaining the image and prompts."""

import logging
from threading import RLock

from graphis.app.ki.base import BaseSegmenter

logger = logging.getLogger(__name__)


class DeviceFallbackSegmenter(BaseSegmenter):
    def __init__(self, factory, unsupported_reason=None, device="dml"):
        self._factory = factory
        self._image = None
        self._lock = RLock()
        self.fallback_reason = unsupported_reason
        if unsupported_reason:
            self._segmenter = factory("cpu")
            logger.warning("%s Using CPU for %s.", unsupported_reason, self._segmenter.backend_id)
        else:
            try:
                self._segmenter = factory(device)
            except RuntimeError as err:
                self.fallback_reason = str(err)
                logger.warning("Could not use %s for AI segmentation: %s. Using CPU.", device, err)
                self._segmenter = factory("cpu")
        self.backend_id = self._segmenter.backend_id

    @property
    def device(self):
        return self._segmenter.device

    @property
    def model_path(self):
        return self._segmenter.model_path

    @property
    def is_ready(self):
        return self._segmenter.is_ready

    def _call(self, method, *args):
        with self._lock:
            try:
                return getattr(self._segmenter, method)(*args)
            except (RuntimeError, NotImplementedError) as err:
                if self.device == "cpu":
                    raise
                self.fallback_reason = str(err)
                logger.warning("GPU device %s failed for %s: %s. Retrying on CPU.", self.device, self.backend_id, err)
                self._segmenter = self._factory("cpu")
                if self._image is not None:
                    self._segmenter.set_image(self._image)
                if method == "set_image":
                    return None
                return getattr(self._segmenter, method)(*args)

    def load(self):
        return self._call("load")

    def set_image(self, image):
        with self._lock:
            self._image = image
            return self._call("set_image", image)

    def predict_mask(self, points):
        return self._call("predict_mask", points)

    def predict_prompt_mask(self, points, box=None):
        return self._call("predict_prompt_mask", points, box)

    def predict_box_mask(self, box):
        return self._call("predict_box_mask", box)

    def predict_pre_masks(self):
        return self._call("predict_pre_masks")

    def reset(self):
        return self._call("reset")
