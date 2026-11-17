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

import copy
import json

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHeaderView, QTableWidgetItem, QWidget

from graphis.app.gui.region_editor_ui import RegionEditorUi
from graphis.app.imgregion.region_graph_model import RegionNode, find_child_list, first_text, region_shape
from graphis.app.imgregion.region_graph_scene import RegionGraphScene
from graphis.app.var_classes import (
    COLOR_CIRCLE_START,
    COLOR_LINESTRING_START,
    COLOR_POINT_START,
    COLOR_POLYGON_START,
    COLOR_RECTANGLE_START,
)
from graphis.interface.imgregion_adapter import language_alternative_items
from graphis.interface.region_membership import PARENT_KEYS, parent_object_map

_REGION_BACKGROUND = QColor(40, 44, 52)
_REGION_BACKGROUND_STYLE = "rgb(40, 44, 52)"


class RegionEditorWidget(QWidget):
    objectSelected = Signal(int)
    objectDeselected = Signal()
    assignGeometryRequested = Signal(int, str)
    clearGeometryRequested = Signal(int)
    zoomToRegionRequested = Signal(int)
    deleteImageRegionRequested = Signal(int)
    restoreOriginalRequested = Signal(int)
    jsonMetadataRequested = Signal(int)
    mergeRegionsRequested = Signal(int, int, str)
    createContainerRequested = Signal(str)
    groupRegionsRequested = Signal(object, str)
    groupRegionsIntoRequested = Signal(object, int)
    assignParentRequested = Signal(int)
    mergeTargetRequested = Signal(int, str)
    detachGeometryPartRequested = Signal(int, int)
    detachParentRequested = Signal(int)
    geometryPartSelected = Signal(int, int, int)
    regionRoleVocabularyRequested = Signal()
    regionTypeVocabularyRequested = Signal()
    contributorRoleVocabularyRequested = Signal()
    descriptionSpeechRequested = Signal()
    transcriptionSpeechRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = RegionEditorUi()
        self.ui.setup(self)
        self.graph_scene = RegionGraphScene(self)
        self.ui.graphicsView.setScene(self.graph_scene)

        self.nodes = []
        self.nodes_by_id = {}
        self._region_form_save_callback = None
        self._geometry_colors = {
            "point": COLOR_POINT_START, "circle": COLOR_CIRCLE_START, "linestring": COLOR_LINESTRING_START,
            "rectangle": COLOR_RECTANGLE_START, "polygon": COLOR_POLYGON_START,
        }

        self.graph_scene.regionSelected.connect(self._region_selected)
        self.graph_scene.geometryPartSelected.connect(
            lambda owner_id, index, ring: self.geometryPartSelected.emit(int(owner_id), index, ring)
        )
        self.graph_scene.assignParentRequested.connect(lambda object_id: self.assignParentRequested.emit(int(object_id)))
        self.graph_scene.mergeTargetRequested.connect(
            lambda object_id, mode: self.mergeTargetRequested.emit(int(object_id), mode)
        )
        self.graph_scene.detachGeometryPartRequested.connect(
            lambda object_id, index: self.detachGeometryPartRequested.emit(int(object_id), index)
        )
        self.graph_scene.detachParentRequested.connect(lambda object_id: self.detachParentRequested.emit(int(object_id)))
        self.graph_scene.selectionCleared.connect(self._selection_cleared)
        self.graph_scene.assignGeometryRequested.connect(self._assign_geometry_requested)
        self.graph_scene.clearGeometryRequested.connect(self._clear_geometry_requested)
        self.graph_scene.zoomToRegionRequested.connect(self._zoom_to_region_requested)
        self.graph_scene.deleteImageRegionRequested.connect(self._delete_image_region_requested)
        self.graph_scene.restoreOriginalRequested.connect(self._restore_original_requested)
        self.graph_scene.jsonMetadataRequested.connect(self._json_metadata_requested)
        self.graph_scene.mergeRegionsRequested.connect(self._merge_regions_requested)
        self.graph_scene.createContainerRequested.connect(self.createContainerRequested.emit)
        self.graph_scene.groupSelectedRequested.connect(self._group_regions_requested)
        self.graph_scene.groupSelectedIntoRequested.connect(self._group_regions_into_requested)
        self.graph_scene.activeValidationIssuesChanged.connect(self.ui.graphicsView.set_validation_issues)
        self.ui.graphicsView.autoLayoutRequested.connect(self.auto_layout)

    def load_graphis_objects(self, objects, validation_issues=None, image_width=None, image_height=None):
        validation_issues = validation_issues or {}
        regions = []
        root_object_ids = []
        self.graph_scene.set_image_size(image_width, image_height)

        for obj in objects:
            attributes = self._object_attributes(obj)
            if not isinstance(attributes, dict):
                continue

            region = copy.deepcopy(attributes)
            raw_object_id = obj.get("id")
            object_id = (
                str(raw_object_id) if raw_object_id is not None and raw_object_id != "" else f"object-{len(regions) + 1}"
            )
            object_type = obj.get("object_type")
            root_object_ids.append(object_id)

            if object_type and "regionBoundary" in region:
                region["regionBoundary"].setdefault("rbShape", object_type)

            regions.append(region)

        self.nodes = self._build_nodes(
            regions,
            parent_id=None,
            base_path=["imageRegion"],
            depth=0,
            root_object_ids=root_object_ids,
            validation_issues=validation_issues,
        )
        self._connect_referenced_parents()
        self._add_multigeometry_parts()
        self._index_nodes()
        self._apply_geometry_colors()
        self.graph_scene.set_nodes(self.nodes)
        self.graph_scene.auto_layout()
        QTimer.singleShot(0, self.ui.graphicsView.fit_graph)

    def set_geometry_color(self, shape, color):
        color = QColor(color)
        if color.isValid():
            self._geometry_colors[shape] = color.name()
            self._apply_geometry_colors()
            for item in self.graph_scene.node_items.values():
                item.refresh_colors()

    def _apply_geometry_colors(self):
        for node in self.nodes_by_id.values():
            shape = region_shape(node.region)
            shape = {"multipoint": "point", "multilinestring": "linestring", "multipolygon": "polygon"}.get(shape, shape)
            node.geometry_color = self._geometry_colors.get(shape, "#202832")

    def set_selection_guidance(self, text=""):
        self.ui.selection_guidance.setText(text)
        self.ui.selection_guidance.setVisible(bool(text))

    def clear_graph(self):
        self.set_selection_guidance()
        self.nodes = []
        self.nodes_by_id = {}
        self.graph_scene.clear_graph()

    def select_object(self, object_id):
        self.graph_scene.select_region(str(object_id))

    def select_geometry_part(self, object_id, part_index, ring_index=0):
        candidates = []
        for node in self.nodes_by_id.values():
            if (node.geometry_owner_id or node.object_id) == str(object_id) and node.geometry_part_index == part_index:
                if node.geometry_ring_index == ring_index:
                    self.graph_scene.select_region(node.object_id)
                    return
                if node.geometry_ring_index is None:
                    candidates.append(node)
        if candidates:
            self.graph_scene.select_region(candidates[0].object_id)

    def clear_selection(self):
        self.graph_scene.clear_region_selection()

    def request_select_object(self, object_id):
        self.graph_scene.request_select_region(str(object_id))

    def request_clear_selection(self):
        self.graph_scene.request_clear_region_selection()

    def fit_graph_delayed(self):
        QTimer.singleShot(0, self.ui.graphicsView.fit_graph)
        QTimer.singleShot(120, self.ui.graphicsView.fit_graph)

    def auto_layout(self):
        self.graph_scene.auto_layout()
        self.ui.graphicsView.fit_graph()

    def configure_region_tables(self, current_model, all_model):
        self.ui.image_region_view.setAlternatingRowColors(True)
        self.set_current_region_model(current_model)
        self.set_all_region_model(all_model)

    def set_current_region_model(self, model):
        self.ui.image_region_view.setModel(model)
        self.resize_current_region_headers()

    def set_all_region_model(self, model):
        self.ui.image_all_region.setModel(model)
        self.resize_all_region_headers()

    def resize_current_region_headers(self):
        header = self.ui.image_region_view.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

    def resize_all_region_headers(self):
        header = self.ui.image_all_region.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

    def connect_region_controls(self, save_callback):
        self.ui.btn_object_save.clicked.connect(save_callback)
        self._region_form_save_callback = save_callback
        self._install_region_form_enter_shortcut()
        self.ui.btn_expand_all.clicked.connect(self.ui.image_region_view.expandAll)
        self.ui.btn_collapse_all.clicked.connect(self.ui.image_region_view.collapseAll)
        self.ui.btn_expand_all_all_region.clicked.connect(self.ui.image_all_region.expandAll)
        self.ui.btn_collapse_all_all_region.clicked.connect(self.ui.image_all_region.collapseAll)
        self.ui.btn_add_region_name_lang.clicked.connect(self.add_region_name_language_row)
        self.ui.btn_remove_region_name_lang.clicked.connect(self.remove_region_name_language_rows)
        self.ui.btn_add_description_lang.clicked.connect(self.add_description_language_row)
        self.ui.btn_remove_description_lang.clicked.connect(self.remove_description_language_rows)
        self.ui.btn_add_transcription_lang.clicked.connect(self.add_transcription_language_row)
        self.ui.btn_remove_transcription_lang.clicked.connect(self.remove_transcription_language_rows)
        self.ui.btn_record_description_speech.clicked.connect(
            lambda checked=False: self.descriptionSpeechRequested.emit()
        )
        self.ui.btn_record_transcription_speech.clicked.connect(
            lambda checked=False: self.transcriptionSpeechRequested.emit()
        )
        self.ui.btn_add_contributor.clicked.connect(self.add_contributor_row)
        self.ui.btn_remove_contributor.clicked.connect(self.remove_contributor_rows)
        self.ui.btn_select_contributor_role_vocab.clicked.connect(self.contributorRoleVocabularyRequested)
        self.ui.btn_select_region_role_vocab.clicked.connect(self.regionRoleVocabularyRequested)
        self.ui.btn_select_region_type_vocab.clicked.connect(self.regionTypeVocabularyRequested)

    def region_form_values(self):
        return {
            "region_id": self.ui.txt_rid.toPlainText(),
            "region_name": self.region_name_default_text(),
            "region_name_alternatives": self.region_name_language_alternatives(),
            "region_type_identifier": self.ui.txt_rctype_indent.toPlainText(),
            "region_type_name": self.ui.txt_rctype_name.toPlainText(),
            "region_role_identifier": self.ui.txt_rrole_ident.toPlainText(),
            "region_role_name": self.ui.txt_rrole_name.toPlainText(),
            "contributors": self.contributor_rows(),
            "description_languages": self.description_language_rows(),
            "transcription_languages": self.transcription_language_rows(),
        }

    def eventFilter(self, watched, event):
        if (
            event.type() == QEvent.Type.KeyPress
            and watched in self._region_form_enter_targets()
            and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
        ):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                return False
            if self._region_form_save_callback is not None:
                self._region_form_save_callback()
            self._clear_region_form_text_focus()
            event.accept()
            return True
        return super().eventFilter(watched, event)

    def _clear_region_form_text_focus(self):
        focused = self.focusWidget()
        if focused in self._region_form_enter_targets():
            focused.clearFocus()
            return
        for widget in self._region_form_text_widgets():
            if widget.hasFocus():
                widget.clearFocus()
                return
            viewport = widget.viewport()
            if viewport is not None and viewport.hasFocus():
                widget.clearFocus()
                viewport.clearFocus()
                return

    def _install_region_form_enter_shortcut(self):
        for target in self._region_form_enter_targets():
            target.installEventFilter(self)

    def _region_form_enter_targets(self):
        targets = []
        for widget in self._region_form_text_widgets():
            targets.append(widget)
            viewport = widget.viewport()
            if viewport is not None:
                targets.append(viewport)
        return tuple(targets)

    def _region_form_text_widgets(self):
        return (
            self.ui.txt_rid,
            self.ui.txt_rrole_ident,
            self.ui.txt_rrole_name,
            self.ui.txt_rctype_indent,
            self.ui.txt_rctype_name,
        )

    def clear_region_form(self):
        for widget in (
            self.ui.txt_rid,
            self.ui.txt_rrole_ident,
            self.ui.txt_rrole_name,
            self.ui.txt_rctype_name,
            self.ui.txt_rctype_indent,
        ):
            widget.setPlainText("")
        self.ui.table_region_name_lang.setRowCount(0)
        self.ui.table_description_lang.setRowCount(0)
        self.ui.table_transcription_lang.setRowCount(0)
        self.ui.table_contributors.setRowCount(0)

    def set_region_role_identifier(self, identifier):
        self.ui.txt_rrole_ident.setPlainText(identifier)

    def set_region_role(self, role_name, identifier=None, term=None):
        self.ui.txt_rrole_name.setPlainText(role_name)
        self.set_region_role_identifier(identifier if identifier is not None else getattr(term, "identifier", ""))

    def apply_region_role_term(self, term):
        self.set_region_role(term.name, term.identifier, term)

    def apply_region_type_term(self, term):
        self.set_region_type(term.name, term.identifier)

    def set_region_identity(self, region_id, name):
        self.ui.txt_rid.setPlainText(region_id)
        self.set_region_name_languages(language_alternative_items(name))

    def set_region_name_languages(self, languages):
        self._set_language_rows(self.ui.table_region_name_lang, languages)

    def add_region_name_language_row(self, checked=False):
        self._add_language_row(self.ui.table_region_name_lang)

    def remove_region_name_language_rows(self):
        self._remove_language_rows(self.ui.table_region_name_lang)

    def region_name_language_alternatives(self):
        return [(language, text) for language, text in self.region_name_language_rows() if language != "x-default"]

    def region_name_default_text(self):
        return self._language_default_text(self.ui.table_region_name_lang)

    def region_name_language_rows(self):
        return self._language_rows(self.ui.table_region_name_lang)

    def region_name_language_error(self):
        return self._language_table_error("Region name", self.region_name_language_rows())

    def description_language_error(self):
        return self._language_table_error("Description", self.description_language_rows())

    def transcription_language_error(self):
        return self._language_table_error("Transcription", self.transcription_language_rows())

    def _language_table_error(self, label, rows):
        languages = set()
        for row, (language, text) in enumerate(rows, start=1):
            if not language and not text:
                return f"{label} language row {row} is empty. Fill it or remove the row."
            if not language:
                return f"{label} language row {row} has no language tag."
            if not text:
                return f"{label} language row {row} has no text."
            if language in languages:
                return f"{label} language '{language}' is used more than once."
            languages.add(language)
        return ""

    def _has_region_name_language(self, language):
        return self._has_language(self.ui.table_region_name_lang, language)

    def _append_region_name_language_row(self, language, text):
        return self._append_language_row(self.ui.table_region_name_lang, language, text)

    def add_description_language_row(self, checked=False):
        self._add_language_row(self.ui.table_description_lang)

    def remove_description_language_rows(self):
        self._remove_language_rows(self.ui.table_description_lang)

    def description_language_rows(self):
        return self._language_rows(self.ui.table_description_lang)

    def set_description_languages(self, languages):
        self._set_language_rows(self.ui.table_description_lang, languages)

    def add_transcription_language_row(self, checked=False):
        self._add_language_row(self.ui.table_transcription_lang)

    def remove_transcription_language_rows(self):
        self._remove_language_rows(self.ui.table_transcription_lang)

    def transcription_language_rows(self):
        return self._language_rows(self.ui.table_transcription_lang)

    def set_transcription_languages(self, languages):
        self._set_language_rows(self.ui.table_transcription_lang, languages)

    def insert_description_text(self, text):
        self._insert_language_text(self.ui.table_description_lang, text)

    def insert_transcription_text(self, text):
        self._insert_language_text(self.ui.table_transcription_lang, text)

    def set_speech_recording_target(self, target):
        self.ui.btn_record_description_speech.setChecked(target == "description")
        self.ui.btn_record_transcription_speech.setChecked(target == "transcription")

    def set_speech_buttons_enabled(self, enabled):
        self.ui.btn_record_description_speech.setEnabled(enabled)
        self.ui.btn_record_transcription_speech.setEnabled(enabled)

    def _set_language_rows(self, table, languages):
        table.setRowCount(0)
        for language, text in languages:
            self._append_language_row(table, language, text)

    def _add_language_row(self, table):
        language = "" if self._has_language(table, "x-default") else "x-default"
        row = self._append_language_row(table, language, "")
        table.setCurrentCell(row, 0)
        column = 1 if language else 0
        table.setCurrentCell(row, column)
        table.editItem(table.item(row, column))

    def _remove_language_rows(self, table):
        selected_rows = sorted({index.row() for index in table.selectedIndexes()}, reverse=True)
        if not selected_rows and table.rowCount():
            selected_rows = [table.rowCount() - 1]
        for row in selected_rows:
            table.removeRow(row)

    def _language_rows(self, table):
        rows = []
        for row in range(table.rowCount()):
            language_item = table.item(row, 0)
            text_item = table.item(row, 1)
            language = language_item.text().strip() if language_item else ""
            text = text_item.text().strip() if text_item else ""
            rows.append((language, text))
        return rows

    def _language_default_text(self, table):
        for language, text in self._language_rows(table):
            if language == "x-default":
                return text
        return ""

    def _has_language(self, table, language):
        return any(row_language == language for row_language, _text in self._language_rows(table))

    def _append_language_row(self, table, language, text):
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(str(language or "")))
        table.setItem(row, 1, QTableWidgetItem(str(text or "")))
        return row

    def _insert_language_text(self, table, text):
        text = str(text or "").strip()
        if not text:
            return

        row = table.currentRow()
        if row < 0:
            row = self._language_row(table, "x-default")
        if row < 0:
            row = self._append_language_row(table, "x-default", "")

        language_item = table.item(row, 0)
        if language_item is None or not language_item.text().strip():
            table.setItem(row, 0, QTableWidgetItem("x-default"))

        text_item = table.item(row, 1)
        existing_text = text_item.text().strip() if text_item is not None else ""
        new_text = f"{existing_text} {text}".strip() if existing_text else text
        table.setItem(row, 1, QTableWidgetItem(new_text))
        table.setCurrentCell(row, 1)
        table.editItem(table.item(row, 1))

    def _language_row(self, table, language):
        for row, (row_language, _text) in enumerate(self._language_rows(table)):
            if row_language == language:
                return row
        return -1

    def set_region_type(self, name, identifier):
        self.ui.txt_rctype_name.setPlainText(name)
        self.ui.txt_rctype_indent.setPlainText(identifier)

    def set_contributors(self, contributors):
        self.ui.table_contributors.setRowCount(0)
        for contributor in contributors:
            self._append_contributor_row(
                contributor.get("role", ""),
                contributor.get("identifier", ""),
                contributor.get("name", ""),
            )

    def set_description(self, text):
        self.set_description_languages(language_alternative_items(text))

    def set_transcription(self, text):
        self.set_transcription_languages(language_alternative_items(text))

    def contributor_rows(self):
        rows = []
        for row in range(self.ui.table_contributors.rowCount()):
            name_item = self.ui.table_contributors.item(row, 0)
            identifier_item = self.ui.table_contributors.item(row, 1)
            role_item = self.ui.table_contributors.item(row, 2)
            rows.append(
                {
                    "role": role_item.text().strip() if role_item else "",
                    "identifier": identifier_item.text().strip() if identifier_item else "",
                    "name": name_item.text().strip() if name_item else "",
                }
            )
        return rows

    def contributor_error(self):
        for row, contributor in enumerate(self.contributor_rows(), start=1):
            role = contributor["role"]
            identifier = contributor["identifier"]
            name = contributor["name"]
            if not role and not identifier and not name:
                return f"Contributor row {row} is empty. Fill it or remove the row."
            if not role:
                return f"Contributor row {row} has no role."
            if not identifier and not name:
                return f"Contributor row {row} has no identifier or name."
        return ""

    def add_contributor_row(self, checked=False):
        row = self._append_contributor_row("", "", "")
        self.ui.table_contributors.setCurrentCell(row, 0)
        self.ui.table_contributors.editItem(self.ui.table_contributors.item(row, 0))

    def remove_contributor_rows(self):
        selected_rows = sorted({index.row() for index in self.ui.table_contributors.selectedIndexes()}, reverse=True)
        if not selected_rows and self.ui.table_contributors.rowCount():
            selected_rows = [self.ui.table_contributors.rowCount() - 1]
        for row in selected_rows:
            self.ui.table_contributors.removeRow(row)

    def selected_contributor_role(self):
        row = self._selected_contributor_row()
        if row < 0:
            return ""
        item = self.ui.table_contributors.item(row, 2)
        return item.text().strip() if item else ""

    def set_selected_contributor_role(self, role):
        row = self._selected_contributor_row()
        if row < 0:
            row = self._append_contributor_row("", "", "")
        self.ui.table_contributors.setItem(row, 2, QTableWidgetItem(role))
        self.ui.table_contributors.setCurrentCell(row, 2)

    def apply_contributor_role_term(self, term):
        self.set_selected_contributor_role(term.identifier or term.name)

    def _append_contributor_row(self, role, identifier, name):
        row = self.ui.table_contributors.rowCount()
        self.ui.table_contributors.insertRow(row)
        self.ui.table_contributors.setItem(row, 0, QTableWidgetItem(str(name or "")))
        self.ui.table_contributors.setItem(row, 1, QTableWidgetItem(str(identifier or "")))
        self.ui.table_contributors.setItem(row, 2, QTableWidgetItem(str(role or "")))
        return row

    def _selected_contributor_row(self):
        selected_rows = self.ui.table_contributors.selectionModel().selectedRows()
        if selected_rows:
            return selected_rows[0].row()
        current_row = self.ui.table_contributors.currentRow()
        if current_row >= 0:
            return current_row
        return -1

    def _region_selected(self, object_id):
        try:
            self.objectSelected.emit(int(object_id))
        except (TypeError, ValueError):
            pass

    def _selection_cleared(self):
        self.objectDeselected.emit()

    def _assign_geometry_requested(self, object_id, object_type):
        try:
            self.assignGeometryRequested.emit(int(object_id), object_type)
        except (TypeError, ValueError):
            pass

    def _clear_geometry_requested(self, object_id):
        try:
            self.clearGeometryRequested.emit(int(object_id))
        except (TypeError, ValueError):
            pass

    def _zoom_to_region_requested(self, object_id):
        try:
            self.zoomToRegionRequested.emit(int(object_id))
        except (TypeError, ValueError):
            pass

    def _delete_image_region_requested(self, object_id):
        try:
            self.deleteImageRegionRequested.emit(int(object_id))
        except (TypeError, ValueError):
            pass

    def _restore_original_requested(self, object_id):
        try:
            self.restoreOriginalRequested.emit(int(object_id))
        except (TypeError, ValueError):
            pass

    def _json_metadata_requested(self, object_id):
        try:
            self.jsonMetadataRequested.emit(int(object_id))
        except (TypeError, ValueError):
            pass

    def _merge_regions_requested(self, source_object_id, target_object_id, mode):
        try:
            self.mergeRegionsRequested.emit(int(source_object_id), int(target_object_id), mode)
        except (TypeError, ValueError):
            pass

    def _group_regions_requested(self, object_ids, mode):
        try:
            self.groupRegionsRequested.emit([int(object_id) for object_id in object_ids], mode)
        except (TypeError, ValueError):
            pass

    def _group_regions_into_requested(self, child_object_ids, container_object_id):
        try:
            child_ids = [int(object_id) for object_id in child_object_ids]
            self.groupRegionsIntoRequested.emit(child_ids, int(container_object_id))
        except (TypeError, ValueError):
            pass

    def _object_attributes(self, obj):
        data = obj.get("data")
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return None
        if isinstance(data, dict):
            return data.get("attributes", data)
        return obj.get("attributes")

    def _build_nodes(
        self,
        regions,
        parent_id,
        base_path,
        depth,
        used_object_ids=None,
        root_object_ids=None,
        validation_issues=None,
    ):
        if used_object_ids is None:
            used_object_ids = set()
        validation_issues = validation_issues or {}
        nodes = []
        for index, region in enumerate(regions):
            if not isinstance(region, dict):
                continue
            path = base_path + [index]
            if parent_id is None and root_object_ids is not None and index < len(root_object_ids):
                object_id = self._unique_object_id(root_object_ids[index], used_object_ids)
            else:
                object_id = self._node_object_id(region, path, used_object_ids)
            node = RegionNode(
                object_id=object_id,
                parent_id=parent_id,
                region=region,
                path=path,
                depth=depth,
                graph_pos=self._load_graph_pos(region),
                validation_issues=validation_issues.get(object_id, []),
            )
            child_key, child_regions = find_child_list(region)
            if child_regions is not None:
                node.children = self._build_nodes(
                    child_regions,
                    object_id,
                    node.path + [child_key],
                    depth + 1,
                    used_object_ids,
                    validation_issues=validation_issues,
                )
            nodes.append(node)
        return nodes

    def _add_multigeometry_parts(self):
        used_ids = {node.object_id for node in self._flatten(self.nodes)}
        for node in self._flatten(self.nodes):
            shape = region_shape(node.region)
            part_type = {
                "multipolygon": "polygon",
                "multipoint": "point",
                "multilinestring": "linestring",
            }.get(shape)
            if part_type is None and shape != "polygon":
                continue
            boundary = node.region.get("regionBoundary") or node.region.get("RegionBoundary") or {}
            coordinates = boundary.get("rbCoordinates", boundary.get("RbCoordinates"))
            if isinstance(coordinates, str):
                try:
                    coordinates = json.loads(coordinates)
                except (TypeError, ValueError):
                    continue
            if not isinstance(coordinates, list):
                continue
            if shape == "polygon":
                self._add_polygon_ring_nodes(node, node.object_id, 0, coordinates, used_ids)
                continue
            for index, part in enumerate(coordinates):
                if not isinstance(part, list) or not part:
                    continue
                part_id = self._unique_object_id(f"{node.object_id}:{part_type}:{index}", used_ids)
                part_node = RegionNode(
                    object_id=part_id,
                    parent_id=node.object_id,
                    geometry_owner_id=node.object_id,
                    geometry_part_index=index,
                    region={
                        "name": f"{part_type.capitalize()} {index + 1}",
                        "regionBoundary": {
                            "rbShape": part_type,
                            "rbUnit": boundary.get("rbUnit", boundary.get("RbUnit", "relative")),
                            "rbCoordinates": copy.deepcopy(part),
                        },
                    },
                    path=node.path + ["regionBoundary", "rbCoordinates", index],
                    depth=node.depth + 1,
                )
                node.children.append(part_node)
                if part_type == "polygon":
                    self._add_polygon_ring_nodes(part_node, node.object_id, index, part, used_ids)

    def _add_polygon_ring_nodes(self, parent, owner_id, part_index, rings, used_ids):
        if len(rings) < 2 or not all(isinstance(ring, list) and ring for ring in rings):
            return
        parent.geometry_part_index = part_index
        parent.geometry_ring_index = 0
        for ring_index, ring in enumerate(rings[1:], start=1):
            ring_id = self._unique_object_id(f"{parent.object_id}:ring:{ring_index}", used_ids)
            parent.children.append(
                RegionNode(
                    object_id=ring_id,
                    parent_id=parent.object_id,
                    geometry_owner_id=owner_id,
                    geometry_part_index=part_index,
                    geometry_ring_index=ring_index,
                    region={
                        "name": f"Inner polygon {ring_index}",
                        "regionBoundary": {"rbShape": "polygon", "rbCoordinates": [copy.deepcopy(ring)]},
                    },
                    path=parent.path + [ring_index],
                    depth=parent.depth + 1,
                )
            )

    def _connect_referenced_parents(self):
        all_nodes = self._flatten(self.nodes)
        by_object_id = {node.object_id: node for node in all_nodes}
        parents = parent_object_map([node.region for node in all_nodes], [node.object_id for node in all_nodes])
        child_ids = {child.object_id for node in all_nodes for child in node.children}

        for node in all_nodes:
            if node.parent_id:
                continue
            parent = by_object_id.get(parents.get(node.object_id))
            if parent and parent is not node and node.object_id not in child_ids:
                node.parent_id = parent.object_id
                parent.children.append(node)
                self._remove_from_roots(node)

    def _remove_from_roots(self, target_node):
        self.nodes = [node for node in self.nodes if node is not target_node]

    def _index_nodes(self):
        self.nodes_by_id = {node.object_id: node for node in self._flatten(self.nodes)}

    def _flatten(self, nodes):
        result = []
        for node in nodes:
            result.append(node)
            result.extend(self._flatten(node.children))
        return result

    def _read_parent_reference(self, region):
        for key in PARENT_KEYS:
            value = region.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                text = first_text(value)
                if text:
                    return text
        return None

    def _read_region_identifier(self, region):
        return first_text(region.get("rId") or region.get("RId"), "")

    def _node_object_id(self, region, path, used_object_ids):
        raw_object_id = region.get("object_id")
        if raw_object_id is None or raw_object_id == "":
            raw_object_id = region.get("id")
        if raw_object_id is None or raw_object_id == "":
            raw_object_id = ".".join(str(part) for part in path)
        return self._unique_object_id(str(raw_object_id), used_object_ids)

    def _unique_object_id(self, base_id, used_object_ids):
        candidate = str(base_id)
        counter = 2
        while candidate in used_object_ids:
            candidate = f"{base_id}-{counter}"
            counter += 1
        used_object_ids.add(candidate)
        return candidate

    def _nodes_by_region_identifier(self, nodes):
        by_region_identifier = {}
        duplicates = set()
        for node in nodes:
            region_identifier = node.RegionID
            if not region_identifier:
                continue
            if region_identifier in by_region_identifier:
                duplicates.add(region_identifier)
                continue
            by_region_identifier[region_identifier] = node
        for region_identifier in duplicates:
            by_region_identifier.pop(region_identifier, None)
        return by_region_identifier, duplicates

    def _load_graph_pos(self, region):
        return None
