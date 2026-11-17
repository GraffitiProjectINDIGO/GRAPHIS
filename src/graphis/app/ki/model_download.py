# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Download AI models into a user-selected folder.

- Speech: faster-whisper models from Hugging Face, each in its own subfolder, e.g. ``<folder>/small``.
- Segmentation: MobileSAM and SAM2 checkpoints from the Ultralytics GitHub releases, stored directly
  in the folder. SAM3 (gated on Hugging Face) and TextureSAM (Google Drive) are downloaded manually;
  see the README.

Files are downloaded under a hidden temporary name first and only renamed after they are complete,
so a cancelled or failed download never leaves a broken model.
"""

import json
import os
import shutil
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

HF_ENDPOINT = "https://huggingface.co"
USER_AGENT = "GRAPHIS"
REQUEST_TIMEOUT_SECONDS = 30
CHUNK_BYTES = 1024 * 1024
SKIPPED_FILES = {".gitattributes", "README.md"}


@dataclass(frozen=True)
class SpeechModelInfo:
    name: str
    repo_id: str
    size_mb: int
    description: str


SPEECH_MODEL_CATALOG = (
    SpeechModelInfo("tiny", "Systran/faster-whisper-tiny", 78, "Fastest, lowest accuracy."),
    SpeechModelInfo("base", "Systran/faster-whisper-base", 148, "Fast. Good for slower computers."),
    SpeechModelInfo("small", "Systran/faster-whisper-small", 487, "Recommended: accurate and real-time on most CPUs."),
    SpeechModelInfo("medium", "Systran/faster-whisper-medium", 1530, "More accurate, slower."),
    SpeechModelInfo(
        "large-v3-turbo", "dropbox-dash/faster-whisper-large-v3-turbo", 1622, "Very accurate. Needs a fast CPU."
    ),
    SpeechModelInfo("large-v3", "Systran/faster-whisper-large-v3", 3090, "Most accurate, slow on CPU."),
)


ULTRALYTICS_ASSETS = "https://github.com/ultralytics/assets/releases/download/v8.4.0"


@dataclass(frozen=True)
class SegmentationModelInfo:
    name: str
    backend_id: str
    filename: str
    url: str
    size_mb: int
    description: str


SEGMENTATION_MODEL_CATALOG = (
    SegmentationModelInfo(
        "MobileSAM", "ultralytics_mobile_sam", "mobile_sam.pt", f"{ULTRALYTICS_ASSETS}/mobile_sam.pt", 41,
        "Fastest. Recommended without an NVIDIA GPU.",
    ),
    SegmentationModelInfo(
        "SAM2", "ultralytics_sam2", "sam2.1_l.pt", f"{ULTRALYTICS_ASSETS}/sam2.1_l.pt", 449,
        "More accurate. A few seconds per image on CPU.",
    ),
)


class DownloadCancelled(Exception):
    pass


def segmentation_model_info(name: str) -> SegmentationModelInfo:
    for info in SEGMENTATION_MODEL_CATALOG:
        if info.name == name:
            return info
    raise KeyError(name)


def is_segmentation_model_downloaded(folder: Path | None, name: str) -> bool:
    return folder is not None and (folder / segmentation_model_info(name).filename).is_file()


def speech_model_info(name: str) -> SpeechModelInfo:
    for info in SPEECH_MODEL_CATALOG:
        if info.name == name:
            return info
    raise KeyError(name)


def is_downloaded(folder: Path | None, name: str) -> bool:
    return folder is not None and (folder / name / "model.bin").is_file()


def _open(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS)


def _check_free_space(folder: Path, total: int) -> None:
    free = shutil.disk_usage(folder).free
    if total and free < total * 1.05:
        raise RuntimeError(f"Not enough disk space: {total / 1e6:.0f} MB needed, {free / 1e6:.0f} MB free.")


def _stream(response, output, progress, cancelled, offset=0, total=0) -> int:
    written = 0
    while True:
        if cancelled is not None and cancelled():
            raise DownloadCancelled()
        chunk = response.read(CHUNK_BYTES)
        if not chunk:
            return written
        output.write(chunk)
        written += len(chunk)
        if progress is not None:
            progress(offset + written, total)


def download_segmentation_model(
    info: SegmentationModelInfo,
    folder: Path,
    progress: Callable[[int, int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> Path:
    """Download a checkpoint into ``folder / info.filename`` and return that path."""
    folder = Path(folder)
    target = folder / info.filename
    if target.is_file():
        return target
    folder.mkdir(parents=True, exist_ok=True)
    partial = folder / f".{info.filename}.download"
    try:
        with _open(info.url) as response:
            total = int(response.headers.get("Content-Length") or 0)
            _check_free_space(folder, total)
            with partial.open("wb") as output:
                written = _stream(response, output, progress, cancelled, total=total)
        if total and written != total:
            raise RuntimeError(f"Download of {info.filename} is incomplete ({written} of {total} bytes).")
        os.replace(partial, target)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    return target


def list_model_files(repo_id: str) -> tuple[str, list[tuple[str, int]]]:
    """Return the repository revision and the (file name, size) pairs to download."""
    url = f"{HF_ENDPOINT}/api/models/{repo_id}?blobs=true"
    with _open(url) as response:
        data = json.load(response)
    files = [
        (item["rfilename"], int(item.get("size") or 0))
        for item in data.get("siblings", [])
        if item.get("rfilename") not in SKIPPED_FILES and "/" not in item.get("rfilename", "/")
    ]
    if not any(name == "model.bin" for name, _ in files):
        raise RuntimeError(f"{repo_id} does not contain a faster-whisper model (model.bin).")
    return str(data.get("sha") or "main"), files


def download_speech_model(
    info: SpeechModelInfo,
    folder: Path,
    progress: Callable[[int, int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> Path:
    """Download a model into ``folder / info.name`` and return that path."""
    folder = Path(folder)
    target = folder / info.name
    if is_downloaded(folder, info.name):
        return target
    if target.exists() and any(target.iterdir()):
        raise RuntimeError(f"The folder {target} already exists and is not a complete model. Remove it first.")

    revision, files = list_model_files(info.repo_id)
    total = sum(size for _, size in files)
    folder.mkdir(parents=True, exist_ok=True)
    _check_free_space(folder, total)

    partial = folder / f".{info.name}.download"
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir()
    done = 0
    try:
        for name, size in files:
            url = f"{HF_ENDPOINT}/{info.repo_id}/resolve/{revision}/{urllib.parse.quote(name)}"
            with _open(url) as response, (partial / name).open("wb") as output:
                written = _stream(response, output, progress, cancelled, done, total)
            if size and written != size:
                raise RuntimeError(f"Download of {name} is incomplete ({written} of {size} bytes).")
            done += written
        if target.exists():
            target.rmdir()
        os.replace(partial, target)
    except BaseException:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return target
