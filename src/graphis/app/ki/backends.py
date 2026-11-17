# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path

from graphis.app.ki.model_paths import segmentation_model_dir

MODEL_FOLDER_HINT = "Select the segmentation model folder in the AI configuration (see README, AI models)."


@dataclass(frozen=True)
class BackendCheck:
    backend_id: str
    available: bool
    message: str = ""
    model_path: Path | None = None


def configured_model_candidates(*names: str) -> tuple[Path, ...]:
    """Model paths in the segmentation folder selected in the AI configuration."""
    folder = segmentation_model_dir()
    if folder is None:
        return ()
    return tuple(folder / name for name in names)


def mobile_sam_model_candidates() -> tuple[Path, ...]:
    return configured_model_candidates("mobile_sam.pt")


def sam2_model_candidates() -> tuple[Path, ...]:
    return configured_model_candidates("sam2.1_l.pt", "sam2.1_hiera_large.pt")


def sam3_model_candidates() -> tuple[Path, ...]:
    return configured_model_candidates("sam3.pt")


def texturesam_repo_candidates() -> tuple[Path, ...]:
    return configured_model_candidates("TextureSAM")


def texturesam_model_candidates() -> tuple[Path, ...]:
    return configured_model_candidates(
        "sam2.1_hiera_small_1.pt", "TextureSAM/Checkpoints/sam2.1_hiera_small_1.pt"
    )


def first_existing_path(paths: tuple[Path, ...]) -> Path | None:
    for path in paths:
        if path.exists() and path.is_file():
            return path
    return None


def find_segmentation_models() -> dict[str, Path | None]:
    """Model files found for each backend, without importing PyTorch."""
    texturesam_repo = first_existing_path(tuple(path / "README.md" for path in texturesam_repo_candidates()))
    return {
        "ultralytics_sam3": first_existing_path(sam3_model_candidates()),
        "ultralytics_sam2": first_existing_path(sam2_model_candidates()),
        "ultralytics_mobile_sam": first_existing_path(mobile_sam_model_candidates()),
        "texturesam": first_existing_path(texturesam_model_candidates()) if texturesam_repo else None,
    }


def _version_tuple(version: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", version)
    return tuple(int(part) for part in parts[:3])


def check_ultralytics_mobile_sam(model_path: str | Path | None = None) -> BackendCheck:
    try:
        import torch  # noqa: F401
        import ultralytics  # noqa: F401
    except ImportError as err:
        return BackendCheck("ultralytics_mobile_sam", False, f"Missing Python dependency: {err.name}")

    resolved_model_path = (
        Path(model_path) if model_path is not None else first_existing_path(mobile_sam_model_candidates())
    )
    if resolved_model_path is None:
        return BackendCheck(
            "ultralytics_mobile_sam",
            False,
            f"MobileSAM model file mobile_sam.pt not found. {MODEL_FOLDER_HINT}",
        )
    if "sam2" in resolved_model_path.name.lower():
        return BackendCheck(
            "ultralytics_mobile_sam",
            False,
            "SAM2 checkpoints need the ultralytics_sam2 backend, not ultralytics_mobile_sam.",
        )
    return BackendCheck("ultralytics_mobile_sam", True, "Ultralytics MobileSAM backend available.", resolved_model_path)


def check_ultralytics_sam2(model_path: str | Path | None = None) -> BackendCheck:
    try:
        import torch  # noqa: F401
        import ultralytics  # noqa: F401
        from ultralytics.models.sam.predict import SAM2Predictor  # noqa: F401
    except ImportError as err:
        return BackendCheck("ultralytics_sam2", False, f"Missing Python dependency: {err.name}")

    resolved_model_path = Path(model_path) if model_path is not None else first_existing_path(sam2_model_candidates())
    if resolved_model_path is None:
        return BackendCheck(
            "ultralytics_sam2",
            False,
            f"SAM2 model file sam2.1_l.pt not found. {MODEL_FOLDER_HINT}",
        )
    if "sam2" not in resolved_model_path.name.lower():
        return BackendCheck(
            "ultralytics_sam2",
            False,
            "The ultralytics_sam2 backend expects a SAM2 checkpoint such as sam2.1_hiera_large.pt.",
        )
    return BackendCheck("ultralytics_sam2", True, "Ultralytics SAM2 backend available.", resolved_model_path)


def check_ultralytics_sam3(model_path: str | Path | None = None) -> BackendCheck:
    try:
        import torch  # noqa: F401
        import ultralytics
        from ultralytics.models.sam import SAM3Predictor  # noqa: F401
    except ImportError as err:
        return BackendCheck("ultralytics_sam3", False, f"Missing Python dependency: {err.name}")

    ultralytics_version = _version_tuple(getattr(ultralytics, "__version__", "0"))
    if ultralytics_version < (8, 3, 237):
        return BackendCheck(
            "ultralytics_sam3",
            False,
            "Ultralytics SAM3 needs ultralytics>=8.3.237. Upgrade with: pip install -U ultralytics",
        )

    resolved_model_path = Path(model_path) if model_path is not None else first_existing_path(sam3_model_candidates())
    if resolved_model_path is None:
        return BackendCheck(
            "ultralytics_sam3",
            False,
            f"SAM3 model file sam3.pt not found. {MODEL_FOLDER_HINT}",
        )
    if "sam3" not in resolved_model_path.name.lower():
        return BackendCheck(
            "ultralytics_sam3",
            False,
            "The ultralytics_sam3 backend expects the SAM3 checkpoint sam3.pt.",
        )
    return BackendCheck("ultralytics_sam3", True, "Ultralytics SAM3 backend available.", resolved_model_path)


def check_texturesam(model_path: str | Path | None = None) -> BackendCheck:
    repo_path = first_existing_path(tuple(path / "README.md" for path in texturesam_repo_candidates()))
    if repo_path is None:
        return BackendCheck(
            "texturesam",
            False,
            f"TextureSAM repository folder 'TextureSAM' not found. {MODEL_FOLDER_HINT}",
        )

    resolved_model_path = (
        Path(model_path) if model_path is not None else first_existing_path(texturesam_model_candidates())
    )
    if resolved_model_path is None:
        return BackendCheck(
            "texturesam",
            False,
            f"TextureSAM checkpoint sam2.1_hiera_small_1.pt not found. {MODEL_FOLDER_HINT}",
        )
    if "sam2.1_hiera_small" not in resolved_model_path.name.lower():
        return BackendCheck("texturesam", False, "TextureSAM expects a fine-tuned SAM2.1 Hiera Small checkpoint.")

    dependency_modules = {
        "cv2": "opencv-python",
        "hydra": "hydra-core",
        "iopath": "iopath",
        "omegaconf": "omegaconf",
        "torch": "torch",
        "torchvision": "torchvision",
    }
    missing_dependencies = [
        package_name
        for module_name, package_name in dependency_modules.items()
        if importlib.util.find_spec(module_name) is None
    ]
    if missing_dependencies:
        return BackendCheck(
            "texturesam",
            False,
            (
                "Missing TextureSAM Python dependencies: "
                f"{', '.join(missing_dependencies)}. Install with: pip install -e \".[texturesam]\""
            ),
        )

    return BackendCheck(
        "texturesam",
        True,
        "TextureSAM backend available.",
        resolved_model_path,
    )
