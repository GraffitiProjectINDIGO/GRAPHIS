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

import copy
import ctypes
import datetime
import json
import logging
import os
import sys
import traceback
import uuid
from ctypes import wintypes
from multiprocessing import freeze_support
from pathlib import Path

from PySide6 import QtCore, QtGui
from PySide6.QtCore import QEvent, QThreadPool, Slot
from PySide6.QtGui import QAction, QColor, QPixmap, Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from graphis import software_version
from graphis.app.config_paths import APP_NAME, ORGANIZATION_NAME, app_config_dir, app_config_file
from graphis.app.controlled_vocabulary import (
    TARGET_CONTRIBUTOR_ROLE,
    TARGET_REGION_ROLE,
    TARGET_REGION_TYPE,
    ControlledVocabularyStore,
    VocabularyTerm,
    graphis_contributor_role_term,
    graphis_role_term,
    graphis_type_term,
)
from graphis.app.graphic.digitizerscene import DIGITIZERScene
from graphis.app.graphic.digitizerview import DIGITIZERView
from graphis.app.gui.file_toolbar import FileToolBar
from graphis.app.gui.main_window_ui import MainWindowUiBuilder
from graphis.app.gui.preview_class import PreviewDelegate, PreviewModel
from graphis.app.gui.region_operations_toolbar import RegionOperationsToolbar
from graphis.app.gui.resources import configure_gui_resources, icon_path_str, stylesheet_path
from graphis.app.gui.resources import icon as resource_icon
from graphis.app.gui.status_bar import GraphisStatusBar
from graphis.app.gui.thumbnail_preview_view import ThumbnailPreviewPanel
from graphis.app.imgregion.json_model import JsonModel
from graphis.app.imgregion.region_editor import RegionEditorWidget
from graphis.app.imgregion.region_graph_dock import GraphDockWidget, RegionEditorPopoutWindow
from graphis.app.imgregion.region_graph_model import CHILD_KEYS
from graphis.app.ki.backends import find_segmentation_models
from graphis.app.ki.model_download import segmentation_model_info
from graphis.app.ki.model_paths import (
    AI_SETTINGS_FILE,
    AIModelSettings,
    apply_ai_settings,
    load_ai_settings,
    write_ai_settings,
)
from graphis.app.ki.speech import available_speech_models
from graphis.app.popups import message_box
from graphis.app.popups.ai_config_popup import AIConfigPopup
from graphis.app.popups.controlled_vocabulary_popup import ControlledVocabularyPopup
from graphis.app.popups.database_statistics_popup import DatabaseStatisticsPopup
from graphis.app.popups.log_popup import LogPopup
from graphis.app.popups.metadata_tool_popup import MetadataToolPopup
from graphis.app.popups.model_download_popup import SegmentationModelDownloadPopup, SpeechModelDownloadPopup
from graphis.app.popups.popup_about import POPUPAbout
from graphis.app.popups.popup_user import POPUPUser
from graphis.app.popups.region_json_metadata_popup import RegionJsonMetadataPopup
from graphis.app.popups.speech_transcription_popup import SpeechTranscriptionPopup
from graphis.app.popups.user_information_popup import UserInformationPopup
from graphis.app.var_classes import (
    LOGGING_STYLE,
    Instructions,
    PreviewModelData,
    get_image_region_role,
    image_region_role,
    load_config,
)
from graphis.db.db_handler import DBHandler
from graphis.interface.exchange import CsvImportResult, export_rectangle_csv, import_rectangle_csv_in_process
from graphis.interface.image_importer import ImageImportResult, image_files_in_folder, import_images
from graphis.interface.image_loader import image_loader
from graphis.interface.image_metadata import (
    image_metadata_dict,
    image_metadata_orientation_present,
    image_metadata_visual_rotation,
)
from graphis.interface.image_regions import OpenImageRegions
from graphis.interface.imgregion_adapter import (
    apply_part_details_to_region,
    base_object_type,
    change_region_unit,
    combine_multigeometry_regions,
    detach_multigeometry_part,
    entity_identifier,
    entity_name,
    entity_roles,
    language_alternative_items,
    language_alternative_value,
    merge_region_geometries,
    metadata_lang_alt_value,
    multigeometry_part,
    normalize_lang_alt_text_fields,
    object_type_from_region,
    put_lang_alt_to_dict_or_remove,
    put_lang_alt_value_to_dict_or_remove,
    put_struc_tag,
    put_struct_to_dict_or_remove,
    put_text_to_dict_or_remove,
    remove_multigeometry_part,
    text_value,
    valid_region_geometry_merge_modes,
    validate_image_object_result,
)
from graphis.interface.meta_exif import meta_writer, parse_img_region
from graphis.interface.metadata_tools import (
    MetadataToolSettings,
    load_metadata_tool_settings,
    metadata_tool_path_from_settings,
    test_metadata_tool,
    write_metadata_tool_settings,
)
from graphis.interface.region_membership import PARENT_KEYS, region_identifier

logger = logging.getLogger(__name__)

AI_BACKEND_OPTIONS = [
    ("ultralytics_sam3", "SAM3"),
    ("ultralytics_sam2", "SAM2"),
    ("ultralytics_mobile_sam", "MobileSAM"),
    ("texturesam", "TextureSAM"),
]
AI_DEFAULT_DEVICE_OPTIONS = [("auto", "Auto"), ("cpu", "CPU")]


METADATA_TOOLS_SETTINGS_FILE = "metadata_tools.json"
STANDARD_REGION_METADATA_KEYS = {
    "rId",
    "RId",
    "name",
    "Name",
    "rRole",
    "RRole",
    "rCtype",
    "RCtype",
    "regionBoundary",
    "RegionBoundary",
}


path_to_license_folder = Path(__file__).resolve().with_name("app")


path_to_config = Path(__file__).resolve().with_name("config") / "graphis.config"
if not path_to_config.exists():
    path_to_config = Path(__file__).resolve().parent.parent.parent / "config" / "graphis.config"

path_to_gui_resources = Path(__file__).resolve().with_name("app")
if (path_to_gui_resources / "gui").exists():
    path_to_gui_resources = Path(__file__).resolve().with_name("app") / "gui"
configure_gui_resources(path_to_gui_resources)


def path_with_forced_suffix(path: str | Path, suffix: str) -> Path:
    path = Path(path)
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    if path.suffix.lower() == suffix.lower():
        return path
    return path.with_suffix(suffix)


def _first_metadata_struct(value):
    if isinstance(value, list):
        return value[0] if value else None
    if isinstance(value, dict):
        return value
    return None


def _contributor_rows_from_metadata(value):
    rows = []
    contributors = value if isinstance(value, list) else [value] if isinstance(value, dict) else []
    for contributor in contributors:
        if not isinstance(contributor, dict):
            continue
        roles = entity_roles(contributor)
        rows.append(
            {
                "role": text_value(roles[-1]) if roles else "",
                "identifier": entity_identifier(contributor),
                "name": entity_name(contributor),
            }
        )
    return rows


def _contributor_entities_from_rows(rows):
    contributors = []
    for row in rows:
        role = str(row.get("role", "")).strip()
        identifier = str(row.get("identifier", "")).strip()
        name = str(row.get("name", "")).strip()
        if not role and not identifier and not name:
            continue
        contributor = {}
        if identifier:
            contributor["identifiers"] = [identifier]
        if name:
            contributor["name"] = name
        if role:
            contributor["role"] = [role]
        contributors.append(contributor)
    return contributors


def _contributor_present_with_role(value, role, identifier, name):
    role = str(role or "").strip()
    identifier = str(identifier or "").strip()
    name = str(name or "").strip()
    contributors = value if isinstance(value, list) else [value] if isinstance(value, dict) else []
    for contributor in contributors:
        if not isinstance(contributor, dict) or role not in entity_roles(contributor):
            continue
        contributor_identifier = entity_identifier(contributor)
        contributor_name = entity_name(contributor)
        if identifier and contributor_identifier == identifier:
            return True
        if not identifier and name and contributor_name == name:
            return True
    return False


def _append_contributor_if_role_missing(data, tag, role, identifier, name):
    role = str(role or "").strip()
    identifier = str(identifier or "").strip()
    name = str(name or "").strip()
    if not role or not (identifier or name):
        return False
    existing_value = data.get(tag, [])
    if _contributor_present_with_role(existing_value, role, identifier, name):
        return False

    if isinstance(existing_value, list):
        contributors = existing_value
    elif isinstance(existing_value, dict):
        contributors = [existing_value]
    else:
        contributors = []
    contributor = {}
    if identifier:
        contributor["identifiers"] = [identifier]
    if name:
        contributor["name"] = name
    contributor["role"] = [role]
    data[tag] = [*contributors, contributor]
    return True


def _language_value_from_rows(rows):
    default_text = ""
    alternatives = []
    for language, text in rows:
        if language == "x-default":
            default_text = text
        else:
            alternatives.append((language, text))
    return language_alternative_value(default_text, alternatives)


def _vocabulary_name_from_identifier(identifier):
    text = str(identifier or "").rstrip("/")
    if not text:
        return ""
    return text.rsplit("/", 1)[-1] or text


class Signaller(QtCore.QObject):
    signal = QtCore.Signal(str, logging.LogRecord)


class QtHandler(logging.Handler):
    def __init__(self, slot_func, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signaller = Signaller()
        self.signaller.signal.connect(slot_func)

    def emit(self, record):
        status = self.format(record)
        self.signaller.signal.emit(status, record)


class OutputWrapper(QtCore.QObject):
    outputWritten = QtCore.Signal(object, object)

    def __init__(self, parent, stdout=True):
        QtCore.QObject.__init__(self, parent)
        if stdout:
            self._stream = sys.stdout
            sys.stdout = self
        else:
            self._stream = sys.stderr
            sys.stderr = self
        self._stdout = stdout

    def write(self, text):
        if self._stream is not None:
            self._stream.write(text)
        self.outputWritten.emit(text, self._stdout)

    def __getattr__(self, name):
        return getattr(self._stream, name)

    def __del__(self):
        try:
            if self._stdout:
                sys.stdout = self._stream
            else:
                sys.stderr = self._stream
        except AttributeError:
            pass


class WorkerSignal(QtCore.QObject):
    finished = QtCore.Signal()
    error = QtCore.Signal(tuple)
    result = QtCore.Signal(object)


class Worker(QtCore.QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignal()

    @Slot()
    def run(self):
        try:
            result = self.fn(
                *self.args,
                **self.kwargs,
            )
        except Exception:
            # traceback.print_exc()
            exec_type, value = sys.exc_info()[:2]
            self.signals.error.emit((exec_type, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)


class MainWindow(QMainWindow):
    actionMenu: QAction
    actionUser: QAction
    centralwidget: QWidget
    frame: QFrame
    verticalLayout_2: QVBoxLayout
    verticalLayout_3: QVBoxLayout
    verticalLayout_5: QVBoxLayout
    lbl_image_name: QLabel
    lbl_image_path: QLabel
    splitter_images: QSplitter
    view_digizizer: DIGITIZERView
    table_preview: ThumbnailPreviewPanel
    status_bar: QStatusBar

    def __init__(self):
        QMainWindow.__init__(self)

        # try to load config File
        (
            self.config_success,
            self.config_default,
            self.config_polygon,
            self.config_rectangle,
            self.config_circle,
            self.config_point,
            self.config_linestringstring,
        ) = load_config(path_to_config)
        self.vocabulary_store = ControlledVocabularyStore(app_config_file("controlled_vocabularies"))
        self.vocabulary_store.set_graphis_terms(self._graphis_vocabulary_terms())
        self.metadata_tool_settings_path = app_config_file(METADATA_TOOLS_SETTINGS_FILE)
        self.config_metadata_tool = load_metadata_tool_settings(self.metadata_tool_settings_path)
        self.ai_settings_path = app_config_file(AI_SETTINGS_FILE)
        self.config_ai = load_ai_settings(self.ai_settings_path)
        apply_ai_settings(self.config_ai)
        MainWindowUiBuilder().setup(self, stylesheet_path())

        self._main_layout_refresh_timer = QtCore.QTimer(self)
        self._main_layout_refresh_timer.setSingleShot(True)
        self._main_layout_refresh_timer.timeout.connect(self._refresh_main_layout)
        self.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.AnimatedDocks
        )
        self._install_region_editor()
        self._install_status_bar()
        self._install_log_popup()
        self._install_logging_handler()
        self._install_output_wrappers()
        self._warn_if_config_fallback_used()

        # ----------------------------------------------------------
        self.setWindowTitle("Graphis")
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(17)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(0)
        self.shadow.setColor(QColor(0, 0, 0, 150))

        self.splitter_images.setSizes([400, 250])

        # self.frame.setGraphicsEffect(self.shadow)

        # --------------------------------------------------------------
        # MultiThread
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(4)
        print(f"Multithreading with maximum {self.thread_pool.maxThreadCount()} threads")

        self.model_image_region = JsonModel()
        self.model_image_region_all = JsonModel()
        self.region_editor.configure_region_tables(self.model_image_region, self.model_image_region_all)

        # ----------------------------------------------------------
        # VARIABLES
        self.color_rectangle = QColor(self.config_rectangle.color_start)
        self.color_polygon = QColor(self.config_polygon.color_start)
        self.color_circle = QColor(self.config_circle.color_start)
        self.color_point = QColor(self.config_point.color_start)
        self.color_linestring = QColor(self.config_linestringstring.color_start)
        for shape in ("point", "circle", "linestring", "rectangle", "polygon"):
            self.region_editor.set_geometry_color(shape, getattr(self, f"color_{shape}"))

        self._install_region_operations_toolbar()

        self.log_file = Path()
        self.pop_user = POPUPUser()
        self.pop_about = POPUPAbout(path_to_license_folder)
        self.speech_model_name = "base"
        self._install_file_toolbar()
        self._install_metadata_tool_popup()
        self._install_ai_config_popup()
        self._install_user_information_popup()
        self.len_image_list = 0
        self.log_sync_nr = 0
        self.image_list = []
        self.digitizer_scene = DIGITIZERScene()
        self.ki_backend_id = self._default_ai_backend()
        self.ki_model_path = None
        self.ki_device = "auto"
        self._ai_initialization_request = None
        self._ai_initialization_worker = None
        self._ai_initialization_activate = False
        self._ai_reload_pending = False
        self._ai_prepared_image = None
        self._ai_keep_model_on_image_change = False
        self._ai_resume_after_image_load = False
        self._ai_device_options = list(AI_DEFAULT_DEVICE_OPTIONS)
        self._ki_backend_user_selected = False
        self.view_digizizer.setScene(self.digitizer_scene)
        self.view_digizizer.aiModeChanged.connect(self._set_ai_segmentation_mode)
        self.view_digizizer.aiToolChanged.connect(self.digitizer_scene.set_ai_tool)
        self.view_digizizer.aiResetRequested.connect(self.digitizer_scene.reset_ai_segmentation)
        self._ai_polygon_context = None
        self._ai_background_context = None
        self.digitizer_scene.aiBackgroundRequested.connect(self._segment_ai_background)
        self.view_digizizer.aiPolygonRequested.connect(self._convert_ai_mask_to_polygons)
        self.view_digizizer.aiPreclassificationChanged.connect(self.digitizer_scene.set_ai_preclassification_visible)
        self.view_digizizer.aiMaskColorChanged.connect(self.digitizer_scene.set_ai_mask_color)
        self.view_digizizer.aiBackendChanged.connect(self._ai_backend_selected)
        self.view_digizizer.aiDeviceChanged.connect(self._ai_device_selected)
        self.view_digizizer.set_ai_backend_options(AI_BACKEND_OPTIONS, self.ki_backend_id)
        self._ai_devices_scanned = False
        self._sync_ai_device_combo()
        self.view_digizizer.polygonBrushToggled.connect(self._set_polygon_brush_enabled)
        self.view_digizizer.polygonBrushModeChanged.connect(self.digitizer_scene.set_polygon_brush_mode)
        self.view_digizizer.polygonBrushSizeChanged.connect(self.digitizer_scene.set_polygon_brush_size)
        self.digitizer_scene.polygonBrushEnabledChanged.connect(self.view_digizizer.set_polygon_brush_checked)
        self.digitizer_scene.operationStateChanged.connect(self.view_digizizer.sync_polygon_brush_controls)
        self.digitizer_scene.color_rectangle = self.color_rectangle
        self.digitizer_scene.color_polygon = self.color_polygon
        self.digitizer_scene.color_circle = self.color_circle
        self.digitizer_scene.color_point = self.color_point
        self.digitizer_scene.color_linestring = self.color_linestring

        self._thumbnail_size_steps = (
            QtCore.QSize(180, 120),
            QtCore.QSize(240, 160),
            QtCore.QSize(300, 200),
            QtCore.QSize(360, 240),
            QtCore.QSize(450, 300),
            QtCore.QSize(540, 360),
        )
        self._thumbnail_size_index = 2
        self.delegate = PreviewDelegate()
        self.delegate.set_thumbnail_size(self._thumbnail_size_steps[self._thumbnail_size_index])
        self.table_preview.set_thumbnail_item_size(self._thumbnail_size_steps[self._thumbnail_size_index])
        self.delegate.rectangle_color = self.color_rectangle
        self.delegate.polygon_color = self.color_polygon
        self.delegate.circle_color = self.color_circle
        self.delegate.point_color = self.color_point
        self.delegate.linestring_color = self.color_linestring
        self.table_preview.setItemDelegate(self.delegate)
        self.model = PreviewModel()
        self.table_preview.setModel(self.model)
        self.table_preview.thumbnailDecreaseRequested.connect(lambda: self._change_thumbnail_size(-1))
        self.table_preview.thumbnailIncreaseRequested.connect(lambda: self._change_thumbnail_size(1))
        self._sync_thumbnail_size_controls()
        self.db = DBHandler()
        self.db.add_undo_listener(self._sync_undo_redo_actions)
        self.image_regions = None
        self.user = ""
        self.user_uri = ""
        self.auto_scale_factor: float | int | None = None
        self._auto_scale_warning_shown = False
        self.current_item = None
        self._current_item_form_baseline = None
        self.current_image = None
        self._visual_rotations_by_image_id = {}
        self.image_region_summaries = {}
        self.count_rectangle = 0
        self.count_polygon = 0
        self.count_circle = 0
        self.count_linestring = 0
        self.count_point = 0
        self.count_multipoint = 0
        self.count_multilinestring = 0
        self.count_multipolygon = 0
        self.database_statistics_popup.set_counts(
            image=0,
            multipoint=0,
            multilinestring=0,
            multipolygon=0,
            rectangle=0,
            polygon=0,
            circle=0,
            linestring=0,
            point=0,
            valid=0,
            warning=0,
            error=0,
        )
        self.rectangle_visible = True
        self.circle_visible = True
        self.point_visible = True
        self.polygon_visible = True
        self.linestring_visible = True
        self.image_loading = False
        self.image_loading_image_id_db = 0
        self.image_loading_name_path = ""
        self.image_loading_name = ""
        self._graph_selection_active = False

        # Connect double on image to load the image
        self.table_preview.doubleClicked.connect(self.scene_load_image)
        self.table_preview.thumbnailActionRequested.connect(self._thumbnail_context_action)

        self.digitizer_scene.object_att.connect(self._request_object_selection)
        self.digitizer_scene.geometry_part_selected.connect(self._select_geometry_part)
        self.digitizer_scene.object_deselected.connect(self._object_selection_cleared)
        self.digitizer_scene.object_add.connect(self.add_data)
        self.digitizer_scene.change_object.connect(self.change_finetuner)
        self.digitizer_scene.smoothGeometryRequested.connect(self._smooth_selected_geometry)
        self.digitizer_scene.reduceVerticesRequested.connect(self._reduce_selected_vertices)
        self.digitizer_scene.populateContextMenuRequested.connect(self._populate_digitizer_context_menu)
        self.digitizer_scene.groupSelectionToggled.connect(self.region_editor.graph_scene.toggle_group_selection)
        self.digitizer_scene.groupSelectionCleared.connect(self.region_editor.graph_scene.clear_group_selection)
        self.region_editor.graph_scene.groupSelectionChanged.connect(self.digitizer_scene.set_group_selection)
        self.digitizer_scene.message_no_valid.connect(self.message_no_valid_polygon)
        self.digitizer_scene.operationStateChanged.connect(self._geometry_operation_state_changed)
        self.digitizer_scene.selection_changed.connect(self._sync_geometry_action_availability)
        self.digitizer_scene.selection_changed.connect(self.view_digizizer.sync_overlay_buttons)
        self.view_digizizer.visualRotationChanged.connect(self._image_view_rotation_changed)
        self.view_digizizer.exifRotationRequested.connect(self._reset_image_view_rotation_to_exif)
        self.view_digizizer.metadataRequested.connect(self._show_image_metadata_popup)
        self._sync_geometry_action_availability()
        self._operation_event_filter_app = QApplication.instance()
        if self._operation_event_filter_app is not None:
            self._operation_event_filter_app.installEventFilter(self)

        self.region_editor.connect_region_controls(self.save_data)
        self.region_editor.objectSelected.connect(self._graph_object_selected)
        self.region_editor.geometryPartSelected.connect(self._select_geometry_part)
        self.region_editor.objectDeselected.connect(self._object_selection_cleared)
        self.region_editor.assignGeometryRequested.connect(self.assign_geometry_to_image_region)
        self.region_editor.clearGeometryRequested.connect(self.clear_image_region_geometry)
        self.region_editor.zoomToRegionRequested.connect(self.zoom_to_image_region)
        self.region_editor.deleteImageRegionRequested.connect(self.delete_image_region)
        self.region_editor.restoreOriginalRequested.connect(self.restore_original_image_regions_for_object)
        self.region_editor.jsonMetadataRequested.connect(self.edit_region_json_metadata)
        self.region_editor.mergeRegionsRequested.connect(self.merge_image_regions)
        self.region_editor.createContainerRequested.connect(self.create_empty_multigeometry_container)
        self.region_editor.groupRegionsRequested.connect(self.group_image_regions)
        self.region_editor.groupRegionsIntoRequested.connect(self.group_image_regions_into_container)
        self.region_editor.assignParentRequested.connect(self._begin_parent_assignment)
        self.region_editor.mergeTargetRequested.connect(self._begin_merge_target_selection)
        self.region_editor.detachGeometryPartRequested.connect(self.detach_geometry_part)
        self.region_editor.detachParentRequested.connect(self.detach_region_parent)
        self.region_editor.regionRoleVocabularyRequested.connect(self._show_region_role_vocabulary_popup)
        self.region_editor.regionTypeVocabularyRequested.connect(self._show_region_type_vocabulary_popup)
        self.region_editor.contributorRoleVocabularyRequested.connect(self._show_contributor_role_vocabulary_popup)
        self.region_editor.descriptionSpeechRequested.connect(self.show_speech_transcription_popup)
        self.region_editor.transcriptionSpeechRequested.connect(self.show_speech_transcription_popup)

        self.pop_user.show()
        self.pop_user.got_user.connect(self.user_save)
        self._sync_undo_redo_actions()

    def _install_region_editor(self):
        self.region_editor = RegionEditorWidget(self)

        self.region_popout = RegionEditorPopoutWindow()
        # self.region_popout.setWindowIcon(self.windowIcon())
        self.region_popout.dockRequested.connect(self.dock_region_editor)
        self.region_dock = GraphDockWidget("Region graph", self, docked_min_width=320)
        self.region_dock.setObjectName("regionGraphDock")
        self.region_dock.setStyleSheet("#regionGraphDock { background-color: #2c3e50; }")
        self.region_dock.setWidget(self.region_editor)
        self.region_dock.toggleRequested.connect(self.toggle_region_editor_window)

        self.region_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.TopDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        self.region_dock.layoutSettled.connect(self._region_dock_layout_settled)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.region_dock)
        QtCore.QTimer.singleShot(
            0,
            lambda: self.region_dock.restore_preferred_docked_size(Qt.DockWidgetArea.RightDockWidgetArea),
        )

    def _graphis_vocabulary_terms(self):
        terms = []
        for name, identifier in image_region_role:
            terms.append(graphis_role_term(name, identifier))
        for config in (
            self.config_polygon,
            self.config_rectangle,
            self.config_circle,
            self.config_point,
            self.config_linestringstring,
        ):
            role_identifier = get_image_region_role(config.region_role_name)
            if config.region_role_name and role_identifier:
                terms.append(graphis_role_term(config.region_role_name, role_identifier))
            if config.rctype_name or config.rctype_identifier:
                terms.append(graphis_type_term(config.rctype_name, config.rctype_identifier))
            for contributor_role in (config.region_creator_role, config.describer_role, config.transcriber_role):
                if contributor_role:
                    terms.append(
                        graphis_contributor_role_term(
                            _vocabulary_name_from_identifier(contributor_role),
                            contributor_role,
                        )
                    )
        return terms

    def _install_user_information_popup(self):
        self.user_information_popup = UserInformationPopup(
            self,
            self.file_toolbar.widgetForAction(self.file_toolbar.action_user_information),
        )
        self.user_information_popup.userChanged.connect(self._sync_user_information)

    def _install_metadata_tool_popup(self):
        self.metadata_tool_popup = MetadataToolPopup(
            self,
            self.file_toolbar.widgetForAction(self.file_toolbar.action_metadata_tools),
        )
        self.metadata_tool_popup.set_values(
            self.config_metadata_tool.tool,
            self.config_metadata_tool.exiftool_path,
            self.config_metadata_tool.exiv2_path,
        )
        self.metadata_tool_popup.settingsChanged.connect(self._sync_metadata_tool_settings)
        self.metadata_tool_popup.settingsSaveRequested.connect(self._save_metadata_tool_settings)
        self.speech_transcription_popup = SpeechTranscriptionPopup(self, self.speech_model_name)

    @Slot(bool)
    def show_metadata_tool_popup(self, checked=False):
        self.metadata_tool_popup.toggle(checked)

    def _install_ai_config_popup(self):
        self.ai_config_popup = AIConfigPopup(
            self,
            self.file_toolbar.widgetForAction(self.file_toolbar.action_ai_config),
        )
        self.ai_config_popup.set_values(self.config_ai.segmentation_dir, self.config_ai.speech_dir)
        self.ai_config_popup.settingsSaveRequested.connect(self._save_ai_settings)
        self.ai_config_popup.speechDownloadRequested.connect(self.show_speech_download_popup)
        self.speech_transcription_popup.downloadRequested.connect(self.show_speech_download_popup)
        self.speech_download_popup = None
        self.ai_config_popup.segmentationDownloadRequested.connect(self.show_segmentation_download_popup)
        self.segmentation_download_popup = None

    @Slot(bool)
    def show_ai_config_popup(self, checked=False):
        self._refresh_ai_config_status()
        self.ai_config_popup.toggle(checked)

    @staticmethod
    def _default_ai_backend():
        """The first model in the toolbox order whose file is in the segmentation folder."""
        found = find_segmentation_models()
        return next((key for key, _ in AI_BACKEND_OPTIONS if found.get(key)), AI_BACKEND_OPTIONS[0][0])

    @Slot()
    def show_segmentation_download_popup(self):
        folder = self.config_ai.segmentation_dir or str(app_config_dir() / "models" / "segmentation")
        if self.segmentation_download_popup is None:
            self.segmentation_download_popup = SegmentationModelDownloadPopup(self, folder)
            self.segmentation_download_popup.modelDownloaded.connect(self._segmentation_model_downloaded)
        else:
            self.segmentation_download_popup.set_folder(folder)
        self.segmentation_download_popup.show()
        self.segmentation_download_popup.raise_()
        self.segmentation_download_popup.activateWindow()

    @Slot(str, str)
    def _segmentation_model_downloaded(self, folder, model_name):
        """Use the download folder as segmentation folder; select the model if the current one is missing."""
        current = self.config_ai.segmentation_dir
        if not current or Path(current).resolve() != Path(folder).resolve():
            self.ai_config_popup.set_values(folder, self.config_ai.speech_dir)
            self._save_ai_settings(folder, self.config_ai.speech_dir)
        else:
            self._refresh_ai_config_status()
        if find_segmentation_models().get(self.ki_backend_id) is None:
            backend_id = segmentation_model_info(model_name).backend_id
            self.view_digizizer.set_ai_backend_options(AI_BACKEND_OPTIONS, backend_id)
            self._ai_backend_selected(backend_id)

    @Slot()
    def show_speech_download_popup(self):
        folder = self.config_ai.speech_dir or str(app_config_dir() / "models" / "speech")
        if self.speech_download_popup is None:
            self.speech_download_popup = SpeechModelDownloadPopup(self, folder)
            self.speech_download_popup.modelDownloaded.connect(self._speech_model_downloaded)
        else:
            self.speech_download_popup.set_folder(folder)
        self.speech_download_popup.show()
        self.speech_download_popup.raise_()
        self.speech_download_popup.activateWindow()

    @Slot(str, str)
    def _speech_model_downloaded(self, folder, model_name):
        """Use the download folder as speech model folder and select the new model."""
        current = self.config_ai.speech_dir
        if not current or Path(current).resolve() != Path(folder).resolve():
            self.ai_config_popup.set_values(self.config_ai.segmentation_dir, folder)
            self._save_ai_settings(self.config_ai.segmentation_dir, folder)
        else:
            self.speech_transcription_popup.refresh_models()
            self._refresh_ai_config_status()
        self.speech_transcription_popup.select_model(model_name)

    def _refresh_ai_config_status(self):
        self.ai_config_popup.set_status(find_segmentation_models(), available_speech_models())

    @Slot(str, str)
    def _save_ai_settings(self, segmentation_dir, speech_dir):
        settings = AIModelSettings(segmentation_dir, speech_dir)
        missing = [path for path in (settings.segmentation_dir, settings.speech_dir) if path and not Path(path).is_dir()]
        if missing:
            self.ai_config_popup.set_result_message(f"Folder not found: {missing[0]}")
            return
        if not write_ai_settings(self.ai_settings_path, settings):
            self.ai_config_popup.set_result_message("Save failed.")
            return
        previous = self.config_ai
        self.config_ai = settings
        apply_ai_settings(settings)
        self._refresh_ai_config_status()
        self.ai_config_popup.set_result_message(f"Saved: {self.ai_settings_path}")
        logger.info("AI model folders saved to: %s", self.ai_settings_path, extra={"finished": True})
        if settings.speech_dir != previous.speech_dir:
            self.speech_transcription_popup.refresh_models()
        if settings.segmentation_dir != previous.segmentation_dir:
            self._ai_model_folder_changed()

    def _ai_model_folder_changed(self):
        """Model files may differ in the new folder; reload the model if AI is on."""
        self.ki_model_path = None
        self._reload_ai_model()

    @Slot()
    def show_speech_transcription_popup(self):
        self.region_editor.set_speech_recording_target(None)
        self.speech_transcription_popup.show()
        self.speech_transcription_popup.raise_()
        self.speech_transcription_popup.activateWindow()

    @Slot()
    def _show_region_role_vocabulary_popup(self):
        term = self._select_controlled_vocabulary_term(
            TARGET_REGION_ROLE,
            self.region_editor.ui.txt_rrole_name.toPlainText(),
            self.region_editor.ui.txt_rrole_ident.toPlainText(),
        )
        if term is not None:
            self.region_editor.apply_region_role_term(term)

    @Slot()
    def _show_region_type_vocabulary_popup(self):
        term = self._select_controlled_vocabulary_term(
            TARGET_REGION_TYPE,
            self.region_editor.ui.txt_rctype_name.toPlainText(),
            self.region_editor.ui.txt_rctype_indent.toPlainText(),
        )
        if term is not None:
            self.region_editor.apply_region_type_term(term)

    @Slot()
    def _show_contributor_role_vocabulary_popup(self):
        current_role = self.region_editor.selected_contributor_role()
        term = self._select_controlled_vocabulary_term(
            TARGET_CONTRIBUTOR_ROLE,
            current_role,
            current_role,
        )
        if term is not None:
            self.region_editor.apply_contributor_role_term(term)

    def _select_controlled_vocabulary_term(self, target, current_name, current_identifier):
        dialog = ControlledVocabularyPopup(
            self,
            self.vocabulary_store,
            target,
            current_name=current_name,
            current_identifier=current_identifier,
        )
        if not dialog.exec():
            return None
        return dialog.selected_term

    @Slot(str, str, str)
    def _sync_metadata_tool_settings(self, tool, exiftool_path, exiv2_path):
        self.config_metadata_tool = MetadataToolSettings(tool, exiftool_path, exiv2_path)

    @Slot(str, str, str)
    def _save_metadata_tool_settings(self, tool, exiftool_path, exiv2_path):
        settings = MetadataToolSettings(tool, exiftool_path, exiv2_path)
        if not write_metadata_tool_settings(self.metadata_tool_settings_path, settings):
            self.metadata_tool_popup.set_result_message("Save failed.")
            return

        self.config_metadata_tool = settings
        self.metadata_tool_popup.set_result_message(f"Saved: {self.metadata_tool_settings_path}")
        logger.info("Metadata tool settings saved to: %s", self.metadata_tool_settings_path, extra={"finished": True})

    def _metadata_tool_path(self):
        return metadata_tool_path_from_settings(self.config_metadata_tool)

    def _metadata_tool_ready_for_import(self):
        result = test_metadata_tool(
            self.config_metadata_tool.tool,
            self.config_metadata_tool.path_for_tool(self.config_metadata_tool.tool),
        )
        if result.available:
            return True

        logger.warning(
            "Cannot import images because %s is not available: %s. Configure metadata tools first.",
            self.config_metadata_tool.tool,
            result.message,
            extra={"finished": True, "open": True},
        )
        if hasattr(self, "metadata_tool_popup"):
            self.metadata_tool_popup.set_result_message(result.message)
        return False

    @Slot(bool)
    def show_user_information_popup(self, checked=False):
        self.user_information_popup.toggle(checked)

    @Slot(str, str)
    def _sync_user_information(self, user, user_uri):
        self.user = user
        self.user_uri = user_uri

    def _segment_ai_background(self, coordinates):
        from graphis.app.ki.background import predict_background

        scene = self.digitizer_scene
        segmenter = scene.ai_controller.segmenter
        if (
            scene.ai_background_busy or scene._ai_current_mask is None
            or segmenter is None or not segmenter.is_ready
        ):
            return
        self._ai_background_context = (scene.ai_controller._image, scene._ai_current_mask)
        scene.ai_background_busy = True
        self.view_digizizer.ai_controls.setEnabled(False)
        worker = Worker(predict_background, segmenter, coordinates, scene.ai_controller.prompt_state())
        worker.signals.result.connect(self._ai_background_ready)
        worker.signals.error.connect(self._ai_background_failed)
        self.thread_pool.start(worker)
        self.start_waiting("Refining mask with background strokes...")

    def _finish_ai_background_wait(self):
        self.digitizer_scene.ai_background_busy = False
        self.view_digizizer.ai_controls.setEnabled(True)
        self.stop_waiting()

    def _ai_background_failed(self, error):
        self._ai_background_context = None
        self._finish_ai_background_wait()
        logger.error("AI background refinement failed: %s", error[2])
        QMessageBox.warning(self, "AI background brush", str(error[1]))

    def _ai_background_ready(self, result):
        context = self._ai_background_context
        self._ai_background_context = None
        self._finish_ai_background_wait()
        scene = self.digitizer_scene
        if (
            context is None or context[0] is not scene.ai_controller._image
            or context[1] is not scene._ai_current_mask or not scene.ai_mode_enabled
        ):
            logger.warning("Image or selection changed; paint the background again.")
            return
        mask, points, box = result
        if mask is None:
            return
        if not scene._accept_ai_mask_update(mask, destructive=True):
            logger.warning("Background correction removed too much; try a smaller stroke.")
            return
        scene.ai_controller.restore_prompt_state((points, box))
        scene._remove_ai_prompt_items_from(0)
        scene._draw_ai_mask(mask)
        logger.info("Mask refined with background strokes.", extra={"finished": True, "open": True})

    def _convert_ai_mask_to_polygons(self):
        from graphis.app.ki.mask_polygon import mask_to_polygons

        scene = self.digitizer_scene
        if self._ai_polygon_context is not None:
            return
        if scene._ai_current_mask is None:
            logger.warning("Create an AI mask before converting it to polygons.")
            return
        self._ai_polygon_context = (scene.image_id_db, scene._ai_current_mask)
        # One region per conversion: separate mask parts are dropped, only the largest polygon is kept.
        worker = Worker(mask_to_polygons, scene._ai_current_mask.copy(), largest_only=True)
        worker.signals.result.connect(self._ai_mask_polygons_ready)
        worker.signals.error.connect(self._ai_mask_polygons_failed)
        self.thread_pool.start(worker)
        logger.info("Converting AI mask to a polygon...")

    def _ai_mask_polygons_failed(self, error):
        self._ai_polygon_context = None
        logger.error("AI mask conversion failed: %s", error[2])
        QMessageBox.warning(self, "AI mask conversion", str(error[1]))

    def _ai_mask_polygons_ready(self, polygons):
        context = self._ai_polygon_context
        self._ai_polygon_context = None
        scene = self.digitizer_scene
        if context is None or context[0] != scene.image_id_db or context[1] is not scene._ai_current_mask:
            logger.warning("AI mask changed; convert the current mask again.")
            return
        if not polygons:
            logger.warning("No mask parts larger than 300 pixels could form a polygon.")
            return
        self._ensure_object_type_visible("polygon")
        # Conversion creates new regions rather than replacing a pending assignment target.
        scene.clear_geometry_assignment_target()
        scene.db.begin_undo_group("Convert AI mask to polygon")
        try:
            for coordinates in polygons:
                object_id, _ = scene.store_sightings("polygon", coordinates)
                # Interactive drawing already has an item; mask conversion must create one.
                data = json.loads(scene.db.db_load_object(object_id)["data"])
                scene.add_object("polygon", data, object_id, self.color_polygon)
        finally:
            scene.db.end_undo_group()
        scene.reset_ai_segmentation(reload_backend=False)
        self.view_digizizer.reset_ai_controls()
        logger.info("Created a polygon from the largest part of the AI mask.", extra={"finished": True, "open": True})

    def _install_file_toolbar(self):
        self.file_toolbar = FileToolBar(self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.file_toolbar)
        self.database_statistics_popup = DatabaseStatisticsPopup(
            self,
            self.file_toolbar.widgetForAction(self.file_toolbar.action_database_statistics),
        )
        self.database_statistics_popup.set_color("circle", self.color_circle)
        self.database_statistics_popup.set_color("point", self.color_point)
        self.database_statistics_popup.set_color("rectangle", self.color_rectangle)
        self.database_statistics_popup.set_color("polygon", self.color_polygon)
        self.database_statistics_popup.set_color("linestring", self.color_linestring)

    @Slot(bool)
    def show_database_statistics_popup(self, checked=False):
        self.database_statistics_popup.toggle(checked)

    def _install_region_operations_toolbar(self):
        self.geom_operations = RegionOperationsToolbar(self)

        self.geom_operations.setAllowedAreas(Qt.ToolBarArea.AllToolBarAreas)

        self.geom_operations.instructionSelected.connect(self.set_instruction)
        self.geom_operations.instructionCleared.connect(self._clear_geometry_operation)
        self.geom_operations.deleteRequested.connect(self.delete_geometry)
        self.geom_operations.deleteImageRegionRequested.connect(self.delete_object)
        self.geom_operations.visibilityToggled.connect(self.change_visibility)
        self.geom_operations.colorChanged.connect(lambda object_type, color: self.change_color(color, object_type))
        self.geom_operations.set_color("circle", self.color_circle)
        self.geom_operations.set_color("point", self.color_point)
        self.geom_operations.set_color("rectangle", self.color_rectangle)
        self.geom_operations.set_color("polygon", self.color_polygon)
        self.geom_operations.set_color("linestring", self.color_linestring)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.geom_operations)

    def _change_thumbnail_size(self, step_delta):
        self._set_thumbnail_size_index(self._thumbnail_size_index + step_delta)

    def _set_thumbnail_size_index(self, index):
        index = max(0, min(index, len(self._thumbnail_size_steps) - 1))
        if index == self._thumbnail_size_index:
            self._sync_thumbnail_size_controls()
            return

        self._thumbnail_size_index = index
        self.delegate.set_thumbnail_size(self._thumbnail_size_steps[index])
        self.table_preview.set_thumbnail_item_size(self._thumbnail_size_steps[index])
        self.table_preview.doItemsLayout()
        self.table_preview.viewport().update()
        self._sync_thumbnail_size_controls()

    def _sync_thumbnail_size_controls(self):
        self.table_preview.set_thumbnail_size_controls_enabled(
            self._thumbnail_size_index > 0,
            self._thumbnail_size_index < len(self._thumbnail_size_steps) - 1,
        )

    @Slot(int)
    def _image_view_rotation_changed(self, degrees):
        image_id = self.image_loading_image_id_db
        if not image_id or self.model is None:
            return
        self._visual_rotations_by_image_id[image_id] = int(degrees) % 360
        self.model.set_visual_rotation(image_id, degrees)

    def _preview_visual_rotation(self, image_id):
        if not image_id:
            return 0
        if self.model is not None:
            rotation = self.model.visual_rotation(image_id)
            self._visual_rotations_by_image_id[image_id] = rotation
            return rotation
        if image_id in self._visual_rotations_by_image_id:
            return self._visual_rotations_by_image_id[image_id]
        image = self.db.db_load_image_record(image_id) if self.db.db_is_set else None
        if image is None:
            return 0
        return image_metadata_visual_rotation(image["image_metadata"])

    def _preview_exif_orientation_present(self, image_id):
        if not image_id or self.model is None:
            return False
        return self.model.exif_orientation_present(image_id)

    @Slot()
    def _reset_image_view_rotation_to_exif(self):
        image_id = self.image_loading_image_id_db
        if not image_id or self.model is None:
            return
        if not self.model.exif_orientation_present(image_id):
            return
        self.view_digizizer.set_visual_rotation(self.model.exif_rotation(image_id))

    @Slot()
    def _show_image_metadata_popup(self):
        image_id = self.image_loading_image_id_db
        metadata = self.model.image_metadata(image_id) if image_id and self.model is not None else {}
        self.view_digizizer.toggle_metadata_popup(metadata)

    @Slot()
    def toggle_preview_table_mode(self):
        self.set_preview_table_mode(not self.table_preview.table_mode())

    @Slot(bool)
    def set_preview_table_mode(self, table_mode):
        self.table_preview.set_table_mode(table_mode)
        if not hasattr(self, "file_toolbar"):
            return

        action = self.file_toolbar.action_preview_table
        if table_mode:
            action.setIcon(resource_icon("preview-thumbnails.svg"))
            action.setText("Show thumbnail preview")
        else:
            action.setIcon(resource_icon("preview-table.svg"))
            action.setText("Show preview table")

    def _schedule_main_layout_refresh(self):
        self._main_layout_refresh_timer.start(0)

    def _refresh_main_layout(self):
        central_widget = self.centralWidget()
        if central_widget is not None:
            central_widget.updateGeometry()
            if central_widget.layout() is not None:
                central_widget.layout().invalidate()
                central_widget.layout().activate()

        if self.layout() is not None:
            self.layout().invalidate()
            self.layout().activate()

        if hasattr(self, "view_digizizer"):
            self.view_digizizer.updateGeometry()
            self.view_digizizer.viewport().update()

    def _region_dock_layout_settled(self):
        self._schedule_main_layout_refresh()
        self._fit_region_graph()

    def _fit_region_graph(self):
        if not hasattr(self, "region_editor"):
            return
        dock_visible = hasattr(self, "region_dock") and self.region_dock.isVisible()
        popout_visible = hasattr(self, "region_popout") and self.region_popout.isVisible()
        if not dock_visible and not popout_visible:
            return
        self.region_editor.fit_graph_delayed()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "region_dock") and self.region_dock.isFloating():
            self.region_dock.request_layout_settled()
        if hasattr(self, "popup_info") and self.popup_info.isVisible():
            self.popup_info.reposition()

    def _sync_region_operations_toolbar(self):
        if not hasattr(self, "geom_operations"):
            return
        self.geom_operations.set_visibility("circle", self.circle_visible)
        self.geom_operations.set_visibility("point", self.point_visible)
        self.geom_operations.set_visibility("rectangle", self.rectangle_visible)
        self.geom_operations.set_visibility("polygon", self.polygon_visible)
        self.geom_operations.set_visibility("linestring", self.linestring_visible)

    def _apply_scene_visibility(self):
        if not hasattr(self, "digitizer_scene"):
            return
        self.digitizer_scene.set_item_visibility("circle", self.circle_visible)
        self.digitizer_scene.set_item_visibility("point", self.point_visible)
        self.digitizer_scene.set_item_visibility("multipoint", self.point_visible)
        self.digitizer_scene.set_item_visibility("rectangle", self.rectangle_visible)
        self.digitizer_scene.set_item_visibility("polygon", self.polygon_visible)
        self.digitizer_scene.set_item_visibility("multipolygon", self.polygon_visible)
        self.digitizer_scene.set_item_visibility("linestring", self.linestring_visible)
        self.digitizer_scene.set_item_visibility("multilinestring", self.linestring_visible)

    def _ensure_object_type_visible(self, object_type):
        object_type = base_object_type(object_type)
        if object_type == "circle":
            self.circle_visible = True
        elif object_type == "rectangle":
            self.rectangle_visible = True
        elif object_type == "polygon":
            self.polygon_visible = True
        elif object_type == "point":
            self.point_visible = True
        elif object_type == "linestring":
            self.linestring_visible = True
        else:
            return

        self._apply_scene_visibility()
        self._sync_region_operations_toolbar()

    def _reset_geometry_visibility(self):
        self.circle_visible = True
        self.point_visible = True
        self.rectangle_visible = True
        self.polygon_visible = True
        self.linestring_visible = True
        self._apply_scene_visibility()
        self._sync_region_operations_toolbar()

    def _object_type_visible(self, object_type):
        object_type = base_object_type(object_type)
        if object_type == "circle":
            return self.circle_visible
        if object_type == "point":
            return self.point_visible
        if object_type == "linestring":
            return self.linestring_visible
        if object_type == "rectangle":
            return self.rectangle_visible
        if object_type == "polygon":
            return self.polygon_visible
        return True

    def _geometry_operation_state_changed(self, _active):
        self._sync_geometry_action_availability()

    def _sync_geometry_action_availability(self):
        if not hasattr(self, "geom_operations") or not hasattr(self, "digitizer_scene"):
            return
        selected_item = self.digitizer_scene.active_geometry_item()
        selected_object_type = getattr(selected_item, "object_type", None) if selected_item is not None else None
        self.geom_operations.set_action_availability(
            has_selection=selected_item is not None,
            selected_object_type=selected_object_type,
            operation_active=self.digitizer_scene.instruction_active,
            has_region=selected_item is not None or self.current_item is not None,
        )
        if self.digitizer_scene.current_instruction == Instructions.No_Instruction:
            self.geom_operations.clear_active_tool()

    def _install_status_bar(self):
        status_bar = QStatusBar(self)
        status_bar.setObjectName("statusBar")
        status_bar.setFixedHeight(40)
        status_bar.setMinimumSize(QtCore.QSize(0, 40))
        status_bar.setSizeGripEnabled(False)
        status_bar.setStyleSheet("""
            QStatusBar {
                background-color: rgb(85, 85, 85);
                border: none;
            }
            QStatusBar::item {
                border: none;
            }
        """)
        self.setStatusBar(status_bar)
        self.status_bar = status_bar

        self.graphis_status = GraphisStatusBar(software_version, self.status_bar)
        self.status_bar.addWidget(self.graphis_status, 1)

    def _install_log_popup(self):
        self.logging_current_level = logging.INFO
        self.popup_info = LogPopup(self, self.graphis_status.btn_info_popup)
        self.popup_info.set_level_style(LOGGING_STYLE[logging.INFO]["frame"])
        self.graphis_status.btn_info_popup.clicked.connect(self.show_info_popup)

    def _install_logging_handler(self):
        self.handler = QtHandler(self.handle_output_logging)
        self.handler.setFormatter(logging.Formatter("%(levelname)s:  %(message)s"))
        logging.getLogger().addHandler(self.handler)
        logging.getLogger().setLevel(logging.INFO)

    def _install_output_wrappers(self):
        self.stdout = OutputWrapper(self, True)
        self.stdout.outputWritten.connect(self.handle_output)
        self.stderr = OutputWrapper(self, False)
        self.stderr.outputWritten.connect(self.handle_output)

    def _warn_if_config_fallback_used(self):
        if not self.config_success:
            logger.warning("Config file is not properly set. Falling back on malformed options.")

    def start_waiting(self, message="Working..."):
        self.graphis_status.set_message(message)
        self.graphis_status.start_spinner()

    def stop_waiting(self, message="Ready"):
        self.graphis_status.stop_spinner()
        self.graphis_status.set_message(message)

    def show_region_dock(self):
        self.dock_region_editor()
        self._fit_region_graph()

    def toggle_region_editor_window(self):
        if self.region_popout.isVisible():
            self.dock_region_editor()
        else:
            self.pop_out_region_editor()

    def pop_out_region_editor(self):
        if self.region_popout.isVisible():
            self.region_popout.raise_()
            self.region_popout.activateWindow()
            self._fit_region_graph()
            return

        if self.region_popout.has_editor():
            self.region_popout.normalize_window_state()
            self.region_popout.show()
            self.region_popout.raise_()
            self.region_popout.activateWindow()
            self._fit_region_graph()
            return

        if self.region_dock.widget() is self.region_editor:
            self.region_dock.setWidget(None)
        self.region_editor.setParent(None)
        self.region_popout.set_editor(self.region_editor)
        self.region_dock.hide()
        self.region_popout.normalize_window_state()
        self.region_popout.show()
        self.region_popout.raise_()
        self.region_popout.activateWindow()
        self._schedule_main_layout_refresh()
        self._fit_region_graph()

    def dock_region_editor(self):
        if self.region_dock.widget() is self.region_editor and not self.region_popout.isVisible():
            self.region_dock.show_or_raise(Qt.DockWidgetArea.RightDockWidgetArea)
            self.region_dock.restore_preferred_docked_size(Qt.DockWidgetArea.RightDockWidgetArea)
            self._fit_region_graph()
            return

        if self.region_popout.isVisible():
            self.region_popout.hide()
        self.region_popout.normalize_window_state()

        editor = self.region_popout.take_editor() or self.region_editor
        if editor.parent() is not None:
            editor.setParent(None)

        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.region_dock)
        self.region_dock.setWidget(editor)
        self.region_dock.setFloating(False)
        self.region_dock.show_or_raise(Qt.DockWidgetArea.RightDockWidgetArea)
        self.region_dock.restore_preferred_docked_size(Qt.DockWidgetArea.RightDockWidgetArea)
        self._schedule_main_layout_refresh()
        self._fit_region_graph()

    def closeEvent(self, event):
        if getattr(self, "_operation_event_filter_app", None) is not None:
            self._operation_event_filter_app.removeEventFilter(self)
            self._operation_event_filter_app = None
        if hasattr(self, "region_popout"):
            self.region_popout.force_close()
        super().closeEvent(event)

    @Slot(int)
    def _graph_object_selected(self, object_id):
        if self._graph_selection_active:
            return

        self._request_object_selection(object_id)

    def _select_geometry_part(self, object_id, part_index, ring_index=0):
        if not self._request_object_selection(object_id):
            return
        self._clear_geometry_operation()
        if self.digitizer_scene.activate_geometry_part(object_id, part_index, ring_index):
            self.region_editor.select_geometry_part(object_id, part_index, ring_index)
            self._center_image_view_on_active_geometry()

    @Slot(int)
    def _request_object_selection(self, object_id):
        if self.current_item and self.current_item.get("id") == object_id:
            self._clear_geometry_operation()
            self.digitizer_scene.activate_object(object_id)
            self._graph_selection_active = True
            try:
                self.region_editor.select_object(object_id)
            finally:
                self._graph_selection_active = False
            return True

        if self.current_item and not self._guard_unsaved_region_metadata_changes("select another image region"):
            return False

        return self.load_data(object_id, check_unsaved=False)

    def _object_selection_cleared(self):
        if self._graph_selection_active:
            return

        if not self._guard_unsaved_region_metadata_changes("clear the selected image region"):
            return

        self._graph_selection_active = True
        try:
            self._clear_geometry_operation()
            self.clear_entries(action_stay_active=True, reset_visibility=False)
            self.digitizer_scene.clear_active_object()
            self.region_editor.clear_selection()
        finally:
            self._graph_selection_active = False

    @Slot(int, int, str)
    def merge_image_regions(self, source_object_id, target_object_id, mode, target_part_index=None):
        if not self._db_ready_for("merge image regions"):
            return
        if source_object_id == target_object_id:
            return
        if not self._guard_unsaved_region_metadata_changes("merge image regions"):
            return

        source_row = self.db.db_load_object(source_object_id)
        target_row = self.db.db_load_object(target_object_id)
        if source_row is None or target_row is None:
            logger.warning("Cannot merge image regions because one of the selected regions no longer exists.")
            return
        if source_row["image"] != target_row["image"]:
            logger.warning("Cannot merge image regions from different images.")
            return

        source_data = json.loads(source_row["data"])
        target_data = json.loads(target_row["data"])
        try:
            merged_data = merge_region_geometries(
                target_data,
                source_data,
                target_row["img_width"],
                target_row["img_height"],
                mode,
                target_part_index=target_part_index,
            )
        except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError) as err:
            logger.warning("Cannot merge image regions: %s", err)
            return

        merged_object_type = object_type_from_region(merged_data)
        if merged_object_type == "invalid":
            logger.warning("Cannot merge image regions because the merged geometry is invalid.")
            return

        label = "Merge image region geometry"
        self.db.begin_undo_group(label)
        try:
            self.db.update_object(
                obj_id=target_object_id,
                data=merged_data,
                object_type=merged_object_type,
                action_label=label,
            )
            self.digitizer_scene.delete_object(source_object_id)
            self.db.db_delete_geometry(source_object_id)
        finally:
            self.db.end_undo_group()

        self._refresh_after_region_geometry_merge(target_object_id, merged_data, merged_object_type)
        logger.info(
            "Merged image region %s into image region %s as %s.",
            source_object_id,
            target_object_id,
            merged_object_type,
            extra={"finished": True, "open": True},
        )

    @Slot(str)
    def create_empty_multigeometry_container(self, object_type):
        if not self._db_ready_for("create multi-geometry container"):
            return
        if not self._current_image_ready_for_region_edit("create multi-geometry container"):
            return
        if not self._guard_unsaved_region_metadata_changes("create a multi-geometry container"):
            return

        container_id = self._create_multigeometry_container(
            object_type,
            child_object_ids=(),
            action_label=f"Create {object_type} container",
        )
        if container_id is not None:
            self._refresh_after_region_grouping(container_id)
            logger.info("Created %s image region container.", object_type, extra={"finished": True, "open": True})

    @Slot(object, str)
    def group_image_regions(self, object_ids, object_type):
        if not self._db_ready_for("group image regions"):
            return
        if not self._current_image_ready_for_region_edit("group image regions"):
            return
        if not self._guard_unsaved_region_metadata_changes("group image regions"):
            return

        child_object_ids = self._valid_group_child_ids(object_ids, object_type)
        if len(child_object_ids) < 2:
            logger.warning("Select at least two compatible image regions to group.")
            return

        container_id = self._create_multigeometry_container(
            object_type,
            child_object_ids=child_object_ids,
            action_label=f"Group image regions as {object_type}",
        )
        if container_id is not None:
            self._refresh_after_region_grouping(container_id)
            logger.info(
                "Grouped %s image regions as %s.",
                len(child_object_ids),
                object_type,
                extra={"finished": True, "open": True},
            )

    @Slot(object, int)
    def group_image_regions_into_container(self, child_object_ids, container_object_id):
        if not self._db_ready_for("group image regions"):
            return
        if not self._current_image_ready_for_region_edit("group image regions"):
            return
        if not self._guard_unsaved_region_metadata_changes("group image regions"):
            return

        container_row = self.db.db_load_object(container_object_id)
        if container_row is None:
            logger.warning("Cannot group image regions because the container no longer exists.")
            return
        container_data = json.loads(container_row["data"])
        container_type = object_type_from_region(container_data)
        if container_type == "invalid":
            container_type = container_row["object_type"]
        child_ids = self._valid_group_child_ids(child_object_ids, container_type, container_object_id)
        if not child_ids:
            logger.warning("Select compatible child image regions before grouping into this container.")
            return

        label = f"Group image regions into {container_type}"
        try:
            combined_data = combine_multigeometry_regions(
                container_data,
                [json.loads(self.db.db_load_object(object_id)["data"]) for object_id in child_ids],
                container_row["img_width"],
                container_row["img_height"],
                container_type,
            )
        except (KeyError, TypeError, ValueError) as err:
            logger.warning("Cannot build multi-geometry: %s", err)
            return
        if self._region_parent_object_map().get(container_object_id) in child_ids:
            for key in PARENT_KEYS:
                combined_data.pop(key, None)
        self.db.begin_undo_group(label)
        try:
            self.db.update_object(
                obj_id=container_object_id,
                data=combined_data,
                object_type=container_type,
                action_label=label,
            )
            self._absorb_multigeometry_sources(child_ids, container_object_id, label)
        finally:
            self.db.end_undo_group()

        self._refresh_after_region_grouping(container_object_id)
        logger.info(
            "Grouped %s image regions into image region %s.",
            len(child_ids),
            container_object_id,
            extra={"finished": True, "open": True},
        )

    def _current_image_ready_for_region_edit(self, action):
        if self.current_image is None or self.image_loading_image_id_db == 0:
            logger.warning("Cannot %s because no image is displayed.", action)
            return False
        return True

    def _create_multigeometry_container(self, object_type, child_object_ids=(), action_label=None):
        if object_type not in {"multipoint", "multilinestring", "multipolygon"}:
            logger.warning("Unsupported multi-geometry container type: %s", object_type)
            return None

        container_id = None
        if child_object_ids:
            rows = [self.db.db_load_object(object_id) for object_id in child_object_ids]
            try:
                # The first selected region supplies the region-level metadata.
                data = copy.deepcopy(json.loads(rows[0]["data"]))
                data["regionBoundary"] = {
                    "rbShape": object_type,
                    "rbUnit": data.get("regionBoundary", {}).get("rbUnit", "pixel"),
                    "rbCoordinates": "[]",
                }
                container_id = rows[0]["id"]
                if self._region_parent_object_map().get(container_id) in child_object_ids:
                    for key in PARENT_KEYS:
                        data.pop(key, None)
                data = combine_multigeometry_regions(
                    data,
                    [json.loads(row["data"]) for row in rows],
                    rows[0]["img_width"],
                    rows[0]["img_height"],
                    object_type,
                )
            except (KeyError, TypeError, ValueError) as err:
                logger.warning("Cannot build multi-geometry: %s", err)
                return None
        else:
            data = self._new_multigeometry_region_data(object_type)
        label = action_label or f"Create {object_type} container"
        self.db.begin_undo_group(label)
        try:
            if container_id is None:
                container_id = self.db.db_store_object(self.image_loading_image_id_db, object_type, data)
            else:
                self.db.update_object(
                    obj_id=container_id, data=data, object_type=object_type, action_label=label
                )
            if child_object_ids:
                self._absorb_multigeometry_sources(child_object_ids, container_id, label)
        finally:
            self.db.end_undo_group()
        return container_id

    def _absorb_multigeometry_sources(self, source_ids, target_id, label):
        source_ids = set(source_ids) - {target_id}
        # Preserve ordinary hierarchy links to regions whose geometry is absorbed.
        for child_id, parent_id in self._region_parent_object_map().items():
            if parent_id in source_ids and child_id not in source_ids and child_id != target_id:
                self._assign_region_parent([child_id], target_id, label)
        for object_id in source_ids:
            self.db.db_delete_geometry(object_id)

    def _new_multigeometry_region_data(self, object_type):
        image = Path(self.current_image["name"]) if self.current_image else Path("image")
        dt = datetime.datetime.now().strftime("%y%m%dT%H:%M:%S")
        base_type = base_object_type(object_type)
        region_role_name = self.get_config_role(base_type, "region_role_name")
        region_role_identifier = get_image_region_role(region_role_name)
        name_region = self.get_config_role(base_type, "region_name_prefix")

        data = {
            "regionBoundary": {
                "rbShape": object_type,
                "rbUnit": "pixel",
                "rbCoordinates": "[]",
                "rbMbPartDetails": [],
            },
            "rCtype": [
                {
                    "identifiers": [self.get_config_role(base_type, "rctype_identifier")],
                    "name": self.get_config_role(base_type, "rctype_name"),
                }
            ],
        }
        data = put_text_to_dict_or_remove(data, "rId", f"{image.stem}_{dt}")
        data = put_lang_alt_to_dict_or_remove(data, "name", name_region, [])
        data = put_struct_to_dict_or_remove(data, "rRole", region_role_identifier, region_role_name)
        data = put_struc_tag(
            data,
            self.config_default["CONTRIBUTOR_TAG"],
            self.get_config_role(base_type, "region_creator_role"),
            indentifier=self.user_information_popup.txt_user_indent.toPlainText(),
            name=self.user_information_popup.txt_user_name.toPlainText(),
        )
        return data

    def _begin_parent_assignment(self, child_object_id):
        if not self._db_ready_for("assign parent") or not self._current_image_ready_for_region_edit("assign parent"):
            return
        if not self._guard_unsaved_region_metadata_changes("assign parent"):
            return
        self._clear_geometry_operation()
        self._cancel_parent_assignment()
        self._parent_assignment = (child_object_id, self.image_loading_image_id_db)
        for view in (self.region_editor.ui.graphicsView, self.view_digizizer):
            view.viewport().setCursor(Qt.CursorShape.CrossCursor)
        self.region_editor.set_selection_guidance(
            "Choose a parent node in the graph or a geometry in the image. Press Escape to cancel."
        )

    def _cancel_parent_assignment(self):
        self._parent_assignment = None
        self._merge_target_selection = None
        self.region_editor.set_selection_guidance()
        for view in (self.region_editor.ui.graphicsView, self.view_digizizer):
            view.viewport().unsetCursor()
        self.statusBar().clearMessage()

    def _begin_merge_target_selection(self, source_id, mode):
        if not self._db_ready_for("merge geometry") or not self._current_image_ready_for_region_edit("merge geometry"):
            return
        if not self._guard_unsaved_region_metadata_changes("merge geometry"):
            return
        self._clear_geometry_operation()
        self._cancel_parent_assignment()
        self._merge_target_selection = (source_id, mode, self.image_loading_image_id_db)
        for view in (self.region_editor.ui.graphicsView, self.view_digizizer):
            view.viewport().setCursor(Qt.CursorShape.CrossCursor)
        target = (
            "an existing compatible multigeometry" if mode == "multigeometry" else "a containing rectangle or polygon"
        )
        self.region_editor.set_selection_guidance(f"Choose {target} in either view. Press Escape to cancel.")

    def _pick_merge_target(self, target_id, target_part_index=None, target_ring_index=0):
        source_id, requested_mode, image_id = self._merge_target_selection
        if image_id != self.image_loading_image_id_db:
            self._cancel_parent_assignment()
            return
        target_id = int(target_id)
        source = self.db.db_load_object(source_id)
        target = self.db.db_load_object(target_id)
        if source is None or target is None or source["image"] != image_id or target["image"] != image_id:
            self._cancel_parent_assignment()
            return
        source_data, target_data = json.loads(source["data"]), json.loads(target["data"])
        mode = object_type_from_region(target_data) if requested_mode == "multigeometry" else requested_mode
        if (
            source_id == target_id
            or (requested_mode == "inner_polygon" and target_ring_index > 0)
            or (requested_mode == "multigeometry" and mode not in {"multipoint", "multilinestring", "multipolygon"})
            or mode not in valid_region_geometry_merge_modes(
                source_data, target_data, target["img_width"], target["img_height"],
                target_part_index=target_part_index,
            )
        ):
            if source_id != target_id and mode in {"multipoint", "multilinestring", "multipolygon"}:
                try:
                    merge_region_geometries(
                        target_data, source_data, target["img_width"], target["img_height"], mode
                    )
                except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError) as err:
                    logger.warning("Cannot merge geometry: %s", err)
                    return
            logger.warning("Choose another target: this geometry is incompatible with the selected merge.")
            return
        self._cancel_parent_assignment()
        if mode == "inner_polygon" and target_part_index is not None:
            self.merge_image_regions(source_id, target_id, mode, target_part_index=target_part_index)
        else:
            self.merge_image_regions(source_id, target_id, mode)

    def _pick_region_parent(self, parent_object_id):
        child_object_id, image_id = self._parent_assignment
        if image_id != self.image_loading_image_id_db:
            self._cancel_parent_assignment()
            return
        parent_object_id = int(parent_object_id)
        if child_object_id == parent_object_id or self._would_create_parent_cycle(child_object_id, parent_object_id):
            logger.warning("Choose another parent: this assignment would create a circular hierarchy.")
            return
        child = self.db.db_load_object(child_object_id)
        parent = self.db.db_load_object(parent_object_id)
        if child is None or parent is None or child["image"] != image_id or parent["image"] != image_id:
            self._cancel_parent_assignment()
            return
        self._assign_region_parent([child_object_id], parent_object_id, "Assign region parent")
        self._cancel_parent_assignment()
        self._refresh_after_region_grouping(child_object_id)

    @Slot(int)
    def detach_region_parent(self, object_id):
        if not self._db_ready_for("detach region parent") or not self._guard_unsaved_region_metadata_changes(
            "detach region parent"
        ):
            return
        row = self.db.db_load_object(object_id)
        if row is None or row["image"] != self.image_loading_image_id_db:
            return
        data = json.loads(row["data"])
        if not any(key in data for key in PARENT_KEYS):
            return
        for key in PARENT_KEYS:
            data.pop(key, None)
        self.db.update_object(obj_id=object_id, data=data, action_label="Detach region from parent")
        self._refresh_after_region_grouping(object_id)
        logger.info("Detached image region from its parent.", extra={"finished": True, "open": True})

    @Slot(int, int)
    def detach_geometry_part(self, object_id, part_index):
        if not self._db_ready_for("detach geometry part") or not self._guard_unsaved_region_metadata_changes(
            "detach geometry part"
        ):
            return
        row = self.db.db_load_object(object_id)
        if row is None or row["image"] != self.image_loading_image_id_db:
            return
        original = json.loads(row["data"])
        try:
            part = multigeometry_part(original, part_index)
            remaining, boundary = detach_multigeometry_part(
                original, row["img_width"], row["img_height"], part_index
            )
        except (IndexError, KeyError, TypeError, ValueError, json.JSONDecodeError) as err:
            logger.warning("Cannot detach geometry part: %s", err)
            return
        detached = copy.deepcopy(original)
        for key in (*PARENT_KEYS, *CHILD_KEYS, "rId", "RId"):
            detached.pop(key, None)
        detached["rId"] = str(uuid.uuid4())
        detached["regionBoundary"] = boundary
        # Part details recorded when the region was combined restore its identity.
        used_region_ids = {
            region_identifier(json.loads(other["data"])) for other in self.db.db_load_objects_image(row["image"])
        }
        apply_part_details_to_region(detached, part, used_region_ids)
        self.db.begin_undo_group("Detach geometry as new image region")
        try:
            self.db.update_object(
                obj_id=object_id, data=remaining, object_type=object_type_from_region(remaining),
                action_label="Detach geometry part",
            )
            detached_id = self.db.db_store_object(row["image"], object_type_from_region(detached), detached)
        finally:
            self.db.end_undo_group()
        self._refresh_after_region_grouping(detached_id)
        logger.info("Detached geometry as a new image region.", extra={"finished": True, "open": True})

    def _assign_region_parent(self, child_object_ids, parent_object_id, action_label):
        parent_object_id = int(parent_object_id)
        parent_row = self.db.db_load_object(parent_object_id)
        if parent_row is None:
            return
        parent_data = json.loads(parent_row["data"])
        parent_rid = region_identifier(parent_data)
        self.db.begin_undo_group(action_label)
        try:
            if not parent_rid:
                parent_rid = str(uuid.uuid4())
                parent_data["rId"] = parent_rid
                self.db.update_object(obj_id=parent_object_id, data=parent_data, action_label=action_label)
            self._assign_region_members(child_object_ids, parent_object_id, parent_rid, action_label)
        finally:
            self.db.end_undo_group()

    def _assign_region_members(self, child_object_ids, parent_object_id, parent_rid, action_label):
        for child_object_id in child_object_ids:
            child_object_id = int(child_object_id)
            if child_object_id == parent_object_id:
                continue
            child_row = self.db.db_load_object(child_object_id)
            if child_row is None:
                continue
            if self._would_create_parent_cycle(child_object_id, parent_object_id):
                logger.warning("Cannot group image region %s because it would create a parent cycle.", child_object_id)
                continue
            child_data = json.loads(child_row["data"])
            for key in PARENT_KEYS:
                child_data.pop(key, None)
            child_data["rMemberOf"] = parent_rid
            self.db.update_object(
                obj_id=child_object_id,
                data=child_data,
                log_validation=False,
                action_label=action_label,
            )

    def _would_create_parent_cycle(self, child_object_id, parent_object_id):
        parent_map = self._region_parent_object_map()
        current = parent_object_id
        visited = set()
        while current is not None and current not in visited:
            if current == child_object_id:
                return True
            visited.add(current)
            current = parent_map.get(current)
        return False

    def _regions_of(self, image_id):
        """Region data of ``image_id``; the open image reuses its parsed and validated regions."""
        regions = getattr(self, "image_regions", None)
        if regions is None or regions.db is not self.db or regions.image_id != image_id:
            return OpenImageRegions(self.db, image_id)
        return regions

    def _region_parent_object_map(self):
        return self._regions_of(self.image_loading_image_id_db).parent_map()

    def _valid_group_child_ids(self, object_ids, object_type, parent_object_id=None):
        accepted_shapes = self._accepted_child_shapes(object_type)
        valid_ids = []
        for object_id in dict.fromkeys(object_ids or ()):
            if parent_object_id is not None and int(object_id) == int(parent_object_id):
                continue
            row = self.db.db_load_object(int(object_id))
            if row is None or row["image"] != self.image_loading_image_id_db:
                continue
            data = json.loads(row["data"])
            shape = object_type_from_region(data)
            if shape in accepted_shapes:
                valid_ids.append(int(object_id))
        return valid_ids

    def _accepted_child_shapes(self, object_type):
        if object_type == "multipoint":
            return {"point", "multipoint"}
        if object_type == "multilinestring":
            return {"linestring", "multilinestring"}
        if object_type == "multipolygon":
            return {"polygon", "multipolygon", "rectangle"}
        return set()

    def _refresh_after_region_grouping(self, selected_object_id):
        self._refresh_after_history_replay(selected_object_id)

    def _refresh_after_region_geometry_merge(self, selected_object_id, selected_data, object_type):
        self.clear_entries(reset_visibility=False)
        self.current_item = {
            "id": selected_object_id,
            "data": copy.deepcopy(selected_data),
            "object_type": object_type,
        }
        self.parse_show_data(object_type, self.current_item["data"])
        self._current_item_form_baseline = self._metadata_from_region_form(show_errors=False)
        self.model_image_region.load(self.current_item["data"])
        self.region_editor.resize_current_region_headers()

        self.digitizer_scene.delete_object(selected_object_id)
        if "regionBoundary" in selected_data:
            self.digitizer_scene.add_object(
                object_type,
                selected_data,
                selected_object_id,
                self._geometry_color(object_type),
            )
        self._apply_scene_visibility()
        self.image_region_view_load_all_image()
        self.digitizer_scene.activate_object(selected_object_id)
        self._graph_selection_active = True
        try:
            self.region_editor.select_object(selected_object_id)
        finally:
            self._graph_selection_active = False
        self._sync_undo_redo_actions()

    def _geometry_color(self, object_type):
        object_type = base_object_type(object_type)
        if object_type == "rectangle":
            return self.color_rectangle
        if object_type == "circle":
            return self.color_circle
        if object_type == "point":
            return self.color_point
        if object_type == "linestring":
            return self.color_linestring
        return self.color_polygon

    def _db_ready_for(self, requested_action: str, require_database: bool = True):
        message = self.db.blocked_message(requested_action, require_database=require_database)
        if message:
            logger.warning(message)
            return False
        return True

    def _sync_undo_redo_actions(self):
        if not hasattr(self, "file_toolbar") or not hasattr(self, "db"):
            return

        image_id = self._current_history_image_id()
        can_use_history = self.db.db_is_set and not self.db.is_busy and image_id is not None
        can_undo = can_use_history and self.db.can_undo(image_id)
        can_redo = can_use_history and self.db.can_redo(image_id)
        undo_label = self.db.undo_label(image_id) if image_id is not None else ""
        redo_label = self.db.redo_label(image_id) if image_id is not None else ""

        self.file_toolbar.action_undo.setEnabled(can_undo)
        self.file_toolbar.action_redo.setEnabled(can_redo)
        self.file_toolbar.action_undo.setToolTip(
            f"Undo {undo_label} on current image" if undo_label else "Nothing to undo for current image"
        )
        self.file_toolbar.action_redo.setToolTip(
            f"Redo {redo_label} on current image" if redo_label else "Nothing to redo for current image"
        )

    def undo(self):
        if not self._db_ready_for("undo"):
            return

        image_id = self._current_history_image_id()
        if image_id is None:
            logger.warning("Cannot undo: no image is displayed.")
            return

        selected_object_id = self._selected_object_id()
        label = self.db.undo(image_id)
        if not label:
            self._sync_undo_redo_actions()
            logger.info("Nothing to undo for the current image.", extra={"finished": True})
            return

        self._refresh_after_history_replay(selected_object_id)
        self.graphis_status.set_message(f"Undid {label}")
        logger.info("Undo: %s", label, extra={"finished": True})

    def redo(self):
        if not self._db_ready_for("redo"):
            return

        image_id = self._current_history_image_id()
        if image_id is None:
            logger.warning("Cannot redo: no image is displayed.")
            return

        selected_object_id = self._selected_object_id()
        label = self.db.redo(image_id)
        if not label:
            self._sync_undo_redo_actions()
            logger.info("Nothing to redo for the current image.", extra={"finished": True})
            return

        self._refresh_after_history_replay(selected_object_id)
        self.graphis_status.set_message(f"Redid {label}")
        logger.info("Redo: %s", label, extra={"finished": True})

    def _current_history_image_id(self):
        if self.image_loading or self.current_image is None or self.image_loading_image_id_db == 0:
            return None
        return self.image_loading_image_id_db

    def _selected_object_id(self):
        if self.current_item is not None:
            return self.current_item.get("id")
        selected_item = self.digitizer_scene.active_geometry_item()
        if selected_item is None:
            return None
        return getattr(selected_item, "obj_id", None)

    def _refresh_after_history_replay(self, selected_object_id=None):
        self._clear_geometry_operation()
        self.current_item = None
        self._current_item_form_baseline = None
        self.model_image_region.clear()
        self.region_editor.clear_region_form()

        if self.current_image is None or self.image_loading_image_id_db == 0:
            self.model_image_region_all.clear()
            self.region_editor.clear_graph()
            self._sync_geometry_action_availability()
            self._sync_undo_redo_actions()
            return

        image_item = getattr(self.digitizer_scene, "image_item", None)
        pixmap = image_item.pixmap() if image_item is not None else QPixmap()
        if pixmap.isNull():
            self.image_region_view_load_all_image()
            self._sync_geometry_action_availability()
            self._sync_undo_redo_actions()
            return

        keep_ai_active = self._ai_active_or_requested()
        self._ai_keep_model_on_image_change = keep_ai_active
        try:
            self.digitizer_scene.change_image(pixmap.toImage())
        finally:
            self._ai_keep_model_on_image_change = False
        self._prepare_ai_for_current_image(activate=keep_ai_active)
        self.view_digizizer.apply_smooth_pixmap_to_scene()
        self.view_digizizer.set_exif_rotation_available(
            self._preview_exif_orientation_present(self.image_loading_image_id_db)
        )
        self.view_digizizer.reset_overlay_position()
        self.digitizer_scene.image_id_db = self.image_loading_image_id_db
        self._load_scene_objects(self.image_loading_image_id_db)
        self._apply_scene_visibility()
        self.image_region_view_load_all_image()

        if selected_object_id is not None and self.db.db_load_object(selected_object_id) is not None:
            self.load_data(selected_object_id)
        else:
            self._graph_selection_active = True
            try:
                self.digitizer_scene.clear_active_object()
                self.region_editor.clear_selection()
            finally:
                self._graph_selection_active = False

        self._sync_geometry_action_availability()
        self._sync_undo_redo_actions()

    def _reload_preview_counts(self):
        if not hasattr(self, "model") or self.model is None:
            return

        self._apply_preview_summary_totals(self.image_region_summaries)

        self.model.layoutAboutToBeChanged.emit()
        for preview in self.model.previews:
            counts = self.image_region_summaries.get(preview.id, {})
            preview.rectangle_number = counts.get("rectangle", 0)
            preview.polygon_number = counts.get("polygon", 0) + counts.get("multipolygon", 0)
            preview.circle_number = counts.get("circle", 0)
            preview.point_number = counts.get("point", 0) + counts.get("multipoint", 0)
            preview.linestring_number = counts.get("linestring", 0) + counts.get("multilinestring", 0)
            preview.error_image = counts.get("error_image", False)
            preview.warning_image = counts.get("warning_image", False)
        self.model.layoutChanged.emit()

    def _empty_image_region_summary(self):
        return {
            "rectangle": 0,
            "polygon": 0,
            "circle": 0,
            "linestring": 0,
            "point": 0,
            "multipoint": 0,
            "multilinestring": 0,
            "multipolygon": 0,
            "error_image": False,
            "warning_image": False,
        }

    def _image_region_summaries(self):
        summaries = {}
        for image in self.db.db_load_images_list():
            summaries[image["id"]] = self._empty_image_region_summary()

        rows_by_image = {}
        for obj in self.db.db_load_objects_all():
            image_id = obj["image"]
            rows_by_image.setdefault(image_id, []).append(dict(obj))

        for image_id, rows in rows_by_image.items():
            try:
                validation_result = validate_image_object_result(
                    rows,
                    img_width=rows[0]["img_width"],
                    img_height=rows[0]["img_height"],
                )
            except Exception:
                validation_result = None
            summaries[image_id] = self._image_region_summary_from_rows(rows, validation_result)

        return summaries

    def _validation_findings(self, validation_result):
        if validation_result is None:
            return None
        if hasattr(validation_result, "issues"):
            return list(validation_result.issues) + list(validation_result.overview_issues)
        return list(validation_result)

    def _image_region_summary_from_rows(self, rows, validation_result):
        summary = self._empty_image_region_summary()

        for obj in rows:
            try:
                region = json.loads(obj["data"])
            except (TypeError, json.JSONDecodeError):
                summary["error_image"] = True
                continue

            object_type = object_type_from_region(region)
            if object_type not in {
                "rectangle",
                "polygon",
                "multipolygon",
                "circle",
                "point",
                "multipoint",
                "linestring",
                "multilinestring",
            }:
                if "regionBoundary" in region and obj["object_type"] in {
                    "rectangle",
                    "polygon",
                    "multipolygon",
                    "linestring",
                    "multilinestring",
                    "circle",
                    "point",
                    "multipoint",
                }:
                    object_type = obj["object_type"]
                else:
                    object_type = None
            if object_type:
                summary[object_type] += 1

        validation_findings = self._validation_findings(validation_result)
        if validation_findings is None:
            summary["error_image"] = True
        else:
            if any(issue.severity == "error" for issue in validation_findings):
                summary["error_image"] = True
            if any(issue.severity == "warning" for issue in validation_findings):
                summary["warning_image"] = True

        return summary

    def _refresh_image_region_summary(self, image_id):
        image = self.db.db_load_image_record(image_id)
        if not image:
            self.image_region_summaries.pop(image_id, None)
            self._reload_preview_counts()
            return None

        regions = self._regions_of(image_id)
        validation_result = regions.validation_result
        self.image_region_summaries[image_id] = self._image_region_summary_from_rows(regions.rows, validation_result)
        self._reload_preview_counts()
        return validation_result

    def _apply_preview_summary_totals(self, summaries):
        self.count_rectangle = sum(summary.get("rectangle", 0) for summary in summaries.values())
        self.count_polygon = sum(summary.get("polygon", 0) for summary in summaries.values())
        self.count_circle = sum(summary.get("circle", 0) for summary in summaries.values())
        self.count_point = sum(summary.get("point", 0) for summary in summaries.values())
        self.count_linestring = sum(summary.get("linestring", 0) for summary in summaries.values())
        self.count_multipoint = sum(summary.get("multipoint", 0) for summary in summaries.values())
        self.count_multilinestring = sum(summary.get("multilinestring", 0) for summary in summaries.values())
        self.count_multipolygon = sum(summary.get("multipolygon", 0) for summary in summaries.values())
        count_error = sum(1 for summary in summaries.values() if summary.get("error_image", False))
        count_warning = sum(1 for summary in summaries.values() if summary.get("warning_image", False))
        count_valid = sum(
            1
            for summary in summaries.values()
            if not summary.get("error_image", False) and not summary.get("warning_image", False)
        )
        self.database_statistics_popup.set_counts(
            image=len(summaries),
            rectangle=self.count_rectangle,
            polygon=self.count_polygon,
            circle=self.count_circle,
            point=self.count_point,
            linestring=self.count_linestring,
            multipoint=self.count_multipoint,
            multilinestring=self.count_multilinestring,
            multipolygon=self.count_multipolygon,
            valid=count_valid,
            warning=count_warning,
            error=count_error,
        )

    # ----------------------------------------------------------
    # SHOW GUI
    # self.show()

    # Thread handler
    @Slot(bool)
    def thread_output_exif(self, success):
        if not success:
            logger.error("Writing metadata failed.")
        self.stop_waiting()
        self.db.unlock()

    @Slot(bool)
    def thread_output(self, success: bool):

        if success:
            self.clean_all_views_and_tables(db_save=True)
            self.loader_all()
            logger.info("Imported %s images.", self.len_image_list, extra={"finished": True, "open": True})
        else:
            logger.error("Image import failed.")

        self.stop_waiting()
        self.db.unlock()

    @Slot(tuple)
    def thread_output_db_error(self, error):
        exec_type, value, error_traceback = error
        logger.error("Database operation failed: %s", value)
        logger.error(error_traceback)
        self.stop_waiting("Operation failed")
        self.db.unlock()

    @Slot(object)
    def thread_output_image_loader(self, image):
        # Swapping the image unchecks the AI button several times (no image, reset controls).
        # With AI on, keep the model across the whole switch and encode the new image afterwards.
        keep_ai_active = self._ai_active_or_requested() or self._ai_resume_after_image_load
        self._ai_resume_after_image_load = False
        self._ai_keep_model_on_image_change = keep_ai_active
        try:
            self.view_digizizer.set_visual_rotation(
                self._preview_visual_rotation(self.image_loading_image_id_db),
                emit_signal=False,
            )
            self.digitizer_scene.change_image(image)
            self.view_digizizer.apply_smooth_pixmap_to_scene()
            self.view_digizizer.set_exif_rotation_available(
                self._preview_exif_orientation_present(self.image_loading_image_id_db)
            )
            self.view_digizizer.reset_overlay_position()
            self.view_digizizer.reset_ai_controls()
        finally:
            self._ai_keep_model_on_image_change = False
        self.set_image_meta_and_display_meta()
        self.model.set_missing_image(self.image_loading_image_id_db, False)
        self.model.set_active_image(self.image_loading_image_id_db)
        self.stop_waiting()
        self.image_loading = False
        self._prepare_ai_for_current_image(activate=keep_ai_active)
        self._sync_undo_redo_actions()

    @Slot(tuple)
    def thread_output_image_open_error(self, error):
        exec_type, value, error_traceback = error
        logger.error("Image loading failed: %s", value)
        logger.error(error_traceback)
        if self.image_loading_image_id_db and not Path(self.image_loading_name).exists():
            self.model.set_missing_image(self.image_loading_image_id_db, True)
        self.stop_waiting("Image loading failed")
        self.image_loading = False
        self._ai_keep_model_on_image_change = False
        if self._ai_resume_after_image_load:
            # The next image could not be shown, so AI stays off: release the kept model.
            self._ai_resume_after_image_load = False
            self._release_ai_segmenter()
        self._sync_undo_redo_actions()

    @Slot(object)
    def thread_output_image_import(self, result: ImageImportResult):
        self.len_image_list = result.imported
        if result.duplicates:
            logger.warning("%s images ignored, for example because they were already imported.", result.duplicates)
        if result.skipped_unreadable:
            logger.warning(
                "%s files skipped because they are not supported or readable images.", result.skipped_unreadable
            )

        if result.imported > 0:
            self.clean_all_views_and_tables(db_save=True)
            self.loader_all()
            logger.info("Imported %s images.", result.imported, extra={"finished": True, "open": True})
        else:
            logger.info("No new images to import.", extra={"finished": True, "open": True})

        self.db.unlock()
        self.stop_waiting()

    @Slot(object)
    def thread_output_csv_import(self, result: CsvImportResult):
        if result.missing_images:
            logger.warning("%s CSV images skipped because the files are missing.", result.missing_images)
        if result.skipped_unreadable_images:
            logger.warning("%s CSV images skipped because they are not readable.", result.skipped_unreadable_images)
        if result.skipped_rows:
            logger.warning("%s CSV rows skipped because they are malformed.", result.skipped_rows)
        if result.duplicate_objects:
            logger.info("%s CSV objects ignored because the geometry already exists.", result.duplicate_objects)

        if result.imported_images or result.added_objects:
            self.clean_all_views_and_tables(db_save=True)
            self.loader_all()
            logger.info(
                "CSV import finished: %s images imported, %s objects added.",
                result.imported_images,
                result.added_objects,
                extra={"finished": True, "open": True},
            )
        else:
            logger.info("CSV import finished. No new objects added.", extra={"finished": True, "open": True})

        self.db.unlock()
        self.stop_waiting()

    def set_image_meta_and_display_meta(self):
        self.view_digizizer.fitInView(self.digitizer_scene.image_item, Qt.KeepAspectRatio)
        self.digitizer_scene.image_id_db = self.image_loading_image_id_db
        self.lbl_image_name.setText(self.image_loading_name_path)

        string_wrap = self.image_loading_name
        if len(string_wrap) > 110:
            string_wrap = string_wrap[:110] + "\n" + string_wrap[110:]

        self.lbl_image_path.setText(string_wrap)
        self.current_image = {"id": self.image_loading_image_id_db, "name": self.image_loading_name_path}
        # Each opened image is parsed and validated once; the result is kept while it stays open.
        self.image_regions = OpenImageRegions(self.db, self.image_loading_image_id_db)
        self._load_scene_objects(self.image_loading_image_id_db)
        self._apply_scene_visibility()
        self.image_region_view_load_all_image()

    def _load_scene_objects(self, image_id):
        for element, data, shape, coordinates in self._regions_of(image_id).drawable_regions():
            display_type = base_object_type(element["object_type"])
            if display_type == "rectangle":
                color = self.color_rectangle
            elif display_type == "circle":
                color = self.color_circle
            elif display_type == "point":
                color = self.color_point
            elif display_type == "linestring":
                color = self.color_linestring
            else:
                color = self.color_polygon
            self.digitizer_scene.add_object(
                element["object_type"], data, element["id"], color, geometry=(shape, coordinates)
            )

    # ----------------------------------------------------------
    # Functions

    def eventFilter(self, obj, event):
        if (
            getattr(self, "_parent_assignment", None) is not None
            or getattr(self, "_merge_target_selection", None) is not None
        ):
            if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
                self._cancel_parent_assignment()
                return True
            if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
                views = (self.region_editor.ui.graphicsView, self.view_digizizer)
                for view in views:
                    if obj is view.viewport() and event.button() == Qt.MouseButton.LeftButton:
                        if event.type() == QEvent.Type.MouseButtonRelease:
                            for item in view.items(event.position().toPoint()):
                                part_index, ring_index = None, 0
                                if view is views[0]:
                                    node_item = self.region_editor.graph_scene._node_item_parent(item)
                                    parent_id = (
                                        node_item.node.geometry_owner_id or node_item.node.object_id
                                        if node_item is not None
                                        else None
                                    )
                                    if node_item is not None:
                                        part_index = node_item.node.geometry_part_index
                                        ring_index = node_item.node.geometry_ring_index or 0
                                else:
                                    parent_id = getattr(item, "obj_id", None)
                                    part_index = getattr(item, "geometry_part_index", None)
                                    ring_index = getattr(item, "geometry_ring_index", 0)
                                if parent_id is not None:
                                    if getattr(self, "_merge_target_selection", None) is not None:
                                        self._pick_merge_target(parent_id, part_index, ring_index)
                                    else:
                                        self._pick_region_parent(parent_id)
                                    break
                        return True
        if self._geometry_operation_in_progress():
            if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
                if self.digitizer_scene.cancel_active_operation():
                    self._sync_geometry_action_availability()
                    event.accept()
                    return True

            blocked_event_types = (
                QEvent.Type.MouseButtonPress,
                QEvent.Type.MouseButtonDblClick,
                QEvent.Type.MouseButtonRelease,
                QEvent.Type.ContextMenu,
            )
            if event.type() in blocked_event_types and not self._event_target_in_digitizer_view(obj, event):
                self._warn_geometry_operation_blocked()
                event.accept()
                return True

        return super().eventFilter(obj, event)

    def _geometry_operation_in_progress(self):
        return hasattr(self, "digitizer_scene") and self.digitizer_scene.instruction_active

    def _event_target_in_digitizer_view(self, obj, event=None):
        if hasattr(self, "digitizer_scene") and obj is self.digitizer_scene:
            return True

        view = getattr(self, "view_digizizer", None)
        if view is None:
            return False
        if event is not None:
            global_pos = self._event_global_pos(event)
            if global_pos is not None and view.viewport().rect().contains(view.viewport().mapFromGlobal(global_pos)):
                return True
        if obj is view or obj is view.viewport():
            return True
        if isinstance(obj, QWidget) and view.isAncestorOf(obj):
            return True

        parent = obj.parent() if hasattr(obj, "parent") else None
        while parent is not None:
            if parent is view:
                return True
            parent = parent.parent() if hasattr(parent, "parent") else None
        return False

    @staticmethod
    def _event_global_pos(event):
        if hasattr(event, "globalPosition"):
            return event.globalPosition().toPoint()
        if hasattr(event, "globalPos"):
            return event.globalPos()
        return None

    def _warn_geometry_operation_blocked(self):
        message = "Finish the geometry operation or press Esc to cancel."
        now = QtCore.QDateTime.currentMSecsSinceEpoch()
        if now - getattr(self, "_last_operation_block_warning_ms", 0) < 1500:
            return
        self._last_operation_block_warning_ms = now
        logger.warning(message)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and self.digitizer_scene.cancel_active_operation():
            self._sync_geometry_action_availability()
            event.accept()
            return

        if self.digitizer_scene.width() != 0.0:
            # Navigate to next or previous image
            if event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
                next_index = self.model.get_relative_index(self.image_loading_image_id_db, 1)
                if next_index is not None:
                    self.scene_load_image(next_index)

            if event.key() == Qt.Key.Key_Backspace:
                next_index = self.model.get_relative_index(self.image_loading_image_id_db, -1)
                if next_index is not None:
                    self.scene_load_image(next_index)

        if event.key() == Qt.Key.Key_S and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.save_data()

    def mousePressEvent(self, event):

        focused_widget = self.focusWidget()
        if isinstance(focused_widget, QPlainTextEdit):
            focused_widget.clearFocus()
        super().mousePressEvent(event)

    @Slot(str, str)
    def user_save(self, user, user_uri):
        self.user = user
        self.user_uri = user_uri
        self.user_information_popup.txt_user_name.setPlainText(user)
        self.user_information_popup.txt_user_indent.setPlainText(user_uri)
        print("Welcome " + self.user.upper() + ".\nEnjoy working with GRAPHIS")
        self.show()
        QtCore.QTimer.singleShot(0, self._warn_auto_scale_if_active)

    def _warn_auto_scale_if_active(self):
        if self._auto_scale_warning_shown or self.auto_scale_factor is None:
            return
        self._auto_scale_warning_shown = True
        logger.warning(
            "Automatic small-screen scaling is active at %.2f. This is experimental and could cause visual glitches.",
            self.auto_scale_factor,
            extra={"finished": True, "open": True},
        )

    def handle_output(self, text, stdout):
        level = logging.INFO if stdout else logging.ERROR
        log_style = LOGGING_STYLE[level]
        self._set_log_indicator(level, log_style)
        self.popup_info.append_text(text, log_style["txt"])

        if not stdout:
            self.popup_info.show_popup()

    @Slot(str, logging.LogRecord)
    def handle_output_logging(self, status, record):
        indicator_level = record.levelno
        log_style = LOGGING_STYLE.get(record.levelno, LOGGING_STYLE[logging.INFO])
        if getattr(record, "finished", False) and record.levelno < logging.WARNING:
            indicator_level = logging.INFO
            log_style = LOGGING_STYLE["finished"]
        self._set_log_indicator(indicator_level, log_style)
        self.popup_info.append_text(status + "\n", log_style["txt"])
        if record.levelno >= logging.WARNING or (getattr(record, "finished", False) and getattr(record, "open", False)):
            self.popup_info.show_popup()

    def _set_log_indicator(self, level, log_style, force=False):
        if force or level >= self.logging_current_level:
            self.graphis_status.set_info_popup_icon(icon_path_str(log_style["icon"]))
            self.popup_info.set_level_style(log_style["frame"])
        self.logging_current_level = max(self.logging_current_level, level)

    def show_info_popup(self):
        if self.popup_info.isVisible():
            self.popup_info.hide_popup()
            self.logging_current_level = logging.INFO
            log_style = LOGGING_STYLE[logging.INFO]
            self._set_log_indicator(logging.INFO, log_style, force=True)
        else:
            self.popup_info.show_popup()

    def image_region_view_load_all_image(self):
        if (
            getattr(self, "_parent_assignment", None) is not None
            or getattr(self, "_merge_target_selection", None) is not None
        ):
            self._cancel_parent_assignment()
        if self.current_image is None:
            self.model_image_region_all.clear()
            self.region_editor.clear_graph()
            return

        regions = self._regions_of(self.current_image["id"])
        data = regions.rows
        json_image_all_region = [json.loads(obj["data"]) for obj in data]
        image = regions.image
        validation_result = regions.validation_result
        issues_by_object = regions.issues_by_object()

        self.image_region_summaries[self.current_image["id"]] = self._image_region_summary_from_rows(
            data,
            validation_result,
        )
        self._reload_preview_counts()

        self.region_editor.load_graphis_objects(
            data,
            validation_issues=issues_by_object,
            image_width=image["width"] if image else None,
            image_height=image["height"] if image else None,
        )
        self.model_image_region_all.load(json_image_all_region)
        self.region_editor.set_all_region_model(self.model_image_region_all)

    def scene_load_image(self, index):

        if not index.isValid():
            return

        image_path = index.data(Qt.ItemDataRole.UserRole)
        image_id = index.data(Qt.ItemDataRole.UserRole + 1)
        if image_path is None or image_id is None:
            return

        image_path = Path(image_path)
        if not image_path.exists():
            self.model.set_missing_image(image_id, True)
            logger.warning("Image does not exist: %s", image_path)
            return
        self.model.set_missing_image(image_id, False)

        if not self.image_loading:
            if not self._guard_unsaved_region_metadata_changes("open another image"):
                return
            self.image_loading = True
            # Clearing the scene unchecks the AI button; with AI on, keep the model for the next image.
            self._ai_resume_after_image_load = self._ai_active_or_requested()
            self._ai_keep_model_on_image_change = self._ai_resume_after_image_load
            try:
                self.view_digizizer.hide_metadata_popup()
                self._sync_undo_redo_actions()
                self.clear_entries()
                self.digitizer_scene.clear_current_operation()
                self.digitizer_scene.clear_active_object()
                self.digitizer_scene.clear()

                self.model_image_region.clear()
                self.model_image_region_all.clear()
                self.region_editor.clear_graph()
                self.current_item = None
                self._current_item_form_baseline = None

                self.digitizer_scene.clear_image()
            except BaseException:
                self._ai_keep_model_on_image_change = False
                raise

            worker = Worker(image_loader, os.fspath(image_path))
            worker.signals.result.connect(self.thread_output_image_loader)
            worker.signals.error.connect(self.thread_output_image_open_error)
            self.image_loading_image_id_db = image_id
            self.image_loading_name_path = image_path.name
            self.image_loading_name = os.fspath(image_path)
            self.thread_pool.start(worker)
            self.start_waiting("Loading image...")

    @Slot(str, object)
    def _thumbnail_context_action(self, action, index):
        if not index.isValid():
            return

        if action == "open_image":
            self.scene_load_image(index)
        elif action == "copy_image_path":
            self._copy_thumbnail_image_path(index)
        elif action == "open_image_location":
            self._open_thumbnail_image_location(index)
        elif action == "restore_original_image_region":
            self._restore_thumbnail_original_image_region(index)
        elif action == "convert_coordinates_relative":
            self._convert_thumbnail_image_region_coordinates(index, "relative")
        elif action == "convert_coordinates_pixel":
            self._convert_thumbnail_image_region_coordinates(index, "pixel")
        elif action == "delete_image":
            self._delete_thumbnail_image_from_database(index)

    def _thumbnail_image_data(self, index):
        image_path = index.data(Qt.ItemDataRole.UserRole)
        image_id = index.data(Qt.ItemDataRole.UserRole + 1)
        if image_path is None or image_id is None:
            return None, None, ""
        image_path = Path(image_path)
        return image_path, int(image_id), image_path.name

    def _convert_thumbnail_image_region_coordinates(self, index, unit):
        _image_path, image_id, image_title = self._thumbnail_image_data(index)
        if image_id is None:
            return
        self.convert_image_region_coordinates(unit, image_id=image_id, image_title=image_title)

    def _confirm_convert_image_region_coordinates(self, unit):
        unit_name = "relative" if unit == "relative" else "pixel"
        answer = message_box.question(
            self,
            "Convert Image Region coordinates?",
            (
                f"Convert Image Region coordinates for all images to {unit_name} units?\n\n"
                "This updates stored database regions. Use Undo on an image to revert converted regions."
            ),
            message_box.StandardButton.Yes | message_box.StandardButton.Cancel,
            message_box.StandardButton.Cancel,
        )
        return answer == message_box.StandardButton.Yes

    def convert_image_region_coordinates(self, unit, image_id=None, image_title=None):
        if unit not in {"relative", "pixel"}:
            logger.error("Unsupported Image Region coordinate unit: %s", unit)
            return
        if not self._db_ready_for("convert image-region coordinates"):
            return
        if image_id is None and not self._confirm_convert_image_region_coordinates(unit):
            return

        updates, skipped = self._collect_image_region_coordinate_updates(unit, image_id=image_id)
        scope = image_title or "database"
        if not updates:
            if skipped:
                logger.warning(
                    "No Image Region coordinates were converted for %s. %s regions could not be converted.",
                    scope,
                    skipped,
                )
            else:
                logger.info("Image Region coordinates are already stored as %s units for %s.", unit, scope)
            return

        label = f"Convert Image Region coordinates to {unit}"
        self.db.begin_undo_group(label)
        try:
            for object_id, converted_region, _update_image_id in updates:
                self.db.update_object(obj_id=object_id, data=converted_region, log_validation=False)
        finally:
            self.db.end_undo_group()

        affected_image_ids = {update_image_id for _object_id, _region, update_image_id in updates}
        current_image_affected = self.current_image is not None and self.current_image["id"] in affected_image_ids
        if image_id is None:
            self.image_region_summaries = self._image_region_summaries()
            if current_image_affected:
                self._refresh_after_history_replay(self._selected_object_id())
            else:
                self._reload_preview_counts()
        elif current_image_affected:
            self._refresh_after_history_replay(self._selected_object_id())
        else:
            self._refresh_image_region_summary(image_id)
            self._sync_undo_redo_actions()

        if skipped:
            logger.warning(
                "Converted %s Image Region coordinates to %s units. %s regions could not be converted.",
                len(updates),
                unit,
                skipped,
            )
        else:
            logger.info(
                "Converted %s Image Region coordinates to %s units.",
                len(updates),
                unit,
                extra={"finished": True, "open": True},
            )

    def _collect_image_region_coordinate_updates(self, unit, image_id=None):
        if image_id is None:
            rows = self.db.db_load_objects_all()
        else:
            image = self.db.db_load_image_record(image_id)
            if not image:
                return [], 0
            rows = [
                {
                    **dict(obj),
                    "img_width": image["width"],
                    "img_height": image["height"],
                }
                for obj in self.db.db_load_objects_image(image_id)
            ]

        updates = []
        skipped = 0
        for obj in rows:
            try:
                region = json.loads(obj["data"])
                converted_region = change_region_unit(region, unit, obj["img_width"], obj["img_height"])
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as err:
                skipped += 1
                logger.warning("Could not convert Image Region object %s to %s units: %s", obj.get("id"), unit, err)
                continue
            if converted_region == region:
                continue
            updates.append((obj["id"], converted_region, obj["image"]))
        return updates, skipped

    def _copy_thumbnail_image_path(self, index):
        image_path, _image_id, _image_title = self._thumbnail_image_data(index)
        if image_path is None:
            return
        QApplication.clipboard().setText(os.fspath(image_path))
        logger.info("Copied image path: %s", image_path, extra={"finished": True})

    def _open_thumbnail_image_location(self, index):
        image_path, _image_id, _image_title = self._thumbnail_image_data(index)
        if image_path is None:
            return

        if not image_path.exists() and _image_id is not None:
            self.model.set_missing_image(_image_id, True)

        location = image_path.parent if image_path.parent.exists() else image_path
        if location.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(os.fspath(location)))
            return

        logger.warning("Cannot open image location because the path does not exist: %s", image_path)

    def _restore_thumbnail_original_image_region(self, index):
        if not self._db_ready_for("restore orig. image region"):
            return

        image_path, image_id, image_title = self._thumbnail_image_data(index)
        if image_id is None:
            return

        self._restore_original_image_regions(image_id, image_title)

    @Slot(int)
    def restore_original_image_regions_for_object(self, object_id):
        if not self._db_ready_for("restore orig. image region"):
            return

        data_row = self.db.db_load_object(object_id)
        if data_row is None:
            logger.warning("Selected image region no longer exists.")
            return
        if not data_row["orig_img_region"]:
            logger.warning("No original image-region snapshot is available for the selected region.")
            return

        image = self.db.db_load_image_record(data_row["image"])
        image_title = self._image_record_title(image, data_row["image"])
        if not image or image["width"] is None or image["height"] is None:
            logger.warning("Cannot restore original image region because image size is missing: %s", image_title)
            return

        original_region = json.loads(data_row["orig_img_region"])
        region_for_app = copy.deepcopy(original_region)
        try:
            if region_for_app.get("Contributor", ""):
                region_for_app[self.config_default["CONTRIBUTOR_TAG"]] = region_for_app.pop("Contributor")
            object_type, data, _user = parse_img_region(
                region_for_app,
                image["width"],
                image["height"],
                self.config_default,
            )
        except Exception:
            logger.exception("Could not parse original image region for: %s", image_title)
            return

        current_data = json.loads(data_row["data"])
        if data_row["object_type"] == object_type and current_data == data:
            logger.info("Selected image region already matches the original.")
            return

        if not self._confirm_restore_original_object_region(image_title):
            return

        self.db.update_object(
            obj_id=object_id,
            data=data,
            object_type=object_type,
            log_validation=False,
            action_label="Restore original image region",
        )
        if self.image_loading_image_id_db == data_row["image"] and self.current_image is not None:
            self._reset_geometry_visibility()
            self._refresh_after_history_replay(object_id)
        else:
            self._refresh_image_region_summary(data_row["image"])
            self._sync_undo_redo_actions()
        logger.info("Restored original image region for: %s", image_title, extra={"finished": True, "open": True})

    def _restore_original_image_regions(self, image_id, image_title):
        original_regions = self.db.db_load_original_image_region(image_id)
        if original_regions is None:
            logger.warning("No original image-region snapshot is available for: %s", image_title)
            return

        if not self._confirm_restore_original_image_region(image_title, len(original_regions)):
            return

        image = self.db.db_load_image_record(image_id)
        if not image or image["width"] is None or image["height"] is None:
            logger.warning("Cannot restore original image regions because image size is missing: %s", image_title)
            return

        parsed_objects = []
        for original_region in original_regions:
            region_for_app = copy.deepcopy(original_region)
            try:
                if region_for_app.get("Contributor", ""):
                    region_for_app[self.config_default["CONTRIBUTOR_TAG"]] = region_for_app.pop("Contributor")
                object_type, data, user = parse_img_region(
                    region_for_app,
                    image["width"],
                    image["height"],
                    self.config_default,
                )
                parsed_objects.append(
                    {
                        "object_type": object_type,
                        "data": data,
                        "user": user or self.user,
                        "orig_img_region": copy.deepcopy(original_region),
                    }
                )
            except Exception:
                logger.exception("Could not parse original image region for: %s", image_title)

        self.db.db_replace_image_objects(image_id, parsed_objects)
        if self.image_loading_image_id_db == image_id and self.current_image is not None:
            self._reset_geometry_visibility()
        self._refresh_after_image_object_replacement(image_id)
        logger.info("Restored original image regions for: %s", image_title, extra={"finished": True, "open": True})

    def _image_record_title(self, image, fallback_image_id):
        if not image:
            return f"Image {fallback_image_id}"
        if image["name"]:
            return image["name"]
        if image["path"]:
            return Path(image["path"]).name
        return f"Image {fallback_image_id}"

    def _confirm_restore_original_image_region(self, image_title, region_count):
        answer = message_box.warning(
            self,
            "Restore original image region?",
            (
                f"Restore the originally imported image regions for:\n{image_title}\n\n"
                f"Original region count: {region_count}\n"
                "All current regions for this image will be replaced.\n\n"
                "This cannot be undone."
            ),
            message_box.StandardButton.Yes | message_box.StandardButton.Cancel,
            message_box.StandardButton.Cancel,
        )
        return answer == message_box.StandardButton.Yes

    def _confirm_restore_original_object_region(self, image_title):
        answer = message_box.warning(
            self,
            "Restore original image region?",
            (
                f"Restore the originally imported selected image region for:\n{image_title}\n\n"
                "This updates only this image region. Use Undo to restore the current version."
            ),
            message_box.StandardButton.Yes | message_box.StandardButton.Cancel,
            message_box.StandardButton.Cancel,
        )
        return answer == message_box.StandardButton.Yes

    def _delete_thumbnail_image_from_database(self, index):
        if not self._db_ready_for("delete image from database"):
            return

        image_path, image_id, image_title = self._thumbnail_image_data(index)
        if image_id is None:
            return

        if not self._confirm_delete_image_from_database(image_title):
            return

        self.db.db_delete_image(image_id)
        self._reload_database_preview()
        logger.info(
            "Deleted image from database: %s",
            image_path or image_title,
            extra={"finished": True, "open": True},
        )

    def _confirm_delete_image_from_database(self, image_title):
        answer = message_box.warning(
            self,
            "Delete image from database?",
            (
                f"<b>Delete this image from the database?</b><br>{image_title}<br><br>"
                "All regions/objects for this image will also be deleted.<br>"
                "The image file on disk will not be deleted.<br><br>"
                "<b>This cannot be undone.</b>"
            ),
            message_box.StandardButton.Yes | message_box.StandardButton.Cancel,
            message_box.StandardButton.Cancel,
        )
        return answer == message_box.StandardButton.Yes

    def _refresh_after_image_object_replacement(self, image_id):
        if self.image_loading_image_id_db == image_id and self.current_image is not None:
            self._refresh_after_history_replay()
        else:
            self._refresh_image_region_summary(image_id)
            self._sync_undo_redo_actions()

    def _reload_database_preview(self):
        self.clean_all_views_and_tables(db_save=True)
        self.loader_all()
        self._sync_database_status_name()

    def _sync_database_status_name(self):
        if self.db.db_is_set and self.db.db_path is not None:
            self.graphis_status.set_sqlite_name(self.db.db_path.name)
        else:
            self.graphis_status.clear_sqlite_name()

    def change_visibility(self, objects_type):
        if self._object_type_visible(objects_type) and self._selected_geometry_type() == objects_type:
            logger.warning(
                "Cannot hide %s geometries while a %s geometry is selected. Save or clear the selection first.",
                objects_type,
                objects_type,
            )
            self._sync_region_operations_toolbar()
            return

        if objects_type == "point":
            self.point_visible = not self.point_visible
        if objects_type == "circle":
            self.circle_visible = not self.circle_visible
        if objects_type == "linestring":
            self.linestring_visible = not self.linestring_visible
        elif objects_type == "rectangle":
            self.rectangle_visible = not self.rectangle_visible
        elif objects_type == "polygon":
            self.polygon_visible = not self.polygon_visible
        self._apply_scene_visibility()
        self._sync_region_operations_toolbar()

    def _selected_geometry_type(self):
        selected_item = self.digitizer_scene.active_geometry_item()
        selected_object_type = getattr(selected_item, "object_type", None) if selected_item is not None else None
        if selected_object_type is not None:
            return selected_object_type
        if self.current_item is not None:
            return self.current_item.get("object_type")
        return None

    @Slot(object)
    def change_color(self, color, object_type):
        self.region_editor.set_geometry_color(object_type, color)

        if object_type == "point":
            self.color_point = color
            self.digitizer_scene.color_point = color
            self.delegate.point_color = color
            self.database_statistics_popup.set_color("point", self.color_point)

        if object_type == "circle":
            self.color_circle = color
            self.digitizer_scene.color_circle = color
            self.delegate.circle_color = color
            self.database_statistics_popup.set_color("circle", self.color_circle)

        if object_type == "linestring":
            self.color_linestring = color
            self.digitizer_scene.color_linestring = color
            self.delegate.linestring_color = color
            self.database_statistics_popup.set_color("linestring", self.color_linestring)
            self.digitizer_scene.change_color("linestring", color)
            if hasattr(self, "geom_operations"):
                self.geom_operations.set_color("linestring", color)
            return

        elif object_type == "rectangle":
            self.color_rectangle = color
            self.digitizer_scene.color_rectangle = color
            self.delegate.rectangle_color = color
            self.database_statistics_popup.set_color("rectangle", self.color_rectangle)

        elif object_type == "polygon":
            self.color_polygon = color
            self.digitizer_scene.color_polygon = color
            self.delegate.polygon_color = color
            self.database_statistics_popup.set_color("polygon", self.color_polygon)

        self.digitizer_scene.change_color(object_type, color)
        if hasattr(self, "geom_operations"):
            self.geom_operations.set_color(object_type, color)

    @Slot()
    def save_data(self):

        if self.current_item is None:
            self.clear_entries(reset_visibility=False)
            return True

        if self.digitizer_scene.image_item is not None:
            if self.current_item is not None:
                data = self._metadata_from_region_form(show_errors=True)
                if data is None:
                    return False

                self.digitizer_scene.set_tooltip(self.current_item["id"], text_value(data.get("rId", "")))
                object_id = self.current_item["id"]
                try:
                    self.db.update_object(obj_id=object_id, data=data)
                except ValueError as err:
                    logger.warning("Cannot save image region: %s", err)
                    return False
                self.current_item["data"] = data
                self.parse_show_data(self.current_item["object_type"], data)
                self._current_item_form_baseline = self._metadata_from_region_form(show_errors=False)
                self.model_image_region.load(data)
                self.region_editor.resize_current_region_headers()

                self.change_color(self.color_rectangle, "rectangle")
                self.change_color(self.color_polygon, "polygon")
                self.change_color(self.color_circle, "circle")
                self.change_color(self.color_linestring, "linestring")
                self.change_color(self.color_point, "point")
                self.image_region_view_load_all_image()
                self.digitizer_scene.activate_object(object_id)
                self._graph_selection_active = True
                try:
                    self.region_editor.select_object(object_id)
                finally:
                    self._graph_selection_active = False
                self._apply_scene_visibility()
                self._sync_undo_redo_actions()
                return True
        return False

    def _metadata_from_region_form(self, show_errors=False):
        if self.current_item is None:
            return None

        object_type = self.current_item["object_type"]
        original_data = self.current_item["data"]
        data = copy.deepcopy(self.current_item["data"])
        form_values = self.region_editor.region_form_values()

        data = put_text_to_dict_or_remove(data, "rId", form_values["region_id"])
        validation_error = (
            self.region_editor.region_name_language_error()
            or self.region_editor.description_language_error()
            or self.region_editor.transcription_language_error()
            or self.region_editor.contributor_error()
        )
        if validation_error:
            if show_errors:
                logger.error("Cannot save region metadata: %s", validation_error)
                message_box.warning(self, "Cannot save region metadata", validation_error)
            return None

        data = put_lang_alt_to_dict_or_remove(
            data,
            "name",
            form_values["region_name"],
            form_values["region_name_alternatives"],
        )

        data = put_struct_to_dict_or_remove(
            data, "rCtype", form_values["region_type_identifier"], form_values["region_type_name"]
        )

        data = put_struct_to_dict_or_remove(
            data, "rRole", form_values["region_role_identifier"], form_values["region_role_name"]
        )

        contributor_tag = self.config_default["CONTRIBUTOR_TAG"]
        contributors = _contributor_entities_from_rows(form_values["contributors"])
        if contributors:
            data[contributor_tag] = contributors
        else:
            data.pop(contributor_tag, None)

        description_tag = self.config_default["TAG_DESCRIBER"]
        transcription_tag = self.config_default["TAG_TRANSCRIBER"]
        description_value = _language_value_from_rows(form_values["description_languages"])
        transcription_value = _language_value_from_rows(form_values["transcription_languages"])

        if description_value != metadata_lang_alt_value(original_data, description_tag):
            self._append_current_user_contributor_if_role_missing(
                data,
                self.get_config_role(object_type, "describer_role"),
            )

        if transcription_value != metadata_lang_alt_value(original_data, transcription_tag):
            self._append_current_user_contributor_if_role_missing(
                data,
                self.get_config_role(object_type, "transcriber_role"),
            )

        data = put_lang_alt_value_to_dict_or_remove(
            data,
            description_tag,
            description_value,
        )
        data = put_lang_alt_value_to_dict_or_remove(
            data,
            transcription_tag,
            transcription_value,
        )

        return normalize_lang_alt_text_fields(data)

    def _populate_digitizer_context_menu(self, menu, item):
        object_id = item.obj_id
        graph = self.region_editor.graph_scene
        group_ids = set(graph.selected_object_ids)
        if group_ids:
            group_ids.add(str(object_id))
        part_index = getattr(item, "geometry_part_index", None)
        ring_index = getattr(item, "geometry_ring_index", 0)
        if not self._request_object_selection(object_id):
            return
        if part_index is not None and len(group_ids) <= 1:
            self.digitizer_scene.activate_geometry_part(object_id, part_index, ring_index)
            self.region_editor.select_geometry_part(object_id, part_index, ring_index)
            owner = self.region_editor.graph_scene.node_items.get(str(object_id))
            select_owner = menu.addAction("Select whole image region")
            select_owner.triggered.connect(lambda: self._request_object_selection(object_id))
            if owner is not None and owner.node.region.get("regionBoundary", {}).get("rbShape") in {
                "multipoint", "multilinestring", "multipolygon"
            } and ring_index == 0:
                detach = menu.addAction("Detach as new image region")
                detach.triggered.connect(lambda: self.detach_geometry_part(object_id, part_index))
            menu.addSeparator()
        graph.set_group_selection(group_ids)
        owner = graph.node_items.get(str(object_id))
        if owner is not None:
            dispatch = graph.populate_region_context_menu(
                menu, owner, include_geometry_assignment=False
            )
            menu.triggered.connect(dispatch)

    def _smooth_selected_geometry(self):
        self._modify_selected_vertices("smooth geometry")

    def _reduce_selected_vertices(self):
        self._modify_selected_vertices("reduce vertices")

    def _modify_selected_vertices(self, operation):
        scene = self.digitizer_scene
        item = scene.smooth_geometry_target()
        if item is None or not self._db_ready_for(operation):
            return
        object_id = item.obj_id
        part_index = getattr(item, "geometry_part_index", None)
        ring_index = getattr(item, "geometry_ring_index", 0)
        if not self._guard_unsaved_region_metadata_changes(operation):
            return
        self._clear_geometry_operation()
        if part_index is None:
            scene.activate_object(object_id)
        else:
            scene.activate_geometry_part(object_id, part_index, ring_index)
        if operation == "smooth geometry":
            scene.smooth_selected_geometry()
        else:
            scene.reduce_selected_vertices()

    def _set_polygon_brush_enabled(self, enabled):
        scene = self.digitizer_scene
        if enabled:
            item = scene.polygon_brush_target()
            if item is None or not self._db_ready_for("edit polygon border"):
                self.view_digizizer.set_polygon_brush_checked(False)
                return
            object_id = item.obj_id
            part_index = getattr(item, "geometry_part_index", None)
            if not self._guard_unsaved_region_metadata_changes("edit polygon border"):
                self.view_digizizer.set_polygon_brush_checked(False)
                return
            self.view_digizizer.set_ai_mode_checked(False)
            self._clear_geometry_operation()
            if part_index is None:
                scene.activate_object(object_id)
            else:
                scene.activate_geometry_part(object_id, part_index)
                self.region_editor.select_geometry_part(object_id, part_index)
        scene.set_polygon_brush_enabled(enabled)
        self.view_digizizer.set_polygon_brush_checked(scene.polygon_brush_enabled)

    def _clear_geometry_operation(self):
        self.digitizer_scene.clear_current_operation()
        if hasattr(self, "geom_operations"):
            self.geom_operations.clear_active_tool()
        self._sync_geometry_action_availability()

    def _set_ai_segmentation_mode(self, enabled):
        if self._ai_initialization_worker is not None:
            # The model prepares in the background; remember whether to switch AI on when it is ready.
            if enabled and not self._ai_initialization_activate:
                self.start_waiting(f"Preparing {self.ki_backend_id} on {self.ki_device}...")
            elif not enabled and self._ai_initialization_activate:
                self.stop_waiting()
            self._ai_initialization_activate = bool(enabled)
            return
        if self.digitizer_scene.ai_background_busy:
            return
        if enabled:
            self._scan_ai_devices()
            self._ensure_ai_segmenter(activate=True)
            return
        if self._ai_keep_model_on_image_change:
            # A new image is shown while AI stays on: keep the model, only the image is encoded again.
            self.digitizer_scene.set_ai_mode_enabled(False)
        else:
            self._release_ai_segmenter()
        self._sync_geometry_action_availability()

    def _scan_ai_devices(self):
        """Detect GPUs once, on the GUI thread.

        PyTorch must be imported on the main thread: importing it first in a worker thread
        crashes later model construction on Windows.
        """
        if self._ai_devices_scanned:
            return
        self._ai_devices_scanned = True
        from graphis.app.ki.devices import torch_device_options

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._ai_device_options = torch_device_options()
        except Exception as err:
            logger.warning("AI device detection failed: %s", err)
        finally:
            QApplication.restoreOverrideCursor()
        self._sync_ai_device_combo()

    def _ai_device_options_for(self, backend_id):
        return [(key, label) for key, label in self._ai_device_options
                if not (key == "dml" and backend_id == "ultralytics_sam3")]

    def _sync_ai_device_combo(self):
        options = self._ai_device_options_for(self.ki_backend_id)
        if self.ki_device not in {key for key, _ in options}:
            self.ki_device = "auto"
        self.view_digizizer.set_ai_device_options(options, self.ki_device)

    @Slot(str)
    def _ai_backend_selected(self, backend_id):
        self._ki_backend_user_selected = True
        if backend_id == self.ki_backend_id:
            return
        previous_device = self.ki_device
        self.ki_backend_id = backend_id
        self.ki_model_path = None
        self._sync_ai_device_combo()
        if self.ki_device != previous_device:
            logger.info("%s cannot use %s; using Auto.", backend_id, previous_device)
        self._reload_ai_model()

    @Slot(str)
    def _ai_device_selected(self, device):
        if device == self.ki_device:
            return
        self.ki_device = device
        self._reload_ai_model()

    def _reload_ai_model(self):
        """Apply a changed model, device or model folder.

        Nothing is loaded while AI is off; the choice is only stored. While AI is on, the new model
        is loaded in the background and AI switches on again when it is ready.
        """
        if self._ai_initialization_worker is not None:
            self._ai_reload_pending = True
            return
        was_active = self._ai_active_or_requested()
        self._release_ai_segmenter()
        if was_active:
            self._scan_ai_devices()
            self._ensure_ai_segmenter(activate=True)
            self.view_digizizer.set_ai_mode_checked(True)

    def _ai_active_or_requested(self):
        return bool(self.digitizer_scene.ai_mode_enabled or self._ai_initialization_activate)

    def _prepare_ai_for_current_image(self, activate=False):
        """Keep AI active across images: encode only the new image, the model stays loaded.

        When AI is off, nothing is prepared.
        """
        if not activate or self.digitizer_scene.ai_controller.image is None:
            return
        self._ensure_ai_segmenter(activate=True)
        if self._ai_initialization_worker is not None:
            self.view_digizizer.set_ai_mode_checked(True)

    def _release_ai_segmenter(self, model_dropped=False):
        """Switch AI off completely: remove masks and prompts, drop the model and free its memory."""
        scene = self.digitizer_scene
        scene.set_ai_mode_enabled(False)
        scene.reset_ai_segmentation(reload_backend=False)
        scene.set_ai_preclassification_visible(False)
        self.view_digizizer.set_ai_preclassification_checked(False)
        had_model = scene.ai_controller.segmenter is not None
        scene.ai_controller.set_segmenter(None)
        self._ai_prepared_image = None
        if had_model or model_dropped:
            from graphis.app.ki.devices import release_ai_memory

            release_ai_memory()
            logger.info("AI switched off; model released from memory.")

    def _ensure_ai_segmenter(self, activate=True):
        from graphis.app.ki.factory import prepare_segmenter

        controller = self.digitizer_scene.ai_controller
        image = controller.image
        if image is None:
            self.view_digizizer.set_ai_mode_checked(False)
            return
        if self._ai_initialization_worker is not None:
            # A preparation is running; its result handler re-encodes the image now shown.
            if activate and not self._ai_initialization_activate:
                self._ai_initialization_activate = True
                self.start_waiting(f"Preparing {self.ki_backend_id} on {self.ki_device}...")
            return
        existing = controller.segmenter
        if existing is not None and image is self._ai_prepared_image:
            self._activate_ai_segmenter(existing)
            return
        # The worker owns the model until completion; image changes must not
        # reset a predictor while its encoder is running on another thread.
        controller.set_segmenter(None)
        self.digitizer_scene.set_ai_mode_enabled(False)
        self._ai_initialization_request = image
        self._ai_initialization_activate = True
        self.view_digizizer.set_ai_initializing(True)
        self.start_waiting(f"Preparing {self.ki_backend_id} on {self.ki_device}...")
        worker = Worker(
            prepare_segmenter, self.ki_backend_id, self.ki_model_path, self.ki_device,
            image.copy(), existing, not self._ki_backend_user_selected,
        )
        self._ai_initialization_worker = worker
        worker.signals.result.connect(self._ai_segmenter_ready)
        worker.signals.error.connect(self._ai_segmenter_failed)
        self.thread_pool.start(worker)

    def _finish_ai_initialization(self):
        image = self._ai_initialization_request
        activate = self._ai_initialization_activate
        self._ai_initialization_request = None
        self._ai_initialization_worker = None
        self._ai_initialization_activate = False
        self.view_digizizer.set_ai_initializing(False)
        self.stop_waiting()
        return image, activate

    @Slot(object)
    def _ai_segmenter_ready(self, segmenter):
        image, activate = self._finish_ai_initialization()
        controller = self.digitizer_scene.ai_controller
        if self._ai_reload_pending:
            # The model or device changed while this one was loading: discard it.
            self._ai_reload_pending = False
            del segmenter
            self._release_ai_segmenter(model_dropped=True)
            if activate:
                self._scan_ai_devices()
                self._ensure_ai_segmenter(activate=True)
            return
        if not activate:
            # AI was switched off while the model was loading: do not keep it.
            del segmenter
            self._release_ai_segmenter(model_dropped=True)
            return
        controller.set_segmenter(segmenter)
        if self.ki_backend_id != segmenter.backend_id:
            self.ki_backend_id = segmenter.backend_id
            self.view_digizizer.set_ai_backend_options(AI_BACKEND_OPTIONS, self.ki_backend_id)
            self._sync_ai_device_combo()
        if image is not controller.image:
            # The image changed while encoding; keep the loaded model and encode the image now shown.
            self._ai_prepared_image = None
            self._ensure_ai_segmenter(activate=True)
            return
        self._ai_prepared_image = image
        self._activate_ai_segmenter(segmenter)

    def _activate_ai_segmenter(self, segmenter):
        scene = self.digitizer_scene
        if (
            scene.instruction_active or scene.polygon_brush_enabled
            or scene.current_instruction != Instructions.No_Instruction
        ):
            self.view_digizizer.set_ai_mode_checked(False)
            logger.info("AI model ready on %s. Finish the geometry tool and enable AI again.", segmenter.device,
                        extra={"finished": True, "open": True})
            return
        self._clear_geometry_operation()
        scene.set_ai_mode_enabled(True)
        self.view_digizizer.set_ai_mode_checked(True)
        self._sync_geometry_action_availability()
        logger.info("AI backend active: %s; device: %s; model: %s", segmenter.backend_id,
                    segmenter.device, segmenter.model_path, extra={"finished": True, "open": True})

    @Slot(tuple)
    def _ai_segmenter_failed(self, error):
        image, activate = self._finish_ai_initialization()
        controller = self.digitizer_scene.ai_controller
        if self._ai_reload_pending:
            self._ai_reload_pending = False
            self._release_ai_segmenter()
            if activate:
                self._ensure_ai_segmenter(activate=True)
            return
        self._release_ai_segmenter()
        self.view_digizizer.set_ai_mode_checked(False)
        logger.error("Could not initialize AI backend: %s", error[2])
        if activate and image is controller.image:
            message_box.warning(self, "AI backend failed", str(error[1]))

    def clear_entries(self, action_stay_active=False, reset_visibility=True):
        self.current_item = None
        self._current_item_form_baseline = None

        if reset_visibility:
            self.point_visible = True
            self.circle_visible = True
            self.linestring_visible = True
            self.rectangle_visible = True
            self.polygon_visible = True
            self._sync_region_operations_toolbar()

        if not action_stay_active:
            self._clear_geometry_operation()

        self.model_image_region.clear()
        self.region_editor.clear_region_form()

    def _has_unsaved_region_metadata_changes(self):
        if self.current_item is None:
            return False
        data = self._metadata_from_region_form(show_errors=False)
        if data is None:
            return True
        baseline = self._current_item_form_baseline
        if baseline is None:
            baseline = self._metadata_for_dirty_comparison(self.current_item["data"])
        return data != baseline

    def _metadata_for_dirty_comparison(self, data):
        normalized = copy.deepcopy(data)
        name_value = normalized.get("name", normalized.get("Name", None))
        language_items = language_alternative_items(name_value)
        if language_items:
            default_text = ""
            alternatives = []
            for language, text in language_items:
                if language == "x-default":
                    default_text = text
                else:
                    alternatives.append((language, text))
            normalized = put_lang_alt_to_dict_or_remove(normalized, "name", default_text, alternatives)
        return normalized

    def _confirm_unsaved_region_metadata_changes(self, action_text):
        if not self._has_unsaved_region_metadata_changes():
            return True

        answer = message_box.warning(
            self,
            "Unsaved region metadata",
            f"The selected image region has unsaved metadata changes.\n\nSave them before you {action_text}?",
            message_box.StandardButton.Save | message_box.StandardButton.Discard | message_box.StandardButton.Cancel,
            message_box.StandardButton.Save,
        )
        if answer == message_box.StandardButton.Save:
            return self.save_data()
        if answer == message_box.StandardButton.Discard:
            return True
        return False

    def _guard_unsaved_region_metadata_changes(self, action_text):
        if self._confirm_unsaved_region_metadata_changes(action_text):
            return True
        self._restore_current_region_selection()
        return False

    def _restore_current_region_selection(self):
        if self.current_item is None:
            return
        object_id = self.current_item["id"]
        self._graph_selection_active = True
        try:
            self.digitizer_scene.activate_object(object_id)
            self.region_editor.select_object(object_id)
        finally:
            self._graph_selection_active = False

    def get_config_role(self, geom_type, config_attr):
        geom_type = base_object_type(geom_type)
        if geom_type == "rectangle":
            item_tag = getattr(self.config_rectangle, config_attr)
        elif geom_type == "polygon":
            item_tag = getattr(self.config_polygon, config_attr)
        elif geom_type == "point":
            item_tag = getattr(self.config_point, config_attr)
        elif geom_type == "linestring":
            item_tag = getattr(self.config_linestringstring, config_attr)
        else:
            item_tag = getattr(self.config_circle, config_attr)
        return item_tag

    def _append_current_user_contributor_if_role_missing(self, data, role):
        return _append_contributor_if_role_missing(
            data,
            self.config_default["CONTRIBUTOR_TAG"],
            role,
            self.user_information_popup.txt_user_indent.toPlainText(),
            self.user_information_popup.txt_user_name.toPlainText(),
        )

    @Slot(int)
    def change_finetuner(self, object_id):
        active_item = self.digitizer_scene.active_geometry_item()
        part_index = getattr(active_item, "geometry_part_index", None)
        ring_index = getattr(active_item, "geometry_ring_index", 0)
        if self.current_item and self.current_item.get("id") != object_id:
            if not self._guard_unsaved_region_metadata_changes("select another image region"):
                return

        data = self.db.db_load_object(object_id)
        jdata = json.loads(data["data"])
        original_jdata = copy.deepcopy(jdata)

        self._append_current_user_contributor_if_role_missing(
            jdata,
            self.get_config_role(data["object_type"], "region_creator_role"),
        )

        self.current_item = {"id": object_id, "data": jdata, "object_type": data["object_type"]}

        if self.current_item["data"] != original_jdata:
            self.db.update_object(obj_id=object_id, data=self.current_item["data"], log_validation=False)

        self.change_color(self.color_rectangle, "rectangle")
        self.change_color(self.color_polygon, "polygon")
        self.change_color(self.color_circle, "circle")
        self.change_color(self.color_linestring, "linestring")
        self.change_color(self.color_point, "point")

        self._clear_geometry_operation()
        self.parse_show_data(data["object_type"], self.current_item["data"])
        self._current_item_form_baseline = self._metadata_from_region_form(show_errors=False)
        self.model_image_region.load(self.current_item["data"])
        self.region_editor.resize_current_region_headers()
        self.image_region_view_load_all_image()
        if part_index is not None:
            self.digitizer_scene.delete_object(object_id)
            self.digitizer_scene.add_object(
                data["object_type"], jdata, object_id, self._geometry_color(data["object_type"])
            )
            self.digitizer_scene.activate_geometry_part(object_id, part_index, ring_index)
        else:
            self.digitizer_scene.activate_object(object_id)
        self._graph_selection_active = True
        try:
            if part_index is not None:
                self.region_editor.select_geometry_part(object_id, part_index, ring_index)
            else:
                self.region_editor.select_object(object_id)
        finally:
            self._graph_selection_active = False

    @Slot(int)
    def load_data(self, object_id, check_unsaved=True):
        if check_unsaved and self.current_item and self.current_item.get("id") != object_id:
            if not self._guard_unsaved_region_metadata_changes("select another image region"):
                return False

        self.clear_entries(reset_visibility=False)
        data = self.db.db_load_object(object_id)

        jdata = json.loads(data["data"])

        self.model_image_region.load(jdata)
        self.region_editor.resize_current_region_headers()
        self.current_item = {"id": object_id, "data": jdata, "object_type": data["object_type"]}

        self.parse_show_data(data["object_type"], self.current_item["data"])
        self._current_item_form_baseline = self._metadata_from_region_form(show_errors=False)
        self._ensure_object_type_visible(data["object_type"])
        self.digitizer_scene.activate_object(object_id)
        self._center_image_view_on_active_geometry()
        if not self._graph_selection_active:
            self._graph_selection_active = True
            try:
                self.region_editor.select_object(object_id)
            finally:
                self._graph_selection_active = False
        return True

    def _center_image_view_on_active_geometry(self):
        if self.view_digizizer.active_object_fully_visible():
            return
        center = self.digitizer_scene.active_object_center()
        if center is None:
            return
        self.view_digizizer._auto_fit_on_resize = False
        self.view_digizizer.centerOn(center)

    @Slot(str)
    def message_no_valid_polygon(self, message):
        logger.error(message)
        self.clear_entries(reset_visibility=False)

    @Slot(int)
    def add_data(self, object_id):
        self.clear_entries(reset_visibility=False)
        data = self.db.db_load_object(object_id)
        jdata = json.loads(data["data"])
        image = Path(self.current_image["name"])

        img_region_dict = {
            "regionBoundary": jdata["regionBoundary"],
            "rCtype": [
                {
                    "identifiers": [self.get_config_role(data["object_type"], "rctype_identifier")],
                    "name": self.get_config_role(data["object_type"], "rctype_name"),
                }
            ],
        }

        region_role_name = self.get_config_role(data["object_type"], "region_role_name")
        region_role_identifier = get_image_region_role(region_role_name)
        region_role_term = self.vocabulary_store.find(
            TARGET_REGION_ROLE,
            name=region_role_name,
            identifier=region_role_identifier,
        )
        self.region_editor.set_region_role(region_role_name, region_role_identifier, region_role_term)

        # RId
        # datetime.now().strftime('%y%j%H%M%S')
        dt = datetime.datetime.now().strftime("%y%m%dT%H:%M:%S")
        rid = image.stem + "_" + dt
        name_region = self.get_config_role(data["object_type"], "region_name_prefix")  # + dt
        img_region_dict = put_text_to_dict_or_remove(img_region_dict, "rId", rid)
        img_region_dict = put_lang_alt_to_dict_or_remove(img_region_dict, "name", name_region, [])

        # Role
        img_region_dict = put_struct_to_dict_or_remove(
            img_region_dict, tag="rRole", indentifier=region_role_identifier, name=region_role_name
        )

        # Region Creator
        img_region_dict = put_struc_tag(
            img_region_dict,
            self.config_default["CONTRIBUTOR_TAG"],
            self.get_config_role(data["object_type"], "region_creator_role"),
            indentifier=self.user_information_popup.txt_user_indent.toPlainText(),
            name=self.user_information_popup.txt_user_name.toPlainText(),
        )

        jdata = img_region_dict
        self.current_item = {"id": object_id, "data": jdata, "object_type": data["object_type"]}

        self.db.update_object(obj_id=self.current_item["id"], data=self.current_item["data"], log_validation=False)
        self.parse_show_data(data["object_type"], self.current_item["data"])
        self._current_item_form_baseline = self._metadata_from_region_form(show_errors=False)
        self.model_image_region.load(self.current_item["data"])
        self.region_editor.resize_current_region_headers()
        self.image_region_view_load_all_image()
        QtCore.QTimer.singleShot(0, lambda object_id=object_id: self._finalize_created_geometry(object_id))

    def _finalize_created_geometry(self, object_id):
        data = self.db.db_load_object(object_id)
        if data is None:
            self._sync_geometry_action_availability()
            return

        region_data = json.loads(data["data"])
        self.digitizer_scene.set_tooltip(object_id, "RId:" + text_value(region_data.get("rId", "")))
        self._ensure_object_type_visible(data["object_type"])
        self.digitizer_scene.clear_current_operation()
        if hasattr(self, "geom_operations"):
            self.geom_operations.clear_active_tool()
        self.digitizer_scene.activate_object(object_id)
        self._graph_selection_active = True
        try:
            self.region_editor.select_object(object_id)
        finally:
            self._graph_selection_active = False
        self._center_image_view_on_active_geometry()
        self._sync_geometry_action_availability()
        self._sync_undo_redo_actions()

    def parse_show_data(self, object_type, dict_item: dict):

        region_id = text_value(dict_item.get("rId", dict_item.get("RId", "")))
        name = dict_item.get("name", dict_item.get("Name", ""))

        self.region_editor.set_region_identity(region_id, name)

        dict_role = _first_metadata_struct(dict_item.get("rRole", dict_item.get("RRole", [])))
        if dict_role:
            role_name = entity_name(dict_role)
            role_identifier = entity_identifier(dict_role)
            role_term = self.vocabulary_store.find(
                TARGET_REGION_ROLE,
                name=role_name,
                identifier=role_identifier,
            )
            if role_term is None:
                role_term = self.vocabulary_store.ensure_metadata_term(TARGET_REGION_ROLE, role_name, role_identifier)
            elif role_identifier and role_identifier != role_term.identifier:
                role_term = VocabularyTerm(
                    TARGET_REGION_ROLE,
                    role_term.source,
                    role_term.name,
                    role_identifier,
                    role_term.qcode,
                    role_term.definition,
                )
            self.region_editor.set_region_role(role_term.name, role_term.identifier, role_term)

        dict_contr = dict_item.get(self.config_default["CONTRIBUTOR_TAG"], [])
        contributor_rows = _contributor_rows_from_metadata(dict_contr)
        for contributor in contributor_rows:
            role = contributor["role"]
            if role:
                self.vocabulary_store.ensure_metadata_term(
                    TARGET_CONTRIBUTOR_ROLE,
                    _vocabulary_name_from_identifier(role),
                    role,
                )
        self.region_editor.set_contributors(contributor_rows)

        dict_rctype = _first_metadata_struct(dict_item.get("rCtype", dict_item.get("RCtype", {})))
        if dict_rctype:
            type_name = entity_name(dict_rctype)
            type_identifier = entity_identifier(dict_rctype)
            self.vocabulary_store.ensure_metadata_term(TARGET_REGION_TYPE, type_name, type_identifier)
            self.region_editor.set_region_type(type_name, type_identifier)

        xmp_dc = metadata_lang_alt_value(dict_item, self.config_default["TAG_DESCRIBER"])
        self.region_editor.set_description_languages(language_alternative_items(xmp_dc))

        xmp_trans = metadata_lang_alt_value(dict_item, self.config_default["TAG_TRANSCRIBER"])
        self.region_editor.set_transcription_languages(language_alternative_items(xmp_trans))

    def _load_current_item_from_active_geometry(self):
        if self.current_item is not None:
            return True

        selected_item = self.digitizer_scene.active_geometry_item()
        object_id = getattr(selected_item, "obj_id", None) if selected_item is not None else None
        if object_id is not None:
            self.load_data(object_id)
        return self.current_item is not None

    def delete_geometry(self):
        if not self._db_ready_for("delete geometry"):
            return

        if not self._load_current_item_from_active_geometry():
            return

        item = self.digitizer_scene.active_geometry_item()
        part_index = getattr(item, "geometry_part_index", None)
        if part_index is not None:
            if not self._guard_unsaved_region_metadata_changes("delete geometry part"):
                return
            if not self._confirm_delete_geometry():
                return
            row = self.db.db_load_object(item.obj_id)
            try:
                data = remove_multigeometry_part(
                    json.loads(row["data"]),
                    row["img_width"],
                    row["img_height"],
                    part_index,
                    getattr(item, "geometry_ring_index", 0),
                )
            except (KeyError, IndexError, TypeError, ValueError) as err:
                logger.warning("Cannot delete geometry part: %s", err)
                return
            self.db.update_object(
                obj_id=item.obj_id,
                data=data,
                object_type=object_type_from_region(data) if "regionBoundary" in data else row["object_type"],
                action_label="Delete geometry part",
            )
            self._refresh_after_history_replay(item.obj_id)
            return

        self._clear_image_region_geometry(self.current_item["id"])

    @Slot(int)
    def clear_image_region_geometry(self, object_id):
        if not self._db_ready_for("clear image region geometry"):
            return

        self._clear_image_region_geometry(object_id)

    def _clear_image_region_geometry(self, object_id):
        data_row = self.db.db_load_object(object_id)
        if data_row is None:
            logger.warning("Selected image region no longer exists.")
            return

        region_data = json.loads(data_row["data"])
        if "regionBoundary" not in region_data:
            logger.warning("Selected image region has no geometry to clear.")
            return

        if not self._confirm_delete_geometry():
            return

        object_type = data_row["object_type"]
        data = copy.deepcopy(region_data)
        data.pop("regionBoundary", None)

        self.digitizer_scene.delete_object(object_id)
        self.db.update_object(
            obj_id=object_id,
            data=data,
            log_validation=False,
            action_label=f"Delete {object_type} geometry",
        )

        if self.current_item is None or self.current_item.get("id") == object_id:
            self.current_item = {"id": object_id, "data": data, "object_type": object_type}
            self._current_item_form_baseline = self._metadata_from_region_form(show_errors=False)
            self.model_image_region.load(data)
            self.region_editor.resize_current_region_headers()
        self.image_region_view_load_all_image()
        self._graph_selection_active = True
        try:
            self.region_editor.select_object(object_id)
        finally:
            self._graph_selection_active = False
        self._sync_geometry_action_availability()
        self._sync_undo_redo_actions()
        logger.info("Deleted geometry for image region %s.", object_id, extra={"finished": True, "open": True})

    @Slot(int)
    def edit_region_json_metadata(self, object_id):
        if not self._db_ready_for("edit additional image region metadata"):
            return

        data_row = self.db.db_load_object(object_id)
        if data_row is None:
            logger.warning("Selected image region no longer exists.")
            return

        if self.current_item is None or self.current_item.get("id") != object_id:
            if not self.load_data(object_id):
                return
        elif not self._guard_unsaved_region_metadata_changes("edit image region metadata"):
            return

        region_data = copy.deepcopy(self.current_item["data"])
        protected_keys = self._standard_region_metadata_keys()
        additional_data = self._additional_region_metadata(region_data, protected_keys)
        dialog = RegionJsonMetadataPopup(self, additional_data, protected_keys, object_id=object_id)
        if not dialog.exec():
            return
        if dialog.additional_data == additional_data:
            return

        updated_region_data = self._with_additional_region_metadata(region_data, dialog.additional_data, protected_keys)
        self._apply_region_json_metadata(object_id, updated_region_data, data_row["object_type"])

    def _standard_region_metadata_keys(self):
        keys = set(STANDARD_REGION_METADATA_KEYS)
        for config_key in ("CONTRIBUTOR_TAG", "TAG_DESCRIBER", "TAG_TRANSCRIBER"):
            value = self.config_default.get(config_key)
            if value:
                keys.add(value)
        return keys

    def _additional_region_metadata(self, region_data, protected_keys):
        return {key: copy.deepcopy(value) for key, value in region_data.items() if key not in protected_keys}

    def _with_additional_region_metadata(self, region_data, additional_data, protected_keys):
        merged = {key: copy.deepcopy(value) for key, value in region_data.items() if key in protected_keys}
        merged.update(copy.deepcopy(additional_data))
        return merged

    def _apply_region_json_metadata(self, object_id, region_data, object_type):
        updated_object_type = object_type_from_region(region_data)
        if updated_object_type not in {
            "rectangle",
            "polygon",
            "multipolygon",
            "circle",
            "point",
            "multipoint",
            "linestring",
            "multilinestring",
        }:
            updated_object_type = object_type
        try:
            self.db.update_object(
                obj_id=object_id,
                data=region_data,
                object_type=updated_object_type,
                action_label="Edit additional image region metadata",
            )
        except ValueError as err:
            logger.warning("Cannot update image region: %s", err)
            return
        self.current_item = {"id": object_id, "data": copy.deepcopy(region_data), "object_type": updated_object_type}
        self.parse_show_data(updated_object_type, self.current_item["data"])
        self._current_item_form_baseline = self._metadata_from_region_form(show_errors=False)
        self.model_image_region.load(self.current_item["data"])
        self.region_editor.resize_current_region_headers()
        self.image_region_view_load_all_image()
        self.digitizer_scene.activate_object(object_id)
        self._graph_selection_active = True
        try:
            self.region_editor.select_object(object_id)
        finally:
            self._graph_selection_active = False
        self._sync_geometry_action_availability()
        self._sync_undo_redo_actions()
        logger.info(
            "Updated additional image region metadata for image region %s.",
            object_id,
            extra={"finished": True, "open": True},
        )

    @Slot(int, str)
    def assign_geometry_to_image_region(self, object_id, object_type):
        if object_type not in {"rectangle", "polygon", "circle", "point", "linestring"}:
            logger.error("Unsupported geometry type: %s", object_type)
            return
        if not self._db_ready_for("assign image region geometry"):
            return
        if self.current_image is None:
            logger.warning("Cannot assign geometry because no image is displayed.")
            return
        if self.db.db_load_object(object_id) is None:
            logger.warning("Selected image region no longer exists.")
            return

        if self.current_item is None or self.current_item.get("id") != object_id:
            if not self.load_data(object_id):
                return
        elif not self._guard_unsaved_region_metadata_changes("assign new geometry"):
            return

        self.digitizer_scene.clear_current_operation()
        self.digitizer_scene.clear_active_object()
        self.digitizer_scene.set_geometry_assignment_target(object_id)
        self._set_create_geometry_instruction(object_type)
        logger.info("Draw a %s to assign it to the selected image region.", object_type)

    @Slot(int)
    def zoom_to_image_region(self, object_id):
        if not self._db_ready_for("zoom to image region"):
            return
        if self.db.db_load_object(object_id) is None:
            logger.warning("Selected image region no longer exists.")
            return

        if self.current_item is None or self.current_item.get("id") != object_id:
            self.load_data(object_id)
        else:
            self._ensure_object_type_visible(self.current_item.get("object_type"))
            self.digitizer_scene.activate_object(object_id)

        if self.digitizer_scene.active_geometry_item() is None:
            logger.warning("Selected image region has no geometry to zoom to.")
            return
        self.view_digizizer.zoom_to_active_object()

    def delete_object(self):
        if not self._db_ready_for("delete image region"):
            return

        if not self._load_current_item_from_active_geometry():
            return

        self._delete_image_region(self.current_item["id"])

    @Slot(int)
    def delete_image_region(self, object_id):
        if not self._db_ready_for("delete image region"):
            return

        self._delete_image_region(object_id)

    def _delete_image_region(self, object_id):
        data_row = self.db.db_load_object(object_id)
        if data_row is None:
            logger.warning("Selected image region no longer exists.")
            return

        if self.current_item is None or self.current_item.get("id") != object_id:
            self.load_data(object_id)

        if not self._confirm_delete_image_region():
            return

        self.digitizer_scene.delete_object(object_id)
        self.db.db_delete_geometry(object_id)

        if self.current_item is not None and self.current_item.get("id") == object_id:
            self.current_item = None
            self.clear_entries(reset_visibility=False)
        self.image_region_view_load_all_image()
        self._sync_geometry_action_availability()
        self._sync_undo_redo_actions()
        logger.info("Deleted image region %s.", object_id, extra={"finished": True, "open": True})

    def _confirm_delete_geometry(self):
        answer = message_box.warning(
            self,
            "Delete geometry?",
            (
                "Delete only the selected image region geometry?\n\n"
                "The image region metadata will be kept. Use Undo to restore it in this session."
            ),
            message_box.StandardButton.Yes | message_box.StandardButton.Cancel,
            message_box.StandardButton.Cancel,
        )
        return answer == message_box.StandardButton.Yes

    def _confirm_delete_image_region(self):
        answer = message_box.warning(
            self,
            "Delete image region?",
            "Delete the selected image region completely?\n\nUse Undo to restore it in this session.",
            message_box.StandardButton.Yes | message_box.StandardButton.Cancel,
            message_box.StandardButton.Cancel,
        )
        return answer == message_box.StandardButton.Yes

    def set_instruction(self, action: str):
        edit_actions = {"move_geometry", "change_geometry", "add_point", "remove_point"}
        create_actions = {"create_rectangle", "create_polygon", "create_circle", "create_point", "create_linestring"}
        selected_item = self.digitizer_scene.active_geometry_item()
        self.digitizer_scene.clear_geometry_assignment_target()

        if action in create_actions | edit_actions:
            if not self._guard_unsaved_region_metadata_changes("start a geometry operation"):
                self._sync_geometry_action_availability()
                return
            self.view_digizizer.set_ai_mode_checked(False)

        if action in {"move_geometry", "change_geometry"} and selected_item is None:
            self._sync_geometry_action_availability()
            return
        if action in {"add_point", "remove_point"} and getattr(selected_item, "object_type", None) not in [
            "polygon",
            "linestring",
        ]:
            self._sync_geometry_action_availability()
            return

        if not self.digitizer_scene.instruction_active:
            if action in create_actions:
                self.clear_entries(reset_visibility=False)
                self.digitizer_scene.clear_active_object()
                self._graph_selection_active = True
                try:
                    self.region_editor.clear_selection()
                finally:
                    self._graph_selection_active = False
            elif action in edit_actions:
                self._clear_geometry_operation()
            else:
                self.clear_entries()

            if action == "create_rectangle":
                self.current_item = None
                self._ensure_object_type_visible("rectangle")
                self.digitizer_scene.current_instruction = Instructions.Rectangle_Instruction
            elif action == "create_polygon":
                self.current_item = None
                self._ensure_object_type_visible("polygon")
                self.digitizer_scene.current_instruction = Instructions.Polygon_Instruction
            elif action == "create_circle":
                self._ensure_object_type_visible("circle")
                self.digitizer_scene.current_instruction = Instructions.Circle_Instruction
            elif action == "create_linestring":
                self._ensure_object_type_visible("linestring")
                self.digitizer_scene.current_instruction = Instructions.Linestring_Instruction
            elif action == "create_point":
                self._ensure_object_type_visible("point")
                self.digitizer_scene.current_instruction = Instructions.Point_Instruction
            elif action == "move_geometry":
                self.digitizer_scene.current_instruction = Instructions.Move_Instruction
            elif action == "change_geometry":
                self.digitizer_scene.current_instruction = Instructions.Change_Instruction
            elif action == "add_point":
                self.digitizer_scene.current_instruction = Instructions.Add_Point
            elif action == "remove_point":
                self.digitizer_scene.current_instruction = Instructions.Remove_Point
            if hasattr(self, "geom_operations"):
                self.geom_operations.set_active_tool(action)

    def _set_create_geometry_instruction(self, object_type):
        action = f"create_{object_type}"
        self._ensure_object_type_visible(object_type)
        if object_type == "rectangle":
            self.digitizer_scene.current_instruction = Instructions.Rectangle_Instruction
        elif object_type == "polygon":
            self.digitizer_scene.current_instruction = Instructions.Polygon_Instruction
        elif object_type == "circle":
            self.digitizer_scene.current_instruction = Instructions.Circle_Instruction
        elif object_type == "linestring":
            self.digitizer_scene.current_instruction = Instructions.Linestring_Instruction
        elif object_type == "point":
            self.digitizer_scene.current_instruction = Instructions.Point_Instruction
        else:
            return

        if hasattr(self, "geom_operations"):
            self.geom_operations.set_active_tool(action)
        self._sync_geometry_action_availability()

    def clean_all_views_and_tables(self, db_save=False):
        self.digitizer_scene.clear_current_operation()
        self.digitizer_scene.clear_active_object()
        self.digitizer_scene.clear()

        self.clear_entries()
        self.model_image_region_all.clear()
        self.region_editor.clear_graph()
        self.lbl_image_name.setText("")
        self.lbl_image_path.setText("")
        self.table_preview.setModel(None)
        self.image_list = []
        self.current_image = None
        self.current_item = None
        self._current_item_form_baseline = None
        self.view_digizizer.set_visual_rotation(0, emit_signal=False)
        self.image_region_summaries = {}
        self.count_rectangle = 0
        self.count_polygon = 0
        self.count_circle = 0
        self.count_linestring = 0
        self.count_point = 0
        self.count_multipoint = 0
        self.count_multilinestring = 0
        self.count_multipolygon = 0
        self.database_statistics_popup.set_counts(
            image=0,
            multipoint=0,
            multilinestring=0,
            multipolygon=0,
            rectangle=0,
            polygon=0,
            circle=0,
            point=0,
            linestring=0,
            valid=0,
            warning=0,
            error=0,
        )
        if self.db.db_is_set and not self.db.is_busy and not db_save:
            self.db.db_close()
            self.db.db_is_set = False
            self._visual_rotations_by_image_id = {}
        self._sync_database_status_name()
        self._sync_undo_redo_actions()

    def load_existing_db(self):
        if not self._db_ready_for("load database", require_database=False):
            return
        if not self._guard_unsaved_region_metadata_changes("load another database"):
            return

        self.digitizer_scene.clear_current_operation()
        db_path, _ = QFileDialog.getOpenFileName(
            self, caption="Load Database", dir="../..", filter="SQLITE Files (*.sqlite)"
        )
        if db_path:
            # clear scene GIS and digitizer
            self.clean_all_views_and_tables()

            self.db.db_load(Path(db_path), self.user)

            # self.db.db_check_abs_path()

            self.digitizer_scene.db = self.db
            print("Existing database was loaded: " + Path(db_path).name)
            self.loader_all()
            self._sync_database_status_name()

    def close_database(self):
        if not self._db_ready_for("close database"):
            return
        if self.image_loading:
            logger.warning("Cannot close database while an image is loading.")
            return
        if not self._guard_unsaved_region_metadata_changes("close the database"):
            return

        sqlite_name = self.db.db_path.name
        self.clean_all_views_and_tables()
        logger.info("Closed database: %s", sqlite_name, extra={"finished": True})

    def loader_all(self):

        images = self.db.db_load_images_list()

        if not images:
            return

        self.image_region_summaries = self._image_region_summaries()
        self._apply_preview_summary_totals(self.image_region_summaries)

        self.model = PreviewModel()
        self.table_preview.setModel(self.model)

        self.image_list = []
        missing_images = 0

        for x in images:
            if x["preview"] is not None:
                # rel = os.path.relpath(x['path'], self.db.db_path)

                stored_path = Path(x["path"])
                if stored_path.is_absolute():
                    new_path = stored_path
                else:
                    new_path = Path(os.path.normpath(os.path.join(self.db.db_path, stored_path)))
                missing_file = not new_path.exists()
                if missing_file:
                    missing_images += 1
                self.image_list.append([new_path, x["id"]])
                pixmap = QPixmap()
                pixmap.loadFromData(x["preview"], "JPG")
                # image = QImage(pixmap)
                summary = self.image_region_summaries.get(x["id"], {})
                image_metadata = image_metadata_dict(x["image_metadata"])
                exif_rotation = image_metadata_visual_rotation(image_metadata)
                exif_orientation_present = image_metadata_orientation_present(image_metadata)
                visual_rotation = self._visual_rotations_by_image_id.get(x["id"], exif_rotation)
                item = PreviewModelData(
                    x["id"],
                    os.fspath(new_path),
                    new_path.name,
                    pixmap,
                    polygon_number=summary.get("polygon", 0) + summary.get("multipolygon", 0),
                    rectangle_number=summary.get("rectangle", 0),
                    circle_number=summary.get("circle", 0),
                    point_number=summary.get("point", 0) + summary.get("multipoint", 0),
                    linestring_number=summary.get("linestring", 0) + summary.get("multilinestring", 0),
                    missing_file=missing_file,
                    error_image=summary.get("error_image", False),
                    warning_image=summary.get("warning_image", False),
                    visual_rotation_degrees=visual_rotation,
                    exif_rotation_degrees=exif_rotation,
                    exif_orientation_present=exif_orientation_present,
                    image_metadata=image_metadata,
                )
                self.model.appendData(item)

            else:
                print("\tEmpty Preview in database image: ", x["path"])

        self.table_preview.doItemsLayout()
        self.table_preview.viewport().update()

        if missing_images:
            logger.warning("%s image files are missing on disk and are marked red in the preview.", missing_images)

    def create_new_db(self):
        if not self._db_ready_for("create database", require_database=False):
            return
        if not self._guard_unsaved_region_metadata_changes("create a new database"):
            return

        self.digitizer_scene.clear_current_operation()
        db_path, _ = QFileDialog.getSaveFileName(caption="Create Database", dir="../..", filter="SQLITE Files (*.sqlite)")

        if db_path:
            self.clean_all_views_and_tables()
            path = path_with_forced_suffix(db_path, ".sqlite")
            if path.exists():
                try:
                    path.unlink()
                    logger.info("DB file was overwritten: %s", path)
                except OSError as err:
                    logger.exception(
                        "DB file seems to be locked. Maybe it is opened by another program: %s",
                        err,
                    )
                    return

            success = self.db.db_create(path, self.user)

            if success:
                self.digitizer_scene.db = self.db
                logger.info("New database was created: %s", path.name, extra={"finished": True})
                self.model = PreviewModel()
                self.table_preview.setModel(self.model)
                self._sync_database_status_name()

    def load_input_image_folder(self, subfolder=False, single_image=False):

        if not self._db_ready_for("import images"):
            return

        image_list = []
        if single_image:
            image_path, _ = QFileDialog.getOpenFileName(self, caption="Select image")
            if image_path:
                image_list = [Path(image_path)]
        elif subfolder:
            folder_path = QFileDialog.getExistingDirectory(self, caption="Select image folder")
            if folder_path:
                image_list = image_files_in_folder(Path(folder_path), recursive=True)
        else:
            image_path, _ = QFileDialog.getOpenFileName(
                self, caption="Click on one image. Only identical file formats are imported"
            )
            if image_path:
                image_path = Path(image_path)
                image_list = sorted(image_path.parent.glob("*" + image_path.suffix))

        if not image_list:
            return
        if not self._metadata_tool_ready_for_import():
            return

        logger.info("Importing images.")
        self.db.lock("importing images", f"{len(image_list)} files")
        worker = Worker(
            import_images,
            image_list,
            self.db.db_path,
            self.user,
            self.config_metadata_tool.tool,
            self._metadata_tool_path(),
            self.config_default,
        )
        worker.signals.result.connect(self.thread_output_image_import)
        worker.signals.error.connect(self.thread_output_db_error)
        self.thread_pool.start(worker)
        self.start_waiting("Importing images...")

    def save_image_regions(self, keep_orig=False):

        if not self._db_ready_for("write image metadata"):
            return

        self.db.lock("writing image metadata")
        worker = Worker(
            meta_writer,
            self.db,
            self.user,
            keep_orig,
            self._metadata_tool_path(),
            self.config_metadata_tool.tool,
            self.config_default,
        )
        worker.signals.result.connect(self.thread_output_exif)
        worker.signals.error.connect(self.thread_output_db_error)
        self.start_waiting("Writing metadata...")
        self.thread_pool.start(worker)

    def import_csv(self):
        if not self._db_ready_for("import CSV"):
            return
        if not self._guard_unsaved_region_metadata_changes("import CSV data"):
            return

        csv_path, _ = QFileDialog.getOpenFileName(self, caption="Import rectangle CSV", filter="CSV (*.csv)")
        if not csv_path:
            return

        self.db.lock("importing CSV", Path(csv_path).name)
        worker = Worker(
            import_rectangle_csv_in_process,
            csv_path,
            self.db.db_path,
            self.user,
            self.config_default["TAG_DESCRIBER"],
            self.config_default["TAG_TRANSCRIBER"],
            self.config_default["CONTRIBUTOR_TAG"],
            {
                "rectangle": self.get_config_role("rectangle", "region_creator_role"),
                "polygon": self.get_config_role("polygon", "region_creator_role"),
                "circle": self.get_config_role("circle", "region_creator_role"),
                "point": self.get_config_role("point", "region_creator_role"),
                "linestring": self.get_config_role("linestring", "region_creator_role"),
            },
            self.user_information_popup.txt_user_indent.toPlainText(),
            self.user_information_popup.txt_user_name.toPlainText(),
            self.config_metadata_tool.tool,
            self._metadata_tool_path(),
        )
        worker.signals.result.connect(self.thread_output_csv_import)
        worker.signals.error.connect(self.thread_output_db_error)
        self.thread_pool.start(worker)
        self.start_waiting("Importing CSV...")

    def save_csv(self):
        if self.db.db_is_set:
            assert self.db.db_path is not None

            objs = self.db.db_load_objects_all()

            if objs:
                image_path, _ = QFileDialog.getSaveFileName(self, caption="Export rectangle CSV", filter="CSV (*.csv)")
                if image_path:
                    image_path = path_with_forced_suffix(image_path, ".csv")
                    export_rectangle_csv(
                        objs,
                        image_path,
                        self.db.db_path,
                        self.config_default["TAG_DESCRIBER"],
                        self.config_default["TAG_TRANSCRIBER"],
                    )
                    logger.info("CSV export finished: %s", image_path, extra={"finished": True})

            else:
                logger.info("Nothing to export.", extra={"finished": True})


def available_screen_size() -> tuple[int, int]:
    rect = wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)  # SPI_GETWORKAREA
    return rect.right - rect.left, rect.bottom - rect.top


def apply_auto_scale_for_small_screen():
    if sys.platform == "win32":
        app_min_width = 1100
        app_min_height = 950
        margin = 40

        screen_width, screen_height = available_screen_size()

        scale = min(
            (screen_width - margin) / app_min_width,
            (screen_height - margin) / app_min_height,
            1.0,
        )

        if scale < 1.0:
            os.environ["QT_SCALE_FACTOR"] = f"{scale:.2f}"
            return scale

    if sys.platform.startswith("linux"):
        os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
        os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
        return None

    return None


def main():

    freeze_support()
    QtCore.QCoreApplication.setOrganizationName(ORGANIZATION_NAME)
    QtCore.QCoreApplication.setApplicationName(APP_NAME)

    auto_scale_factor = apply_auto_scale_for_small_screen()

    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication()
    window = MainWindow()

    window.auto_scale_factor = auto_scale_factor
    #  app.installEventFilter(window)
    app.setWindowIcon(resource_icon("icon.png"))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
