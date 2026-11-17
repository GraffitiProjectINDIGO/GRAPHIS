# Copyright (C) 2026 Martin Wieser, Geert Verhoeven
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

EXIFTOOL = "exiftool"
EXIV2 = "exiv2"
SUPPORTED_METADATA_TOOLS = (EXIFTOOL, EXIV2)


@dataclass
class MetadataToolSettings:
    tool: str = EXIFTOOL
    exiftool_path: str = ""
    exiv2_path: str = ""

    def __post_init__(self):
        self.tool = normalize_metadata_tool(self.tool)
        self.exiftool_path = (self.exiftool_path or "").strip()
        self.exiv2_path = (self.exiv2_path or "").strip()

    def path_for_tool(self, tool: str | None = None) -> str:
        tool = normalize_metadata_tool(tool or self.tool)
        return self.exiv2_path if tool == EXIV2 else self.exiftool_path

    def to_dict(self) -> dict[str, str]:
        return {
            "tool": self.tool,
            "exiftool_path": self.exiftool_path,
            "exiv2_path": self.exiv2_path,
        }


@dataclass(frozen=True)
class MetadataToolTestResult:
    available: bool
    message: str
    executable: str = ""
    output: str = ""
    returncode: int | None = None


def normalize_metadata_tool(tool: str | None) -> str:
    tool = (tool or EXIFTOOL).strip().lower()
    return tool if tool in SUPPORTED_METADATA_TOOLS else EXIFTOOL


def load_metadata_tool_settings(config_path: Path) -> MetadataToolSettings:
    if not config_path.exists():
        return MetadataToolSettings()
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Could not read metadata tool settings: %s", config_path)
        return MetadataToolSettings()
    return MetadataToolSettings(
        tool=str(data.get("tool", EXIFTOOL)),
        exiftool_path=str(data.get("exiftool_path", "")),
        exiv2_path=str(data.get("exiv2_path", "")),
    )


def write_metadata_tool_settings(config_path: Path, settings: MetadataToolSettings) -> bool:
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")
    except OSError:
        logger.exception("Could not write metadata tool settings: %s", config_path)
        return False
    return True


def exiftool_path_from_settings(settings: MetadataToolSettings) -> str:
    configured_path = settings.exiftool_path.strip()
    if configured_path:
        return configured_path
    return shutil.which(EXIFTOOL) or EXIFTOOL


def metadata_tool_path_from_settings(settings: MetadataToolSettings) -> str:
    tool = normalize_metadata_tool(settings.tool)
    configured_path = settings.path_for_tool(tool)
    if configured_path:
        return configured_path
    return shutil.which(tool) or tool


def resolve_metadata_tool_executable(tool: str, configured_path: str = "") -> str | None:
    tool = normalize_metadata_tool(tool)
    configured_path = (configured_path or "").strip()
    if configured_path:
        return configured_path

    return shutil.which(EXIV2 if tool == EXIV2 else EXIFTOOL)


def metadata_tool_version_args(tool: str, executable: str) -> list[str]:
    tool = normalize_metadata_tool(tool)
    if tool == EXIV2:
        return [executable, "-V"]
    return [executable, "-ver"]


def test_metadata_tool(
    tool: str,
    configured_path: str = "",
    timeout: int = 5,
) -> MetadataToolTestResult:
    tool = normalize_metadata_tool(tool)
    executable = resolve_metadata_tool_executable(tool, configured_path)
    if not executable:
        return MetadataToolTestResult(False, "Tool not found on PATH.")

    try:
        result = subprocess.run(
            metadata_tool_version_args(tool, executable),
            input="",
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except OSError as err:
        return MetadataToolTestResult(False, f"Tool failed to start: {err}", executable=executable)
    except subprocess.TimeoutExpired:
        return MetadataToolTestResult(False, "Tool test timed out.", executable=executable)

    output = (result.stdout or result.stderr).strip()
    if result.returncode == 0:
        version_text = output.splitlines()[0] if output else executable
        return MetadataToolTestResult(True, f"Available: {version_text}", executable, output, result.returncode)

    return MetadataToolTestResult(
        False,
        f"Test failed: {output or executable}",
        executable,
        output,
        result.returncode,
    )
