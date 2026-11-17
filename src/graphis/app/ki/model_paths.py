# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""User-selected folders for AI model files.

GRAPHIS does not ship or download models. Users download them and select the folders in the
AI configuration; see the "AI models" section of the README.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

AI_SETTINGS_FILE = "ai_models.json"


@dataclass
class AIModelSettings:
    segmentation_dir: str = ""
    speech_dir: str = ""

    def __post_init__(self):
        self.segmentation_dir = (self.segmentation_dir or "").strip()
        self.speech_dir = (self.speech_dir or "").strip()

    def to_dict(self) -> dict[str, str]:
        return {"segmentation_dir": self.segmentation_dir, "speech_dir": self.speech_dir}


def load_ai_settings(config_path: Path) -> AIModelSettings:
    if not config_path.exists():
        return AIModelSettings()
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Could not read AI model settings: %s", config_path)
        return AIModelSettings()
    return AIModelSettings(str(data.get("segmentation_dir", "")), str(data.get("speech_dir", "")))


def write_ai_settings(config_path: Path, settings: AIModelSettings) -> bool:
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")
    except OSError:
        logger.exception("Could not write AI model settings: %s", config_path)
        return False
    return True


_settings = AIModelSettings()


def apply_ai_settings(settings: AIModelSettings) -> None:
    """Make the folders available to the segmentation and speech backends."""
    global _settings
    _settings = AIModelSettings(settings.segmentation_dir, settings.speech_dir)


def _folder(path_text: str) -> Path | None:
    return Path(path_text).expanduser() if path_text else None


def segmentation_model_dir() -> Path | None:
    return _folder(_settings.segmentation_dir)


def speech_model_dir() -> Path | None:
    return _folder(_settings.speech_dir)
