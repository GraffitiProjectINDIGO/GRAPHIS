# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import logging
from pathlib import Path

from graphis.app.ki.backends import (
    BackendCheck,
    check_texturesam,
    check_ultralytics_mobile_sam,
    check_ultralytics_sam2,
    check_ultralytics_sam3,
)
from graphis.app.ki.base import BaseSegmenter
from graphis.app.ki.device_fallback import DeviceFallbackSegmenter
from graphis.app.ki.devices import is_gpu_device
from graphis.app.ki.texturesam import TextureSAMSegmenter
from graphis.app.ki.ultralytics_sam import UltralyticsSAM2Segmenter, UltralyticsSAM3Segmenter, UltralyticsSAMSegmenter

logger = logging.getLogger(__name__)


def check_backend(backend_id: str, model_path: str | Path | None = None) -> BackendCheck:
    if backend_id == "ultralytics_mobile_sam":
        return check_ultralytics_mobile_sam(model_path)
    if backend_id == "ultralytics_sam2":
        return check_ultralytics_sam2(model_path)
    if backend_id == "ultralytics_sam3":
        return check_ultralytics_sam3(model_path)
    if backend_id == "texturesam":
        return check_texturesam(model_path)
    if backend_id == "disabled":
        return BackendCheck("disabled", True, "AI segmentation disabled.")
    return BackendCheck(backend_id, False, f"Unknown KI backend: {backend_id}")


def create_segmenter(
    backend_id: str = "ultralytics_mobile_sam", model_path: str | Path | None = None, device: str = "auto"
) -> BaseSegmenter:
    """Create a segmenter; GPU devices are wrapped so failures fall back to CPU."""
    device = (device or "auto").strip().lower()
    if not is_gpu_device(device):
        return _create_segmenter(backend_id, model_path, device)
    reason = None
    if device in {"dml", "directml"}:
        device = "dml"
        if backend_id == "ultralytics_sam3":
            reason = "SAM3 uses complex tensors that DirectML cannot handle."
    return DeviceFallbackSegmenter(
        lambda selected: _create_segmenter(backend_id, model_path, selected), reason, device=device
    )


def _create_segmenter(backend_id, model_path, device):
    if backend_id == "ultralytics_mobile_sam":
        return UltralyticsSAMSegmenter(model_path=model_path, device=device)
    if backend_id == "ultralytics_sam2":
        return UltralyticsSAM2Segmenter(model_path=model_path, device=device)
    if backend_id == "ultralytics_sam3":
        return UltralyticsSAM3Segmenter(model_path=model_path, device=device)
    if backend_id == "texturesam":
        return TextureSAMSegmenter(model_path=model_path, device=device)
    raise RuntimeError(f"Cannot create KI backend: {backend_id}")


def prepare_segmenter(backend_id, model_path, device, image, existing=None, allow_backend_fallback=False):
    """Load the model and, when an image is given, encode it. Runs in a worker without touching GUI state."""
    if existing is not None:
        if image is None:
            existing.load()
        else:
            existing.set_image(image)
        return existing
    try:
        segmenter = create_segmenter(backend_id, model_path, device)
        if image is None:
            segmenter.load()
        else:
            segmenter.set_image(image)
        return segmenter
    except Exception:
        if not allow_backend_fallback or backend_id != "ultralytics_sam3" or model_path is not None:
            raise
        logger.warning("SAM3 initialization failed; trying SAM2.", exc_info=True)
        return prepare_segmenter("ultralytics_sam2", None, device, image)
