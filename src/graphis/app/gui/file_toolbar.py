# Copyright (C) 2026 Martin Wieser

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QFrame, QSizePolicy, QToolBar, QWidget

from graphis.app.gui.resources import icon as resource_icon


class FileToolBar(QToolBar):
    def __init__(self, main_window):
        super().__init__("File", main_window)
        self.main_window = main_window

        self.setObjectName("fileToolbar")
        self.setMovable(False)
        self.setFloatable(False)
        self.setAllowedAreas(Qt.ToolBarArea.TopToolBarArea)
        self.setIconSize(QSize(26, 26))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setStyleSheet("""
            QToolBar {
                background: rgb(85, 85, 85);
                spacing:4px;
                padding: 6px;
                border: none;
            }
            QToolButton {
                background: rgb(150, 150, 150);
                border: 1px solid rgb(70, 78, 92);
                border-radius: 4px;
                padding: 4px;
            }
            QToolButton:hover,
            QToolButton:checked {
                background: rgb(65, 74, 90);
            }
            QToolButton:pressed {
                background: rgb(90, 110, 135);
            }
            QToolBar::separator {
                background: rgb(70, 78, 92);
                width: 1px;
                margin: 5px;
            }
        """)

        self._build_actions()
        self.layout().setSpacing(4)

    def _add_expanding_spacer(self):
        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return self.addWidget(spacer)

    def _build_actions(self):
        self.centering_spacer_left_action = self._add_expanding_spacer()

        self.action_load_database = self.addAction(
            resource_icon("open-database.svg"),
            "Load database",
            self.main_window.load_existing_db,
        )
        self.action_create_database = self.addAction(
            resource_icon("create-database.svg"),
            "Create new database",
            self.main_window.create_new_db,
        )
        self.action_close_database = self.addAction(
            resource_icon("close-database.svg"),
            "Close database",
            self.main_window.close_database,
        )
        self.addSeparator()

        self.action_undo = self.addAction(
            resource_icon("undo.svg"),
            "Undo",
            self.main_window.undo,
        )
        self.action_undo.setShortcut(QKeySequence("Ctrl+Z"))

        self.action_redo = self.addAction(
            resource_icon("redo.svg"),
            "Redo",
            self.main_window.redo,
        )
        self.action_redo.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        self.addSeparator()

        self.action_add_single_image = self.addAction(
            resource_icon("add-image.svg"),
            "Add single image",
            lambda: self.main_window.load_input_image_folder(single_image=True),
        )
        self.action_add_image_folder = self.addAction(
            resource_icon("add-image-folder.svg"),
            "Add images of folder",
            lambda: self.main_window.load_input_image_folder(),
        )
        self.action_add_image_folder_subfolders = self.addAction(
            resource_icon("add-image-folder-recursive.svg"),
            "Add images of folder/subfolders",
            lambda: self.main_window.load_input_image_folder(subfolder=True),
        )
        self.action_import_csv = self.addAction(
            resource_icon("import-csv.svg"),
            "Import bounding boxes from CSV file",
            self.main_window.import_csv,
        )
        self.addSeparator()

        self.action_save_csv = self.addAction(
            resource_icon("save-csv.svg"),
            "Save bounding boxes to CSV file",
            self.main_window.save_csv,
        )
        self.action_save_regions = self.addAction(
            resource_icon("save-image-regions.svg"),
            "Save image regions to files",
            lambda: self.main_window.save_image_regions(keep_orig=False),
        )
        self.action_save_regions_keep_originals = self.addAction(
            resource_icon("save-image-regions-keep-originals.svg"),
            "Save image regions to files (keep original images)",
            lambda: self.main_window.save_image_regions(keep_orig=True),
        )
        self.addSeparator()

        self.action_regions_to_relative = self.addAction(
            resource_icon("coordinates-relative.svg"),
            "Convert all image-region coordinates to relative units",
            lambda: self.main_window.convert_image_region_coordinates("relative"),
        )
        self.action_regions_to_pixel = self.addAction(
            resource_icon("coordinates-pixel.svg"),
            "Convert all image-region coordinates to absolute pixel units",
            lambda: self.main_window.convert_image_region_coordinates("pixel"),
        )
        self.addSeparator()

        self.action_database_statistics = self.addAction(
            resource_icon("database-statistics.svg"),
            "Show database statistics",
            self.main_window.show_database_statistics_popup,
        )
        self.action_database_statistics.setCheckable(True)

        custom_separator = QFrame()
        custom_separator.setFrameShape(QFrame.Shape.VLine)  # Use HLine for vertical toolbars
        custom_separator.setFrameShadow(QFrame.Shadow.Sunken)

        # Set an explicit width and margins for the separator
        custom_separator.setFixedWidth(20)  # Total space the separator occupies
        custom_separator.setStyleSheet("""
            margin-left: 8px;
            margin-right: 8px;
            color: #444444; /* Line color */
        """)

        # self.addSeparator()
        self.addWidget(custom_separator)

        self.action_metadata_tools = self.addAction(
            resource_icon("exif-config.svg"),
            "Configure EXIF metadata tools",
            self.main_window.show_metadata_tool_popup,
        )
        self.action_metadata_tools.setCheckable(True)

        self.action_ai_config = self.addAction(
            resource_icon("ai-config.svg"),
            "Configure AI model folders",
            self.main_window.show_ai_config_popup,
        )
        self.action_ai_config.setCheckable(True)

        self.action_user_information = self.addAction(
            resource_icon("user-information.svg"),
            "Change user information",
            self.main_window.show_user_information_popup,
        )
        self.action_user_information.setCheckable(True)

        custom_separator = QFrame()
        custom_separator.setFrameShape(QFrame.Shape.VLine)  # Use HLine for vertical toolbars
        custom_separator.setFrameShadow(QFrame.Shadow.Sunken)

        # Set an explicit width and margins for the separator
        custom_separator.setFixedWidth(20)  # Total space the separator occupies
        custom_separator.setStyleSheet("""
            margin-left: 8px;
            margin-right: 8px;
            color: #444444; /* Line color */
        """)

        # Insert it directly into your toolbar
        self.addWidget(custom_separator)

        self.action_preview_table = self.addAction(
            resource_icon("preview-table.svg"),
            "Show preview table",
        )
        self.action_preview_table.triggered.connect(lambda _checked=False: self.main_window.toggle_preview_table_mode())

        self.action_show_region_window = self.addAction(
            resource_icon("region-dock.svg"),
            "Show region window",
            self.main_window.show_region_dock,
        )
        self.action_pop_out_region_window = self.addAction(
            resource_icon("region-popout.svg"),
            "Pop out region window",
            self.main_window.pop_out_region_editor,
        )

        self.action_about = self.addAction(
            resource_icon("about.svg"),
            "About GRAPHIS",
            self.main_window.pop_about.show,
        )
        self.centering_spacer_right_action = self._add_expanding_spacer()
