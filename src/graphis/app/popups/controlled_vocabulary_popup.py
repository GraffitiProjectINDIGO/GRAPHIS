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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from graphis.app.controlled_vocabulary import (
    SOURCE_CUSTOM,
    SOURCE_GRAPHIS,
    SOURCE_IMAGE_METADATA,
    SOURCE_IPTC_ROLE,
    SOURCE_IPTC_TYPE,
    SUPPORTED_TARGETS,
    TARGET_LABELS,
    TARGET_REGION_ROLE,
    TARGET_REGION_TYPE,
    VocabularyTerm,
)
from graphis.app.popups import message_box


class ControlledVocabularyPopup(QDialog):
    def __init__(self, parent, store, target: str, current_name: str = "", current_identifier: str = ""):
        super().__init__(parent)
        self.store = store
        self.initial_target = target
        self.selected_term = None

        self.setWindowTitle("Select controlled vocabulary term")
        self.resize(920, 650)
        self.setStyleSheet("""
            QDialog {
                background-color: rgb(40, 44, 52);
                color: rgb(210, 210, 210);
            }
            QLabel,
            QGroupBox {
                color: rgb(220, 220, 220);
                font: 10pt "Segoe UI";
            }
            QComboBox,
            QLineEdit,
            QTableWidget {
                background-color: rgb(52, 70, 72);
                color: rgb(230, 230, 230);
                border: 1px solid rgb(95, 112, 116);
                border-radius: 3px;
                padding: 4px;
                font: 10pt "Segoe UI";
            }
            QTableWidget {
                gridline-color: rgb(40, 44, 52);
                selection-background-color: rgb(34, 113, 150);
                selection-color: rgb(255, 255, 255);
                alternate-background-color: rgb(46, 62, 64);
            }
            QTableWidget::item {
                border: 0px;
                padding: 3px;
            }
            QTableWidget::item:hover {
                background-color: rgb(64, 86, 92);
                color: rgb(255, 255, 255);
            }
            QTableWidget::item:selected {
                background-color: rgb(34, 113, 150);
                color: rgb(255, 255, 255);
            }
            QHeaderView::section {
                background-color: rgb(52, 59, 72);
                color: rgb(230, 230, 230);
                border: 0px;
                padding: 4px;
            }
            QPushButton {
                background-color: rgb(52, 59, 72);
                border: 1px solid rgb(70, 78, 92);
                border-radius: 4px;
                padding: 5px 10px;
                color: rgb(230, 230, 230);
                font: 9pt "Segoe UI";
            }
            QPushButton:hover {
                background-color: rgb(65, 74, 90);
            }
            QPushButton:pressed {
                background-color: rgb(35, 40, 49);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        filters = QGridLayout()
        filters.setColumnStretch(1, 1)
        self.target_combo = QComboBox(self)
        for target_value in SUPPORTED_TARGETS:
            self.target_combo.addItem(TARGET_LABELS[target_value], target_value)
        target_index = self.target_combo.findData(target)
        if target_index >= 0:
            self.target_combo.setCurrentIndex(target_index)
        self.source_combo = QComboBox(self)
        self._populate_source_combo()
        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Search name, URI, QCode, or definition")
        filters.addWidget(QLabel("Target", self), 0, 0)
        filters.addWidget(self.target_combo, 0, 1)
        filters.addWidget(QLabel("Source", self), 1, 0)
        filters.addWidget(self.source_combo, 1, 1)
        filters.addWidget(QLabel("Search", self), 2, 0)
        filters.addWidget(self.search_edit, 2, 1)
        layout.addLayout(filters)

        self.table = QTableWidget(0, 6, self)
        self.table.setHorizontalHeaderLabels(("Name", "Source", "Identifier URI", "QCode", "Definition", "Order"))
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnHidden(5, True)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        layout.addWidget(self.table, 1)

        custom_group = QGroupBox("Add or edit custom term", self)
        custom_layout = QGridLayout(custom_group)
        self.custom_name_edit = QLineEdit(self)
        self.custom_identifier_edit = QLineEdit(self)
        self.custom_qcode_edit = QLineEdit(self)
        self.custom_definition_edit = QLineEdit(self)
        self.custom_identifier_edit.setPlaceholderText("https://example.org/vocab/term")
        self.custom_definition_edit.setPlaceholderText("Short explanation or definition")
        custom_layout.addWidget(QLabel("Name", self), 0, 0)
        custom_layout.addWidget(self.custom_name_edit, 0, 1)
        custom_layout.addWidget(QLabel("Identifier URI", self), 1, 0)
        custom_layout.addWidget(self.custom_identifier_edit, 1, 1)
        custom_layout.addWidget(QLabel("QCode", self), 2, 0)
        custom_layout.addWidget(self.custom_qcode_edit, 2, 1)
        custom_layout.addWidget(QLabel("Explanation", self), 3, 0)
        custom_layout.addWidget(self.custom_definition_edit, 3, 1)

        custom_buttons = QHBoxLayout()
        custom_buttons.addStretch(1)
        self.add_custom_button = QPushButton("Add / update", self)
        self.clear_custom_button = QPushButton("Clear fields", self)
        custom_buttons.addWidget(self.add_custom_button)
        custom_buttons.addWidget(self.clear_custom_button)
        custom_layout.addLayout(custom_buttons, 4, 0, 1, 2)
        layout.addWidget(custom_group)

        self.status_label = QLabel("", self)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        footer_layout = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh IPTC", self)
        self.export_codes_button = QPushButton("Save codes", self)
        self.import_codes_button = QPushButton("Load codes", self)
        self.restore_codes_button = QPushButton("Restore", self)
        footer_layout.addWidget(self.refresh_button)
        footer_layout.addWidget(self.export_codes_button)
        footer_layout.addWidget(self.import_codes_button)
        footer_layout.addWidget(self.restore_codes_button)
        footer_layout.addStretch(1)

        buttons = QDialogButtonBox(self)
        self.use_button = buttons.addButton("Use selected", QDialogButtonBox.ButtonRole.AcceptRole)
        buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        footer_layout.addWidget(buttons)
        layout.addLayout(footer_layout)

        self.target_combo.currentIndexChanged.connect(self._target_changed)
        self.source_combo.currentIndexChanged.connect(self._reload_terms)
        self.search_edit.textChanged.connect(self._reload_terms)
        self.refresh_button.clicked.connect(self._refresh_iptc_terms)
        self.table.itemDoubleClicked.connect(lambda _item: self._accept_selected())
        self.table.customContextMenuRequested.connect(self._show_table_context_menu)
        self.add_custom_button.clicked.connect(self._add_custom_term_from_fields)
        self.clear_custom_button.clicked.connect(self._clear_custom_fields)
        self.export_codes_button.clicked.connect(self._export_codes)
        self.import_codes_button.clicked.connect(self._import_codes)
        self.restore_codes_button.clicked.connect(self._restore_codes)
        self.use_button.clicked.connect(self._accept_selected)
        buttons.rejected.connect(self.reject)

        self.refresh_button.setEnabled(self._target() in {TARGET_REGION_ROLE, TARGET_REGION_TYPE})
        self._ensure_current_custom_draft(current_name, current_identifier)
        self._reload_terms()
        self._select_current(current_name, current_identifier)

    def _target(self) -> str:
        return self.target_combo.currentData()

    def _source_options(self, target: str) -> list[str]:
        sources = ["All sources", SOURCE_GRAPHIS]
        if target == TARGET_REGION_ROLE:
            sources.append(SOURCE_IPTC_ROLE)
        elif target == TARGET_REGION_TYPE:
            sources.append(SOURCE_IPTC_TYPE)
        sources.extend((SOURCE_IMAGE_METADATA, SOURCE_CUSTOM))
        return sources

    def _populate_source_combo(self, preferred_source: str = ""):
        selected_source = preferred_source or self.source_combo.currentText()
        self.source_combo.blockSignals(True)
        self.source_combo.clear()
        for source in self._source_options(self._target()):
            self.source_combo.addItem(source)
        index = self.source_combo.findText(selected_source)
        if index >= 0:
            self.source_combo.setCurrentIndex(index)
        self.source_combo.blockSignals(False)

    def _target_changed(self):
        self._populate_source_combo()
        self.refresh_button.setEnabled(self._target() in {TARGET_REGION_ROLE, TARGET_REGION_TYPE})
        self._reload_terms()

    def _reload_terms(self):
        self.table.setSortingEnabled(False)
        selected_source = self.source_combo.currentText()
        search_text = self.search_edit.text()
        terms = self.store.terms(self._target())
        if selected_source != "All sources":
            terms = [term for term in terms if term.source == selected_source]
        terms = [term for term in terms if term.matches(search_text)]

        self.table.setRowCount(0)
        for order, term in enumerate(terms):
            self._append_row(term, order)
        self.table.setSortingEnabled(True)
        self.table.sortItems(5, Qt.SortOrder.AscendingOrder)
        self.status_label.setText(f"{len(terms)} term(s)")

    def _append_row(self, term: VocabularyTerm, order: int):
        row = self.table.rowCount()
        self.table.insertRow(row)
        values = (term.name, term.source, term.identifier, term.qcode, term.definition, f"{order:08d}")
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setData(Qt.ItemDataRole.UserRole, term)
            self.table.setItem(row, column, item)

    def _selected_table_term(self) -> VocabularyTerm | None:
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        item = self.table.item(selected_rows[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _accept_selected(self):
        term = self._selected_table_term()
        if term is None:
            self.status_label.setText("Select a term first.")
            return
        if term.target != self.initial_target:
            self.status_label.setText(
                f"Selected target {TARGET_LABELS.get(term.target, term.target)} cannot be used for "
                f"{TARGET_LABELS.get(self.initial_target, self.initial_target)}."
            )
            return
        self.selected_term = term
        self.accept()

    def _refresh_iptc_terms(self):
        result = self.store.refresh_iptc_terms(self._target())
        self._reload_terms()
        if result.refreshed:
            self.status_label.setText(f"Loaded {len(result.terms)} IPTC term(s).")
        else:
            self.status_label.setText(f"{result.message} Showing {len(result.terms)} term(s).")

    def _select_current(self, current_name: str, current_identifier: str):
        current_identifier = current_identifier.strip()
        current_name = current_name.strip()
        for row in range(self.table.rowCount()):
            term = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if current_identifier and term.identifier.rstrip("/") == current_identifier.rstrip("/"):
                self.table.selectRow(row)
                return
            if current_name and term.name == current_name:
                self.table.selectRow(row)
                return
        if self.table.rowCount():
            self.table.selectRow(0)

    def _show_table_context_menu(self, position):
        row = self.table.indexAt(position).row()
        if row < 0:
            return
        self.table.selectRow(row)
        term = self._selected_table_term()
        if term is None:
            return

        menu = QMenu(self)
        edit_action = menu.addAction("Edit as custom term")
        remove_action = menu.addAction("Remove term")
        action = menu.exec(self.table.viewport().mapToGlobal(position))
        if action == edit_action:
            self._load_term_to_custom_fields(term)
        elif action == remove_action:
            self.store.remove_term(term)
            self._reload_terms()
            self.status_label.setText(f"Removed: {term.name}")

    def _add_custom_term_from_fields(self):
        term = self._custom_term_from_fields()
        if term is None:
            return
        term = self.store.add_custom_term(term)
        self._clear_custom_fields()
        self._reload_terms()
        self._select_current(term.name, term.identifier)
        self.status_label.setText(f"Added custom term: {term.name}")

    def _custom_term_from_fields(self) -> VocabularyTerm | None:
        name = self.custom_name_edit.text().strip()
        identifier = self.custom_identifier_edit.text().strip()
        qcode = self.custom_qcode_edit.text().strip()
        definition = self.custom_definition_edit.text().strip()
        if not name or not identifier:
            self.status_label.setText("Custom term needs both name and identifier.")
            return None
        return VocabularyTerm(self._target(), SOURCE_CUSTOM, name, identifier, qcode, definition)

    def _load_term_to_custom_fields(self, term: VocabularyTerm):
        target_index = self.target_combo.findData(term.target)
        if target_index >= 0 and target_index != self.target_combo.currentIndex():
            self.target_combo.setCurrentIndex(target_index)
        self.custom_name_edit.setText(term.name)
        self.custom_identifier_edit.setText(term.identifier)
        self.custom_qcode_edit.setText(term.qcode)
        self.custom_definition_edit.setText(term.definition)
        self.custom_name_edit.setFocus()

    def _clear_custom_fields(self):
        self.custom_name_edit.clear()
        self.custom_identifier_edit.clear()
        self.custom_qcode_edit.clear()
        self.custom_definition_edit.clear()

    def _ensure_current_custom_draft(self, current_name: str, current_identifier: str):
        current_identifier = current_identifier.strip()
        current_name = current_name.strip()
        if not current_name and not current_identifier:
            return
        existing = self.store.find(self._target(), current_name, current_identifier)
        if existing is not None and existing.source != SOURCE_IMAGE_METADATA:
            return
        self.custom_name_edit.setText(current_name)
        self.custom_identifier_edit.setText(current_identifier)

    def _export_codes(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save controlled vocabulary codes", "", "JSON files (*.json)")
        if not path:
            return
        count = self.store.export_user_terms(path)
        self.status_label.setText(f"Saved {count} code(s).")

    def _import_codes(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load controlled vocabulary codes", "", "JSON files (*.json)")
        if not path:
            return
        count = self.store.import_custom_terms(path)
        self._reload_terms()
        self.status_label.setText(f"Loaded {count} custom code(s).")

    def _restore_codes(self):
        answer = message_box.warning(
            self,
            "Restore controlled vocabulary codes",
            "Remove custom codes, image-derived codes, and removed-term choices for both region roles and content types?",
            message_box.StandardButton.Yes | message_box.StandardButton.No,
            message_box.StandardButton.No,
        )
        if answer != message_box.StandardButton.Yes:
            return
        self.store.clear_user_terms()
        self._clear_custom_fields()
        self._reload_terms()
        self.status_label.setText("Restored default GRAPHIS/IPTC terms.")
