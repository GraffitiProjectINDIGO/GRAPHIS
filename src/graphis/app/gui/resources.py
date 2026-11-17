# Copyright (C) 2026 Martin Wieser

from pathlib import Path

from PySide6.QtGui import QIcon, QPixmap


class _ResourcePaths:
    def __init__(self, gui_dir: str | Path):
        self.gui_dir = Path(gui_dir)

    @property
    def icon_dir(self) -> Path:
        return self.gui_dir / "icons"


_RESOURCE_PATHS = _ResourcePaths(Path(__file__).resolve().parent)


def configure_gui_resources(gui_dir: str | Path) -> None:
    _RESOURCE_PATHS.gui_dir = Path(gui_dir)


def resource_path(name: str) -> Path:
    return _RESOURCE_PATHS.gui_dir / name


def stylesheet_path(name: str = "main_window.qss") -> Path:
    return resource_path(name)


def icon_path(name: str) -> Path:
    return _RESOURCE_PATHS.icon_dir / name


def icon_path_str(name: str) -> str:
    return icon_path(name).as_posix()


def icon_url(name: str) -> str:
    return f'"{icon_path(name).as_posix()}"'


def icon(name: str) -> QIcon:
    return QIcon(icon_path_str(name))


def pixmap(name: str) -> QPixmap:
    return QPixmap(icon_path_str(name))
