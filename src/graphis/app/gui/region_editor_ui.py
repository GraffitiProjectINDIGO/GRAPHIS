# Copyright (C) 2026 Martin Wieser

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTabWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from graphis.app.gui.resources import icon as resource_icon
from graphis.app.gui.resources import icon_url
from graphis.app.imgregion.region_graph_view import RegionGraphView

BACKGROUND = "rgb(40, 44, 52)"
TEXT = "rgb(210, 210, 210)"

ROOT_STYLE = f"""
QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT};
}}
"""

TAB_STYLE = """
QTabWidget {
    background-color: rgb(40, 44, 52);
}
QTabWidget::pane {
    border: 0px solid rgb(0, 0, 0);
}
QTabBar::tab {
    background: rgb(70, 50, 72);
    border: 2px solid #C4C4C3;
    border-bottom-color: #C2C7CB;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    min-width: 8ex;
    padding: 3px;
}
QTabBar::tab:selected {
    border-color: #C2C7CB;
    border-bottom-color: #C2C7CB;
}
QTabBar::tab:!selected {
    margin-top: 5px;
}
"""

BUTTON_STYLE = """
QPushButton {
    border: 2px solid rgb(52, 59, 72);
    border-radius: 5px;
    background-color: rgb(52, 59, 72);
}
QPushButton:hover {
    background-color: rgb(57, 65, 80);
    border: 2px solid rgb(61, 70, 86);
}
QPushButton:pressed {
    background-color: rgb(35, 40, 49);
    border: 2px solid rgb(43, 50, 61);
}
QPushButton:checked {
    background-color: rgb(117, 49, 49);
    border: 2px solid rgb(161, 72, 72);
}
"""


def tree_style():
    closed_icon = icon_url("cil-size-grip.png")
    open_icon = icon_url("circle.svg")
    return (
        """
QTreeView {
    alternate-background-color: #222222;
    background: transparent;
}
QTreeView::branch:has-children:!has-siblings:closed,
QTreeView::branch:closed:has-children:has-siblings {
    border-image: none;
    image: url("""
        + closed_icon
        + """);
}
QTreeView::branch:open:has-children:!has-siblings,
QTreeView::branch:open:has-children:has-siblings {
    border-image: none;
    image: url("""
        + open_icon
        + """);
}
"""
    )


class RegionEditorUi:
    def setup(self, region_editor):
        if not region_editor.objectName():
            region_editor.setObjectName("region_editor")
        region_editor.resize(690, 700)
        region_editor.setMinimumSize(QSize(0, 420))
        region_editor.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        region_editor.setWindowTitle("Form")
        region_editor.setStyleSheet(ROOT_STYLE)

        self._font_normal = self._font(10)
        self._font_label = self._font(11, bold=True)
        self._font_group = self._font(10, bold=True)
        self._font_tabs = self._font(9, bold=True)

        self.horizontalLayout = QHBoxLayout(region_editor)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(0)

        self.graph_panel = QWidget(region_editor)
        graph_layout = QVBoxLayout(self.graph_panel)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_layout.setSpacing(0)
        self.selection_guidance = QLabel(self.graph_panel)
        self.selection_guidance.setObjectName("selectionGuidance")
        self.selection_guidance.setTextFormat(Qt.TextFormat.PlainText)
        self.selection_guidance.setWordWrap(True)
        self.selection_guidance.setContentsMargins(8, 6, 8, 6)
        self.selection_guidance.hide()
        graph_layout.addWidget(self.selection_guidance)

        self.graphicsView = RegionGraphView(self.graph_panel)
        self.graphicsView.setObjectName("graphicsView")
        self.graphicsView.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.graphicsView.setStyleSheet(f"background-color: {BACKGROUND};")
        graph_layout.addWidget(self.graphicsView, 1)
        self.horizontalLayout.addWidget(self.graph_panel, 1)

        self.region_widget = QTabWidget(region_editor)
        self.region_widget.setObjectName("region_widget")
        self.region_widget.setMaximumWidth(350)
        self.region_widget.setFont(self._font_tabs)
        self.region_widget.setStyleSheet(TAB_STYLE)
        self.horizontalLayout.addWidget(self.region_widget)

        self._build_change_region_tab()
        self._build_current_region_tab()
        self._build_all_regions_tab()
        self.region_widget.setCurrentIndex(0)

    def _build_change_region_tab(self):
        self.tab = QWidget()
        self.tab.setObjectName("tab")
        layout = QVBoxLayout(self.tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.btn_object_save = QPushButton(self.tab)
        self.btn_object_save.setObjectName("btn_object_save")
        self.btn_object_save.setFixedSize(30, 30)
        self.btn_object_save.setFont(self._font_group)
        self.btn_object_save.setStyleSheet(BUTTON_STYLE)
        self.btn_object_save.setIcon(resource_icon("save.svg"))
        self.btn_object_save.setIconSize(QSize(30, 30))
        layout.addWidget(self.btn_object_save)

        form_frame = QFrame(self.tab)
        form_frame.setObjectName("regionFormFrame")
        form_frame.setStyleSheet("background-color: rgb(0, 74, 117);")
        form_frame.setFrameShape(QFrame.Shape.StyledPanel)
        form_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(9, 3, 9, 3)
        form_layout.setSpacing(6)

        self.txt_rid = self._plain_text("txt_rid", "rgb(52, 70, 72)")
        form_layout.addWidget(self._region_group())

        self.txt_rrole_ident = self._plain_text("txt_rrole_ident", "rgb(52, 70, 72)", read_only=True)
        self.txt_rrole_name = self._plain_text("txt_rrole_name", "rgb(52, 70, 72)", read_only=True)
        form_layout.addWidget(
            self._form_group(
                "groupBox_11",
                "Region Role",
                (
                    ("Identifier", self._field_with_button(self.txt_rrole_ident, "btn_select_region_role_vocab")),
                    ("Name", self.txt_rrole_name),
                ),
            )
        )

        self.txt_rctype_indent = self._plain_text("txt_rctype_indent", "rgb(52, 70, 72)", read_only=True)
        self.txt_rctype_name = self._plain_text("txt_rctype_name", "rgb(52, 70, 72)", read_only=True)
        form_layout.addWidget(
            self._form_group(
                "groupBox_10",
                "Region Content Type",
                (
                    ("Identifier", self._field_with_button(self.txt_rctype_indent, "btn_select_region_type_vocab")),
                    ("Name", self.txt_rctype_name),
                ),
            )
        )

        layout.addWidget(form_frame)

        self.tabWidget_3 = QTabWidget(self.tab)
        self.tabWidget_3.setObjectName("tabWidget_3")
        self.tabWidget_3.setFont(self._font_tabs)
        self.tabWidget_3.setStyleSheet(TAB_STYLE)
        self._build_creator_tab()
        self._build_description_tab()
        self._build_transcription_tab()
        self.tabWidget_3.setCurrentIndex(1)
        layout.addWidget(self.tabWidget_3, 1)

        self.region_widget.addTab(self.tab, "Change region info")

    def _build_creator_tab(self):
        self.tab_7 = QWidget()
        layout = QVBoxLayout(self.tab_7)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.table_contributors = QTableWidget(0, 3, self.tab_7)
        self.table_contributors.setObjectName("table_contributors")
        self.table_contributors.setHorizontalHeaderLabels(("Name", "Identifier", "Role"))
        self.table_contributors.setFont(self._font_normal)
        self.table_contributors.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_contributors.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_contributors.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        self.table_contributors.setStyleSheet(self._metadata_table_style())
        self.table_contributors.verticalHeader().setVisible(False)
        header = self.table_contributors.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table_contributors, 1)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        self.btn_add_contributor = self._symbol_button("btn_add_contributor", "+", "Add contributor")
        self.btn_remove_contributor = self._symbol_button("btn_remove_contributor", "-", "Remove contributor")
        self.btn_select_contributor_role_vocab = self._symbol_button(
            "btn_select_contributor_role_vocab", "...", "Select contributor role"
        )
        button_layout.addWidget(self.btn_add_contributor)
        button_layout.addWidget(self.btn_remove_contributor)
        button_layout.addWidget(self.btn_select_contributor_role_vocab)
        layout.addLayout(button_layout)
        self.tabWidget_3.addTab(self.tab_7, "Contributor")

    def _build_description_tab(self):
        self.tab_6 = QWidget()
        layout = QVBoxLayout(self.tab_6)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.groupBox_8 = QGroupBox("XMP-DC Description", self.tab_6)
        self.groupBox_8.setObjectName("groupBox_8")
        self.groupBox_8.setFont(self._font_group)
        description_layout = QVBoxLayout(self.groupBox_8)
        self.table_description_lang = self._metadata_language_table("table_description_lang")
        description_layout.addWidget(self.table_description_lang, 1)
        description_buttons = self._language_button_row(
            "btn_add_description_lang",
            "btn_remove_description_lang",
            "Add description language",
            "Remove description language",
            speech_object_name="btn_record_description_speech",
            speech_tooltip="Record description from microphone",
        )
        (
            self.btn_add_description_lang,
            self.btn_remove_description_lang,
            self.btn_record_description_speech,
            description_button_layout,
        ) = description_buttons
        description_layout.addLayout(description_button_layout)
        layout.addWidget(self.groupBox_8, 1)
        self.tabWidget_3.addTab(self.tab_6, "Description")

    def _build_transcription_tab(self):
        self.tab_9 = QWidget()
        layout = QVBoxLayout(self.tab_9)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.groupBox_7 = QGroupBox("XMP-DC Title", self.tab_9)
        self.groupBox_7.setObjectName("groupBox_7")
        self.groupBox_7.setFont(self._font_group)
        transcription_layout = QVBoxLayout(self.groupBox_7)
        self.table_transcription_lang = self._metadata_language_table("table_transcription_lang")
        transcription_layout.addWidget(self.table_transcription_lang, 1)
        transcription_buttons = self._language_button_row(
            "btn_add_transcription_lang",
            "btn_remove_transcription_lang",
            "Add title language",
            "Remove title language",
            speech_object_name="btn_record_transcription_speech",
            speech_tooltip="Record transcription from microphone",
        )
        (
            self.btn_add_transcription_lang,
            self.btn_remove_transcription_lang,
            self.btn_record_transcription_speech,
            transcription_button_layout,
        ) = transcription_buttons
        transcription_layout.addLayout(transcription_button_layout)
        layout.addWidget(self.groupBox_7, 1)
        self.tabWidget_3.addTab(self.tab_9, "Transcription")

    def _region_group(self):
        group = QGroupBox("Region")
        group.setObjectName("groupBox_5")
        group.setFont(self._font_group)
        layout = QFormLayout(group)
        layout.setVerticalSpacing(10)
        layout.setContentsMargins(9, 9, 9, 3)

        label = QLabel("Region Identifier", group)
        label.setFont(self._font_label)
        layout.addRow(label, self.txt_rid)

        self.table_region_name_lang = QTableWidget(0, 2, group)
        self.table_region_name_lang.setObjectName("table_region_name_lang")
        self.table_region_name_lang.setHorizontalHeaderLabels(("Language", "Text"))
        self.table_region_name_lang.setToolTip(
            "Use x-default as the fallback region name."
            "Other rows are localized names with language tags such as de, en, or fr."
        )
        self.table_region_name_lang.setFont(self._font_normal)
        self.table_region_name_lang.setMaximumHeight(130)
        self.table_region_name_lang.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_region_name_lang.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_region_name_lang.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        self.table_region_name_lang.setStyleSheet(
            """
            QTableWidget {
                background-color: rgb(52, 90, 72);
                gridline-color: rgb(40, 44, 52);
            }
            QHeaderView::section {
                background-color: rgb(52, 70, 72);
                color: rgb(210, 210, 210);
                border: 0px;
                padding: 2px;
            }
            """
        )
        header = self.table_region_name_lang.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_region_name_lang.verticalHeader().setVisible(False)

        lang_layout = QVBoxLayout()
        lang_layout.setContentsMargins(0, 0, 0, 0)
        lang_layout.setSpacing(4)
        lang_layout.addWidget(self.table_region_name_lang)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addStretch(1)
        self.btn_add_region_name_lang = self._symbol_button("btn_add_region_name_lang", "+", "Add language")
        self.btn_remove_region_name_lang = self._symbol_button("btn_remove_region_name_lang", "-", "Remove language")
        button_layout.addWidget(self.btn_add_region_name_lang)
        button_layout.addWidget(self.btn_remove_region_name_lang)
        lang_layout.addLayout(button_layout)

        label = QLabel("Region\nName", group)
        label.setFont(self._font_label)
        layout.addRow(label, lang_layout)
        return group

    def _build_current_region_tab(self):
        self.tab_2 = QWidget()
        layout = QVBoxLayout(self.tab_2)
        layout.setContentsMargins(9, 9, 9, 9)
        layout.setSpacing(6)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        self.btn_expand_all = self._small_button("btn_expand_all", "Expand all")
        self.btn_collapse_all = self._small_button("btn_collapse_all", "Collapse all")
        button_layout.addWidget(self.btn_expand_all)
        button_layout.addWidget(self.btn_collapse_all)
        layout.addLayout(button_layout)

        self.image_region_view = self._tree_view("image_region_view")
        layout.addWidget(self.image_region_view, 1)
        self.region_widget.addTab(self.tab_2, "View region info")

    def _build_all_regions_tab(self):
        self.tab_8 = QWidget()
        layout = QVBoxLayout(self.tab_8)
        layout.setContentsMargins(9, 9, 9, 9)
        layout.setSpacing(6)

        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        self.btn_expand_all_all_region = self._small_button("btn_expand_all_all_region", "Expand all")
        self.btn_collapse_all_all_region = self._small_button("btn_collapse_all_all_region", "Collapse all")
        button_layout.addWidget(self.btn_expand_all_all_region)
        button_layout.addWidget(self.btn_collapse_all_all_region)
        layout.addLayout(button_layout)

        self.image_all_region = self._tree_view("image_all_region")
        self.image_all_region.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        self.image_all_region.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        layout.addWidget(self.image_all_region, 1)
        self.region_widget.addTab(self.tab_8, "All region info")

    def _form_group(self, object_name, title, rows):
        group = QGroupBox(title)
        group.setObjectName(object_name)
        group.setFont(self._font_group)
        layout = QFormLayout(group)
        layout.setVerticalSpacing(10)
        layout.setContentsMargins(9, 9, 9, 3)
        for label_text, widget in rows:
            label = QLabel(label_text, group)
            label.setFont(self._font_label)
            layout.addRow(label, widget)
        return group

    def _form_frame(self, object_name, rows):
        frame = QFrame()
        frame.setObjectName(object_name)
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setFrameShadow(QFrame.Shadow.Raised)
        layout = QFormLayout(frame)
        layout.setContentsMargins(9, 0, 9, 0)
        for label_text, widget in rows:
            label = QLabel(label_text, frame)
            label.setFont(self._font_label)
            layout.addRow(label, widget)
        return frame

    def _metadata_language_table(self, object_name):
        table = QTableWidget(0, 2)
        table.setObjectName(object_name)
        table.setHorizontalHeaderLabels(("Language", "Text"))
        table.setFont(self._font_normal)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        table.setStyleSheet(self._metadata_table_style())
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        return table

    def _language_button_row(
        self,
        add_object_name,
        remove_object_name,
        add_tooltip,
        remove_tooltip,
        speech_object_name=None,
        speech_tooltip=None,
    ):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)
        add_button = self._symbol_button(add_object_name, "+", add_tooltip)
        remove_button = self._symbol_button(remove_object_name, "-", remove_tooltip)
        speech_button = None
        if speech_object_name is not None:
            speech_button = self._symbol_button(speech_object_name, "", speech_tooltip or "Record from microphone")
            speech_button.setIcon(resource_icon("microphone.svg"))
            speech_button.setIconSize(QSize(18, 18))
            speech_button.setCheckable(True)
            layout.addWidget(speech_button)
        layout.addWidget(add_button)
        layout.addWidget(remove_button)
        return add_button, remove_button, speech_button, layout

    def _metadata_table_style(self):
        return """
            QTableWidget {
                background-color: rgb(52, 90, 72);
                gridline-color: rgb(40, 44, 52);
            }
            QHeaderView::section {
                background-color: rgb(52, 70, 72);
                color: rgb(210, 210, 210);
                border: 0px;
                padding: 2px;
            }
        """

    def _plain_text(self, object_name, background, read_only=False):
        widget = QPlainTextEdit()
        widget.setObjectName(object_name)
        widget.setFont(self._font_normal)
        widget.setMaximumHeight(40)
        widget.setStyleSheet(f"background-color: {background};")
        widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        widget.setReadOnly(read_only)
        return widget

    def _tree_view(self, object_name):
        view = QTreeView()
        view.setObjectName(object_name)
        view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        view.setStyleSheet(tree_style())
        view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        view.setAlternatingRowColors(True)
        view.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        view.setIndentation(40)
        view.header().setVisible(False)
        view.header().setCascadingSectionResizes(False)
        view.header().setMinimumSectionSize(220)
        view.header().setDefaultSectionSize(220)
        view.header().setStretchLastSection(False)
        return view

    def _field_with_button(self, field, button_object_name):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(field, 1)
        button = self._symbol_button(button_object_name, "...", "Select controlled vocabulary term")
        setattr(self, button_object_name, button)
        layout.addWidget(button)
        return container

    def _small_button(self, object_name, text):
        button = QPushButton(text)
        button.setObjectName(object_name)
        button.setMaximumWidth(100)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        button.setStyleSheet(BUTTON_STYLE)
        return button

    def _symbol_button(self, object_name, text, tooltip):
        button = QPushButton(text)
        button.setObjectName(object_name)
        button.setFixedSize(24, 24)
        button.setFont(self._font(13, bold=True))
        button.setToolTip(tooltip)
        button.setStyleSheet(BUTTON_STYLE)
        return button

    @staticmethod
    def _font(point_size, bold=False):
        font = QFont()
        font.setPointSize(point_size)
        font.setBold(bold)
        return font
