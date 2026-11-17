# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import os
import tomllib

from PyInstaller.utils.hooks import collect_all
from importlib.util import find_spec


specpath = os.path.dirname(os.path.abspath(SPEC))
path_to_repo_main = Path(specpath)
print("Path to repo main folder:", path_to_repo_main.as_posix())

path_to_src = path_to_repo_main / "src"
path_to_graphis = path_to_src / "graphis"
path_to_graphis_app = path_to_graphis / "app"
path_to_graphis_gui = path_to_graphis_app / "gui"
path_to_icons = path_to_graphis_app / "gui" / "icons"
icon = path_to_icons / "icon.png"
pyproject_toml_file = path_to_repo_main / "pyproject.toml"

if pyproject_toml_file.exists() and pyproject_toml_file.is_file():
    with pyproject_toml_file.open("rb") as fp:
        toml_file = tomllib.load(fp)
    __package_version = toml_file["project"]["version"]
else:
    raise SystemExit(f"pyproject.toml not found: {pyproject_toml_file}")

name_app = "GRAPHIS_" + __package_version.replace(".", "_")

block_cipher = None

added_files = [
    ((path_to_repo_main / "config" / "graphis.config").as_posix(), "config"),
    (path_to_icons.as_posix(), "app/icons"),
    ((path_to_graphis_gui / "main_window.qss").as_posix(), "app"),
    ((path_to_graphis_app / "ThirdPartyNotices.json").as_posix(), "app"),
    (pyproject_toml_file.as_posix(), "."),
    ((path_to_repo_main / "license").as_posix(), "."),
]

added_binaries = []
added_hiddenimports = []

# IPTC-IRIS ships an ExifTool config (iptc_iris/data/exiftool_iptc_2026.config) that it passes to
# every ExifTool call; PyInstaller does not collect such data files on its own.
iris_datas, iris_binaries, iris_imports = collect_all("iptc_iris")
added_files += iris_datas
added_hiddenimports += iris_imports

if find_spec("torch_directml") is not None:
    dml_datas, dml_binaries, dml_imports = collect_all("torch_directml")
    added_files += dml_datas
    added_binaries += dml_binaries
    added_hiddenimports += dml_imports

# Speech recognition: faster-whisper (Silero VAD asset), CTranslate2 and ONNX Runtime native libraries.
# No AI models are bundled; users download them and select the folders in the AI configuration.
for package in ("faster_whisper", "ctranslate2", "onnxruntime"):
    if find_spec(package) is not None:
        package_datas, package_binaries, package_imports = collect_all(package)
        added_files += package_datas
        added_binaries += package_binaries
        added_hiddenimports += package_imports

a = Analysis(
    [(path_to_graphis / "main.py").as_posix()],
    pathex=[path_to_src.as_posix()],
    binaries=added_binaries,
    datas=added_files,
    hiddenimports=added_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=name_app,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon.as_posix(),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=name_app,
)
