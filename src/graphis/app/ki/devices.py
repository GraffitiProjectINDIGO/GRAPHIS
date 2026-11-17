# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""PyTorch device discovery for AI segmentation.

Supported devices:
- ``cpu`` everywhere; always the fallback.
- ``cuda[:N]`` for NVIDIA CUDA builds of PyTorch (Windows, Linux) and AMD ROCm builds (Linux).
  ROCm builds report themselves through the CUDA API, so both use the same code path.
- ``mps`` for Apple Silicon (macOS).
- ``dml`` only as an explicit, experimental opt-in when ``torch-directml`` is installed (Windows).

``auto`` selects CUDA/ROCm, then MPS, then CPU. It never selects DirectML.
"""

import gc
import sys
from typing import Any

GPU_FALLBACK_DEVICES = ("cuda", "mps", "dml")


def torch_directml_available() -> bool:
    try:
        import torch_directml
    except (ImportError, OSError, RuntimeError):
        return False

    try:
        return bool(torch_directml.is_available())
    except Exception:
        return False


def torch_directml_device() -> Any:
    try:
        import torch_directml
    except ImportError as err:
        raise RuntimeError("DirectML was selected, but torch-directml is not installed.") from err

    if not torch_directml_available():
        raise RuntimeError("DirectML was selected, but no DirectML device is available.")
    return torch_directml.device()


def _import_torch():
    try:
        import torch
    except ImportError:
        return None
    return torch


def _cuda_available(torch) -> bool:
    try:
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _mps_available(torch) -> bool:
    backend = getattr(getattr(torch, "backends", None), "mps", None)
    try:
        return bool(backend is not None and backend.is_available())
    except Exception:
        return False


def gpu_vendor_label(torch) -> str:
    return "AMD ROCm" if getattr(torch.version, "hip", None) else "NVIDIA CUDA"


def torch_device_options() -> list[tuple[str, str]]:
    """Return every device PyTorch can use on this computer as (device id, label)."""
    options = [("auto", "Auto"), ("cpu", "CPU")]
    torch = _import_torch()
    if torch is not None:
        if _cuda_available(torch):
            vendor = gpu_vendor_label(torch)
            for index in range(torch.cuda.device_count()):
                options.append((f"cuda:{index}", f"{vendor} {index}: {torch.cuda.get_device_name(index)}"))
        if _mps_available(torch):
            options.append(("mps", "Apple GPU (MPS)"))
    if torch_directml_available():
        options.append(("dml", "DirectML (experimental)"))
    return options


def resolve_sam_device(device: str = "auto") -> str:
    device = (device or "auto").strip().lower()
    if device == "auto":
        torch = _import_torch()
        if torch is None:
            return "cpu"
        if _cuda_available(torch):
            return "cuda"
        if _mps_available(torch):
            return "mps"
        return "cpu"
    if device == "cpu":
        return "cpu"
    if device in {"dml", "directml"}:
        if not torch_directml_available():
            raise RuntimeError("DirectML was selected for SAM, but no DirectML device is available.")
        return "dml"
    if device == "cuda" or device.startswith("cuda:"):
        torch = _import_torch()
        if torch is None:
            raise RuntimeError("A GPU was selected for SAM, but PyTorch is not installed.")
        if not _cuda_available(torch):
            raise RuntimeError("A CUDA/ROCm GPU was selected for SAM, but PyTorch cannot use it.")
        return device
    if device == "mps":
        torch = _import_torch()
        if torch is None or not _mps_available(torch):
            raise RuntimeError("The Apple GPU (MPS) was selected for SAM, but PyTorch cannot use it.")
        return "mps"
    raise ValueError(f"Unsupported SAM device: {device}")


def is_gpu_device(device: str) -> bool:
    device = (device or "").strip().lower()
    return device in {"auto", "directml"} or device.split(":", 1)[0] in GPU_FALLBACK_DEVICES


def release_ai_memory() -> None:
    """Free memory of released models. Never imports PyTorch just for this."""
    gc.collect()
    torch = sys.modules.get("torch")
    if torch is None:
        return
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        mps = getattr(torch, "mps", None)
        if mps is not None and _mps_available(torch):
            mps.empty_cache()
    except Exception:
        pass


def sam_device_options(backend_id=None) -> list[tuple[str, str]]:
    return [(key, label) for key, label in torch_device_options()
            if not (key == "dml" and backend_id == "ultralytics_sam3")]
