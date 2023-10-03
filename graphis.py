# Copyright (C) 2023 Martin Wieser
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

__version__ = '2.2'

import sys
from os import environ
import traceback
import json
from pathlib import Path
import numpy
import datetime
import csv
from exiftool import ExifTool
from multiprocessing import freeze_support
import os
from PySide6 import QtCore, QtGui
from PySide6.QtWidgets import *
from PySide6.QtCore import Slot, SignalInstance, QThreadPool, QEvent

from PySide6.QtGui import (QColor, Qt, QPixmap, QAction)

from app.preview_class import PreviewModel, PreviewDelegate
from app.var_classes import (Instructions, PreviewModelData,
                             image_region_role, put_struct_to_dict_or_remove, put_text_to_dict_or_remove,
                             put_struc_tag, find_key_role, PREVIEW_HEIGHT, load_config,
                             get_image_region_role)
from app.ui_main import Ui_MainWindow
from app.digitizerscene import DIGITIZERScene
from app.image_loader import image_loader
from app.db_handler import DBHandler
from app.popup_user import POPUPUser
from app.meta_exif import parse_img_region
from app.meta_exif import meta_writer
from app.json_model import JsonModel


class OutputWrapper(QtCore.QObject):
    outputWritten: SignalInstance = QtCore.Signal(object, object)

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
    finished: SignalInstance = QtCore.Signal()
    error: SignalInstance = QtCore.Signal(tuple)
    result: SignalInstance = QtCore.Signal(object)


class Worker(QtCore.QRunnable):

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignal()

    @Slot()
    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs, )
        except:
            # traceback.print_exc()
            exec_type, value = sys.exc_info()[:2]
            self.signals.error.emit((exec_type, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)


class MainWindow(QMainWindow):

    def __init__(self):
        QMainWindow.__init__(self)

        # try to load config File
        self.config_success, self.config_default, self.config_polygon, \
            self.config_rectangle, self.config_circle = load_config()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.label_version.setText(str(__version__))

        # ----------------------------------------------------------
        # Appearance STUFF
        # Window size ==> default size
        # start_size = QSize(1000, 1000)
        # self.resize(start_size)
        # self.setMinimumSize(start_size)
        # frame, shadow
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(17)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(0)
        self.shadow.setColor(QColor(0, 0, 0, 150))

        self.ui.splitter_images.setSizes([600, 150])
        self.ui.splitter_main.setSizes([600, 100])

        # self.ui.frame_main.setGraphicsEffect(self.shadow)

        def double_click_maximize_restore(event):
            # IF DOUBLE CLICK CHANGE STATUS
            if event.type() == QEvent.MouseButtonDblClick:
                self.maximize_restore()

            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.ui.frame_label_top_btns.mouseDoubleClickEvent = double_click_maximize_restore

        # --------------------------------------------------------------
        # move window
        self.dragPos = None

        def drag_window(event):
            # MOVE WINDOW
            if event.buttons() == Qt.MouseButton.LeftButton and not self.isMaximized():
                self.move(self.pos() + event.globalPosition().toPoint() - self.dragPos.toPoint())
                self.dragPos = event.globalPosition()
                event.accept()

        # WIDGET TO MOVE
        self.ui.frame_label_top_btns.mouseMoveEvent = drag_window

        # ==> RESIZE WINDOW
        self.sizegrip = QSizeGrip(self.ui.frame_size_grip)
        self.sizegrip.setStyleSheet("width: 20px; height: 20px; margin 0px; padding: 0px;")

        # ==> MINIMIZE
        self.ui.btn_minimize.clicked.connect(lambda: self.showMinimized())

        # ==> MAXIMIZE/RESTORE
        self.ui.btn_maximize_restore.clicked.connect(lambda: self.maximize_restore())

        # SHOW ==> CLOSE APPLICATION
        self.ui.btn_close.clicked.connect(lambda: self.close())

        # MultiThread
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(4)
        print("Multithreading with maximum %d threads" % self.thread_pool.maxThreadCount())

        self.ui.image_region_view.setAlternatingRowColors(True)
        self.model_image_region = JsonModel()
        self.model_image_region_all = JsonModel()

        self.ui.image_region_view.setModel(self.model_image_region)
        self.ui.image_all_region.setModel(self.model_image_region_all)

        self.ui.image_region_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.ui.image_region_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.ui.image_region_view.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        self.ui.image_all_region.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.ui.image_all_region.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.ui.image_all_region.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        #

        # Redirect Logger
        stdout = OutputWrapper(self, True)
        stdout.outputWritten.connect(self.handle_output)
        stderr = OutputWrapper(self, False)
        stderr.outputWritten.connect(self.handle_output)

        self.action_menu1 = QAction("Create new database", self)
        self.action_menu2 = QAction("Load database", self)
        self.action_menu3 = QAction("Add images of folder", self)
        self.action_menu3_subfolder = QAction("Add images of folder/subfolders", self)
        self.action_menu3_singleimage = QAction("Add single image", self)
        self.action_menu4 = QAction("Save bounding boxes to CSV file", self)
        self.action_menu5 = QAction("Save image regions to files", self)
        self.action_menu6 = QAction("Save image regions to files (keep original images)", self)

        self.alignMenu = QMenu(self)
        self.alignMenu.addAction(self.action_menu1)
        self.alignMenu.addAction(self.action_menu2)
        self.alignMenu.addSeparator()
        self.alignMenu.addAction(self.action_menu3_singleimage)
        self.alignMenu.addAction(self.action_menu3)
        self.alignMenu.addAction(self.action_menu3_subfolder)
        self.alignMenu.addSeparator()
        self.alignMenu.addAction(self.action_menu4)
        self.alignMenu.addAction(self.action_menu5)
        self.alignMenu.addAction(self.action_menu6)
        self.alignMenu.setStyleSheet("background: rgb(130, 130, 130);font: 10pt;\n")

        self.ui.toolButton.setMenu(self.alignMenu)

        # ----------------------------------------------------------
        # VARIABLES
        self.color_rectangle = QColor(self.config_rectangle.color_start)
        self.color_polygon = QColor(self.config_polygon.color_start)
        self.color_circle = QColor(self.config_circle.color_start)

        self.ui.btn_color_circle.set_color(self.color_circle)
        self.ui.btn_color_rectangle.set_color(self.color_rectangle)
        self.ui.btn_color_polygon.set_color(self.color_polygon)
        self.ui.lbl_circle_number.setStyleSheet(r"color: %s;" % self.color_circle.name())
        self.ui.lbl_rectangle_number.setStyleSheet(r"color: %s;" % self.color_rectangle.name())
        self.ui.lbl_polygon_number.setStyleSheet(r"color: %s;" % self.color_polygon.name())

        self.log_file = Path()
        self.pop_user = POPUPUser()
        self.len_image_list = 0
        self.log_sync_nr = 0
        self.image_list = []
        self.digitizer_scene = DIGITIZERScene()
        self.ui.view_digizizer.setScene(self.digitizer_scene)
        self.digitizer_scene.color_rectangle = self.color_rectangle
        self.digitizer_scene.color_polygon = self.color_polygon
        self.digitizer_scene.color_circle = self.color_circle

        self.delegate = PreviewDelegate()
        self.delegate.rectangle_color = self.color_rectangle
        self.delegate.polygon_color = self.color_polygon
        self.delegate.circle_color = self.color_circle
        self.ui.table_preview.setItemDelegate(self.delegate)
        self.model = PreviewModel()
        self.ui.table_preview.setModel(self.model)
        self.db = DBHandler()
        self.user = ''
        self.user_uri = ''
        self.current_item = None
        self.current_image = None
        self.count_rectangle = 0
        self.count_polygon = 0
        self.count_circle = 0
        self.rectangle_visible = True
        self.circle_visible = True
        self.polygon_visible = True
        self.image_loading = False
        self.image_loading_image_id_db = 0
        self.image_loading_name_path = ''
        self.image_loading_name = ''
        self.image_importer_list = []

        # ------------------------------------------------------------------------------------------------------------
        # EVENTS #
        # Menu Action Items
        self.action_menu1.triggered.connect(self.create_new_db)
        self.action_menu2.triggered.connect(self.load_existing_db)
        self.action_menu3.triggered.connect(lambda: self.load_input_image_folder())
        self.action_menu3_subfolder.triggered.connect(lambda: self.load_input_image_folder(subfolder=True))
        self.action_menu3_singleimage.triggered.connect(lambda: self.load_input_image_folder(single_image=True))
        self.action_menu4.triggered.connect(self.save_csv)
        self.action_menu5.triggered.connect(lambda: self.save_image_regions(keep_orig=False))
        self.action_menu6.triggered.connect(lambda: self.save_image_regions(keep_orig=True))

        # Connect double on image to load the image
        self.ui.table_preview.doubleClicked.connect(self.scene_load_image)

        # Geometry Creation
        self.ui.btn_create_rectangle.clicked.connect(lambda: self.set_instruction('create_rectangle'))
        self.ui.btn_create_polygon.clicked.connect(lambda: self.set_instruction('create_polygon'))
        self.ui.btn_create_circle.clicked.connect(lambda: self.set_instruction('create_circle'))
        self.ui.btn_geometry_move.clicked.connect(lambda: self.set_instruction('move_geometry'))
        self.ui.btn_geometry_resize.clicked.connect(lambda: self.set_instruction('change_geometry'))
        self.ui.btn_geometry_add_vertex.clicked.connect(lambda: self.set_instruction('add_vertex'))
        self.ui.btn_geometry_remove_vertex.clicked.connect(lambda: self.set_instruction('remove_vertex'))

        # self.ui.text_rectangle_attribute.focus_out.connect(self.save_data)

        self.digitizer_scene.object_att.connect(self.load_data)
        self.digitizer_scene.object_add.connect(self.add_data)
        self.digitizer_scene.change_object.connect(self.change_finetuner)
        self.digitizer_scene.message_no_valid.connect(self.message_no_valid_polygon)
        self.ui.btn_geometry_remove.clicked.connect(self.delete_object)

        # Visibility of geometries
        self.ui.btn_show_rectangle.clicked.connect(lambda: self.change_visibility('rectangle'))
        self.ui.btn_show_polygon.clicked.connect(lambda: self.change_visibility('polygon'))
        self.ui.btn_show_circle.clicked.connect(lambda: self.change_visibility('circle'))

        self.ui.btn_color_circle.colorChanged.connect(lambda color: self.change_color(color, 'circle'))
        self.ui.btn_color_rectangle.colorChanged.connect(lambda color: self.change_color(color, 'rectangle'))
        self.ui.btn_color_polygon.colorChanged.connect(lambda color: self.change_color(color, 'polygon'))

        # Save object data from fields
        self.ui.btn_object_save.clicked.connect(self.save_data)

        # Store region roles into drop down combo box
        self.ui.comboBox_region_role.addItems([x[0] for x in image_region_role])
        self.ui.comboBox_region_role.currentIndexChanged.connect(self.combo_change)

        self.ui.btn_expand_all.clicked.connect(self.ui.image_region_view.expandAll)
        self.ui.btn_collapse_all.clicked.connect(self.ui.image_region_view.collapseAll)

        self.ui.btn_expand_all_all_region.clicked.connect(self.ui.image_all_region.expandAll)
        self.ui.btn_collapse_all_all_region.clicked.connect(self.ui.image_all_region.collapseAll)

        # window basic attributes
        # self.ui_start_up()
        self.pop_user.show()
        self.pop_user.got_user.connect(self.user_save)

    # ----------------------------------------------------------
    # SHOW GUI
    # self.show()

    # Thread handler
    @Slot(bool)
    def thread_output_exif(self, success):
        self.ui.waiting_spinner.stop()
        self.db.is_locked = False

    @Slot(bool)
    def thread_output(self, success: bool):

        if success:
            self.clean_all_views_and_tables(db_save=True)
            self.loader_all()

        self.ui.waiting_spinner.stop()
        self.db.is_locked = False

    @Slot(bool)
    def thread_output(self, success: bool):

        if success:
            self.clean_all_views_and_tables(db_save=True)
            self.loader_all()

        self.ui.waiting_spinner.stop()
        self.db.is_locked = False

    @Slot(object)
    def thread_output_image_loader(self, pixmap):
        self.digitizer_scene.change_image(pixmap)
        self.set_image_meta_and_display_meta()
        self.ui.waiting_spinner.stop()
        self.image_loading = False

    def thread_output_image_importer(self):
        added_images = []
        failed_images = 0
        for image in self.image_importer_list:

            rel = os.path.relpath(image, self.db.db_path)
            new_path = os.path.normpath(os.path.join(self.db.db_path, rel))
            image_id = self.db.db_store_image(Path(rel))
            if image_id >= 0:
                self.image_list.append([Path(new_path), image_id])
                added_images.append([Path(new_path), image_id])
            else:
                failed_images += 1

        len_image_list = len(added_images)
        self.len_image_list = len_image_list

        if failed_images:
            print(f"\t\t{failed_images} images ignored (e.g already imported)")
        # self.ui.lbl_image_nr.setText(str(len_image_list))

        if len_image_list > 0:
            print(f"\t\tStart to import {len_image_list} images")
            worker = Worker(add_preview, added_images, self.db, self.user,
                            self.config_default['CONTRIBUTOR_TAG'])
            worker.signals.result.connect(self.thread_output)
            self.ui.waiting_spinner.start()
            self.thread_pool.start(worker)
        else:
            self.db.is_locked = False
            self.ui.waiting_spinner.stop()

    @Slot(tuple)
    def thread_output_image_error(self, error):

        msg = QMessageBox(self, text="Sorry, seems not to be a valid image format")
        msg.setWindowTitle('Warning')
        # msg.setStyleSheet('background-color: rgb(40, 44, 52);')
        msg.exec()
        print("Image loading failed. No supported image format: " + self.image_importer_list[0].suffix)
        self.db.is_locked = False
        self.ui.waiting_spinner.stop()

    def set_image_meta_and_display_meta(self):
        self.ui.view_digizizer.fitInView(self.digitizer_scene.image_item, Qt.KeepAspectRatio)
        self.digitizer_scene.image_id_db = self.image_loading_image_id_db
        self.ui.lbl_image_name.setText(self.image_loading_name_path)

        string_wrap = self.image_loading_name
        if len(string_wrap) > 110:
            string_wrap = string_wrap[:110] + '\n' + string_wrap[110:]

        self.ui.lbl_image_path.setText(string_wrap)
        self.current_image = {'id': self.image_loading_image_id_db - 1, 'name': self.image_loading_name_path}
        data = self.db.db_load_objects_image(self.image_loading_image_id_db)

        if data:
            for element in data:
                data = json.loads(element["data"])
                if element["object_type"] == 'rectangle':
                    color = self.color_rectangle
                elif element["object_type"] == 'circle':
                    color = self.color_circle
                else:
                    color = self.color_polygon
                self.digitizer_scene.add_object(element["object_type"], data, element['id'], color)

            self.image_region_view_load_all_image()

    # ----------------------------------------------------------
    # Functions

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if self.digitizer_scene.width() != 0.0:
            # Navigate to next or previous image
            if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:

                next_index = self.model.get_index(self.image_loading_image_id_db + 1)
                if next_index is not None:
                    self.scene_load_image(next_index)

            if event.key() == Qt.Key_Backspace:
                next_index = self.model.get_index(self.image_loading_image_id_db - 1)
                if next_index is not None:
                    self.scene_load_image(next_index)

        if event.key() == Qt.Key.Key_S and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.save_data()

    #  def eventFilter(self, source, event):
    #      if event.type() == QtCore.QEvent.Type.KeyPress:

    #              if self.digitizer_scene.width() != 0.0:
    #                  # Navigate to next or previous image
    #                  if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:

    #                      next_index = self.model.get_index(self.image_loading_image_id_db+1)
    #                      if not next_index is None:
    #                          self.scene_load_image(next_index)
    #                          return True

    #                  if event.key() == Qt.Key_Backspace:
    #                      next_index = self.model.get_index(self.image_loading_image_id_db-1)
    #                      if not next_index is None:
    #                          self.scene_load_image(next_index)
    #                          return True

    #              if event.key() == Qt.Key.Key_S and event.modifiers() == Qt.Modifier.CTRL:
    #                  self.save_data()
    #                  return True
    #      return False

    def maximize_restore(self):

        if not self.isMaximized():
            self.showMaximized()
            self.ui.horizontalLayout.setContentsMargins(0, 0, 0, 0)
            self.ui.btn_maximize_restore.setToolTip("Restore")
            self.ui.btn_maximize_restore.setIcon(QtGui.QIcon(u":/icons/icons/cil-window-restore.png"))
            self.ui.frame_size_grip.hide()
        else:
            self.showNormal()
            self.resize(self.width() + 1, self.height() + 1)
            self.ui.horizontalLayout.setContentsMargins(0, 0, 0, 0)
            self.ui.btn_maximize_restore.setToolTip("Maximize")
            self.ui.btn_maximize_restore.setIcon(QtGui.QIcon(u":/icons/icons/cil-window-maximize.png"))
            self.ui.frame_size_grip.show()

    def mousePressEvent(self, event):
        self.dragPos = event.globalPosition()
        focused_widget = self.focusWidget()
        if isinstance(focused_widget, QPlainTextEdit):
            focused_widget.clearFocus()
        super(MainWindow, self).mousePressEvent(event)

    @Slot(str, str)
    def user_save(self, user, user_uri):
        self.user = user
        self.user_uri = user_uri
        self.ui.txt_user_name.setPlainText(user)
        self.ui.txt_user_indent.setPlainText(user_uri)
        print('Welcome ' + self.user.upper() + '.\nEnjoy working with GRAPHIS')
        if not self.config_success:
            print('Config file is not proper set.\nFallback on malformed options')
        self.show()

    def handle_output(self, text, stdout):
        self.ui.info_screen.moveCursor(QtGui.QTextCursor.End)
        self.ui.info_screen.setTextColor(QColor(255, 255, 255) if stdout else QColor(255, 0, 0))
        self.ui.info_screen.insertPlainText(text)
        self.ui.info_screen.setTextColor(QColor(255, 255, 255))

    def combo_change(self):
        new_id = ''
        new_name = self.sender().currentText()
        for x in image_region_role:
            if x[0] == new_name:
                new_id = x[1]
        self.ui.txt_rrole_ident.setPlainText(new_id)

    def image_region_view_load_all_image(self):

        json_image_all_region = []
        data = self.db.db_load_objects_image(self.current_image['id'] + 1)
        for obj in data:
            json_image_all_region.append(json.loads(obj['data'])['attributes'])
        self.model_image_region_all.load(json_image_all_region)
        self.ui.image_all_region.setModel(self.model_image_region_all)
        self.ui.image_all_region.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.ui.image_all_region.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        # self.ui.image_all_region.resizeColumnToContents(1)

    def scene_load_image(self, index):

        if not self.image_loading:
            self.image_loading = True
            self.clear_entries()
            self.digitizer_scene.current_instruction = Instructions.No_Instruction
            self.digitizer_scene.instruction_active = False
            self.digitizer_scene.clear()

            self.model_image_region.clear()
            self.model_image_region_all.clear()
            self.current_item = None

            self.digitizer_scene.clear_image()
            if Path(index.data(Qt.ItemDataRole.UserRole)).exists():

                worker = Worker(image_loader, index.data(Qt.ItemDataRole.UserRole))
                worker.signals.result.connect(self.thread_output_image_loader)
                self.image_loading_image_id_db = index.data(Qt.ItemDataRole.UserRole + 1)
                self.image_loading_name_path = index.data(Qt.ItemDataRole.ToolTipRole)
                self.image_loading_name = index.data(Qt.ItemDataRole.UserRole)
                self.thread_pool.start(worker)
                self.ui.waiting_spinner.start()
            else:
                print("Image does not exist.")
                self.image_loading = False

    def change_visibility(self, objects_type):
        self.digitizer_scene.hide_item(objects_type)
        self.current_item = None

        self.change_visible_button(objects_type)

    def change_visible_button(self, objects_type: str, show_all=False):

        if show_all:
            self.circle_visible = True
            icon = QtGui.QIcon(u":/icons/icons/circle_show.svg")
            self.ui.btn_show_circle.setIcon(icon)
            self.rectangle_visible = True
            icon = QtGui.QIcon(u":/icons/icons/rectangle_show.svg")
            self.ui.btn_show_rectangle.setIcon(icon)
            self.polygon_visible = True
            icon = QtGui.QIcon(u":/icons/icons/polygon_show.svg")
            self.ui.btn_show_polygon.setIcon(icon)
        else:

            if objects_type == "circle":
                self.circle_visible = not self.circle_visible
                if self.circle_visible:
                    icon = QtGui.QIcon(u":/icons/icons/circle_show.svg")
                else:
                    icon = QtGui.QIcon(u":/icons/icons/circle_hide.svg")
                self.ui.btn_show_circle.setIcon(icon)

            elif objects_type == "rectangle":
                self.rectangle_visible = not self.rectangle_visible
                if self.rectangle_visible:
                    icon = QtGui.QIcon(u":/icons/icons/rectangle_show.svg")
                else:
                    icon = QtGui.QIcon(u":/icons/icons/rectangle_hide.svg")
                self.ui.btn_show_rectangle.setIcon(icon)

            elif objects_type == "polygon":
                self.polygon_visible = not self.polygon_visible
                if self.polygon_visible:
                    icon = QtGui.QIcon(u":/icons/icons/polygon_show.svg")
                else:
                    icon = QtGui.QIcon(u":/icons/icons/polygon_hide.svg")
                self.ui.btn_show_polygon.setIcon(icon)

    @Slot(object)
    def change_color(self, color, object_type):

        if object_type == "circle":
            self.color_circle = color
            self.digitizer_scene.color_circle = color
            self.delegate.circle_color = color
            self.ui.lbl_circle_number.setStyleSheet(r"color: %s;" % self.color_circle.name())

        elif object_type == "rectangle":
            self.color_rectangle = color
            self.digitizer_scene.color_rectangle = color
            self.delegate.rectangle_color = color
            self.ui.lbl_rectangle_number.setStyleSheet(r"color: %s;" % self.color_rectangle.name())

        elif object_type == "polygon":
            self.color_polygon = color
            self.digitizer_scene.color_polygon = color
            self.delegate.polygon_color = color
            self.ui.lbl_polygon_number.setStyleSheet(r"color: %s;" % self.color_polygon.name())

        self.digitizer_scene.change_color(object_type, color)

    @Slot()
    def save_data(self):

        if self.current_item is None:
            self.clear_entries()

        if self.digitizer_scene.image_item is not None:
            if self.current_item is not None:

                object_type = self.current_item['object_type']
                data = self.current_item['data']['attributes']

                data = put_text_to_dict_or_remove(data, 'RId', self.ui.txt_rid.toPlainText())
                data = put_text_to_dict_or_remove(data, 'Name', self.ui.txt_rname.toPlainText())

                data = put_struct_to_dict_or_remove(data, 'RCtype', self.ui.txt_rctype_indent.toPlainText(),
                                                    self.ui.txt_rctype_name.toPlainText())

                data = put_struct_to_dict_or_remove(data, 'RRole', self.ui.txt_rrole_ident.toPlainText(),
                                                    self.ui.comboBox_region_role.currentText())

                data = put_struc_tag(data, self.config_default["CONTRIBUTOR_TAG"],
                                     self.ui.contr_creator_role.toPlainText(),
                                     self.ui.contr_creator_ident.toPlainText(),
                                     self.ui.contr_creator_name.toPlainText())

                describer_text = self.ui.xmp_dc.toPlainText()

                transcriber_text = self.ui.xmp_dc_transcriber.toPlainText()

                indent_user = self.ui.txt_user_indent.toPlainText()
                name_user = self.ui.txt_user_name.toPlainText()

                if describer_text != data.get(self.config_default["TAG_DESCRIBER"], ''):
                    if describer_text:
                        temp_user_indent = indent_user
                        temp_user_name = name_user
                    else:
                        temp_user_indent = ''
                        temp_user_name = ''
                    data = put_struc_tag(data, self.config_default["CONTRIBUTOR_TAG"],
                                         self.get_config_role(object_type, 'describer_role'),
                                         temp_user_indent,
                                         temp_user_name)

                if transcriber_text != data.get(self.config_default["TAG_TRANSCRIBER"], ''):
                    if transcriber_text:
                        temp_user_indent = indent_user
                        temp_user_name = name_user
                    else:
                        temp_user_indent = ''
                        temp_user_name = ''
                    data = put_struc_tag(data, self.config_default["CONTRIBUTOR_TAG"],
                                         self.get_config_role(object_type, 'transcriber_role'),
                                         temp_user_indent,
                                         temp_user_name)

                # Old code to append
                # success, idx = find_key_role(data, self.config_default["CONTRIBUTOR_TAG"],
                #                             self.get_config_role(object_type, 'describer_role'))
                # if success:
                #
                #    if describer_text != data.get(self.config_default["TAG_DESCRIBER"], ''):
                #
                #        data = put_struc_tag(data, self.config_default["CONTRIBUTOR_TAG"],
                #                             self.get_config_role(object_type, 'describer_modifier_role'),
                #                             descr_ident,
                #                             descr_name)
                # else:
                #
                #    if describer_text:
                #        data = put_struc_tag(data, self.config_default["CONTRIBUTOR_TAG"],
                #                             self.get_config_role(object_type, 'describer_creator_role'),
                #                             descr_ident,
                #                             descr_name)

                data = put_text_to_dict_or_remove(data, self.config_default["TAG_TRANSCRIBER"],
                                                  transcriber_text)

                data = put_text_to_dict_or_remove(data, self.config_default["TAG_DESCRIBER"],
                                                  describer_text)

                self.digitizer_scene.set_tooltip(self.current_item['id'], data['RId'])
                self.current_item['data']['attributes'] = data
                self.model_image_region.load(data)
                self.ui.image_region_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
                self.ui.image_region_view.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
                self.db.update_object(obj_id=self.current_item['id'], data=self.current_item['data'])

                self.change_color(self.color_rectangle, 'rectangle')
                self.change_color(self.color_polygon, 'polygon')
                self.change_color(self.color_circle, 'circle')
                self.current_item = None
                self.image_region_view_load_all_image()
                self.clear_entries(action_stay_active=True)

    def clear_entries(self, action_stay_active=False):
        self.current_item = None

        self.change_visible_button('', show_all=True)

        if not action_stay_active:
            self.digitizer_scene.instruction_active = False
            self.ui.btn_create_rectangle.setIcon(QtGui.QIcon(u":/icons/icons/rectangle.svg"))
            self.ui.btn_create_polygon.setIcon(QtGui.QIcon(u":/icons/icons/polygon.svg"))
            self.ui.btn_create_circle.setIcon(QtGui.QIcon(u":/icons/icons/circle.svg"))
            self.ui.btn_geometry_move.setIcon(QtGui.QIcon(u":/icons/icons/move.svg"))
            self.ui.btn_geometry_resize.setIcon(QtGui.QIcon(u":/icons/icons/resize.svg"))
            self.ui.btn_geometry_add_vertex.setIcon(QtGui.QIcon(u":/icons/icons/add_node.svg"))
            self.ui.btn_geometry_remove_vertex.setIcon(QtGui.QIcon(u":/icons/icons/remove_node.svg"))

            self.digitizer_scene.current_instruction = Instructions.No_Instruction

        self.model_image_region.clear()
        self.ui.txt_rid.setPlainText('')
        self.ui.txt_rname.setPlainText('')

        self.ui.contr_creator_name.setPlainText('')
        self.ui.contr_creator_ident.setPlainText('')
        self.ui.contr_creator_role.setPlainText('')

        self.ui.contr_describer_name.setPlainText('')
        self.ui.contr_describer_ident.setPlainText('')
        self.ui.contr_describer_role.setPlainText('')

        self.ui.contr_transcriber_name.setPlainText('')
        self.ui.contr_transcriber_ident.setPlainText('')
        self.ui.contr_transcriber_role.setPlainText('')

        self.ui.txt_rctype_name.setPlainText('')
        self.ui.txt_rctype_indent.setPlainText('')

        self.ui.xmp_dc.setPlainText('')
        self.ui.xmp_dc_transcriber.setPlainText('')

    def get_config_role(self, geom_type, config_attr):
        if geom_type == 'rectangle':
            item_tag = getattr(self.config_rectangle, config_attr)
        elif geom_type == 'polygon':
            item_tag = getattr(self.config_polygon, config_attr)
        else:
            item_tag = getattr(self.config_circle, config_attr)
        return item_tag

    @Slot(int)
    def change_finetuner(self, object_id):

        self.clear_entries()
        data = self.db.db_load_object(object_id)
        jdata = json.loads(data['data'])

        # jdata['attributes'] = append_struc_tag(jdata['attributes'],
        jdata['attributes'] = put_struc_tag(jdata['attributes'],
                                            tag=self.config_default["CONTRIBUTOR_TAG"],
                                            role=self.get_config_role(data['object_type'],
                                                                      'region_creator_role'),
                                            indentifier=self.ui.txt_user_indent.toPlainText(),
                                            name=self.ui.txt_user_name.toPlainText())

        self.current_item = {'id': object_id, 'data': jdata, 'object_type': data['object_type']}

        self.db.update_object(obj_id=object_id, data=self.current_item['data'])

        self.change_color(self.color_rectangle, 'rectangle')
        self.change_color(self.color_polygon, 'polygon')
        self.change_color(self.color_circle, 'circle')

        self.current_item = None
        self.clear_entries()
        self.image_region_view_load_all_image()

    @Slot(int)
    def load_data(self, object_id):
        self.clear_entries()
        data = self.db.db_load_object(object_id)

        jdata = json.loads(data['data'])

        self.model_image_region.load(jdata['attributes'])
        self.ui.image_region_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.ui.image_region_view.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.current_item = {'id': object_id, 'data': jdata, 'object_type': data['object_type']}

        self.parse_show_data(data['object_type'], self.current_item['data']['attributes'])

    @Slot()
    def message_no_valid_polygon(self):
        msg = QMessageBox(self,
                          text="That was or will not be a valid polygon\nEither not enough points (min 3) or self intersecting")
        msg.setWindowTitle('Warning')
        # msg.setStyleSheet('background-color: rgb(40, 44, 52);')
        msg.exec()
        self.clear_entries()

    @Slot(int)
    def add_data(self, object_id):
        self.clear_entries(action_stay_active=True)
        data = self.db.db_load_object(object_id)
        jdata = json.loads(data['data'])
        image = Path(self.current_image['name'])

        # self.model_image_region.load(jdata['attributes'])
        img_region_dict = {"RegionBoundary": jdata['attributes']["RegionBoundary"], 'RCtype': [
            {'Identifier': [self.get_config_role(data['object_type'], 'rctype_identifier')],
             'Name': self.get_config_role(data['object_type'], 'rctype_name')}]}

        self.ui.comboBox_region_role.setCurrentText(
            self.get_config_role(data['object_type'], 'region_role_name'))
        self.ui.txt_rrole_ident.setPlainText(
            get_image_region_role(self.get_config_role(data['object_type'], 'region_role_name')))

        # RId
        # datetime.now().strftime('%y%j%H%M%S')
        dt = datetime.datetime.now().strftime('%y%m%dT%H:%M:%S')
        rid = image.stem + '_' + dt
        name_region = self.get_config_role(data['object_type'], 'region_name_prefix')  # + dt
        img_region_dict = put_text_to_dict_or_remove(img_region_dict, 'RId', rid)
        img_region_dict = put_text_to_dict_or_remove(img_region_dict, 'Name', name_region)

        # Role
        img_region_dict = put_struct_to_dict_or_remove(img_region_dict, tag='RRole',
                                                       indentifier=self.ui.txt_rrole_ident.toPlainText(),
                                                       name=self.ui.comboBox_region_role.currentText())

        # Region Creator
        img_region_dict = put_struc_tag(img_region_dict, self.config_default["CONTRIBUTOR_TAG"],
                                        self.get_config_role(data['object_type'], 'region_creator_role'),
                                        indentifier=self.ui.txt_user_indent.toPlainText(),
                                        name=self.ui.txt_user_name.toPlainText())

        jdata['attributes'] = img_region_dict
        self.current_item = {'id': object_id, 'data': jdata, 'object_type': data['object_type']}

        if data['object_type'] == 'rectangle':
            self.count_rectangle += 1
            self.model.add_number(self.current_image['id'], 'rectangle')
            self.ui.lbl_rectangle_number.setText(str(self.count_rectangle))
        elif data['object_type'] == 'polygon':
            self.count_polygon += 1
            self.model.add_number(self.current_image['id'], 'polygon')
            self.ui.lbl_polygon_number.setText(str(self.count_polygon))
        else:
            self.count_circle += 1
            self.model.add_number(self.current_image['id'], 'circle')
            self.ui.lbl_circle_number.setText(str(self.count_circle))

        self.db.update_object(obj_id=self.current_item['id'], data=self.current_item['data'])
        self.parse_show_data(data['object_type'], self.current_item['data']['attributes'])
        self.model_image_region.load(self.current_item['data']['attributes'])
        self.ui.image_region_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.ui.image_region_view.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.image_region_view_load_all_image()

    def parse_show_data(self, object_type, dict_item: dict):

        region_id = dict_item.get("RId", '')
        name = dict_item.get("Name", '')

        self.ui.txt_rid.setPlainText(region_id)
        self.ui.txt_rname.setPlainText(name)

        dict_role = dict_item.get('RRole', [])
        if dict_role:
            new_id = image_region_role[0][1]
            new_name = image_region_role[0][0]
            for x in image_region_role:
                if x[0] == dict_role[0]['Name']:
                    new_id = x[1]
                    new_name = x[0]

            self.ui.comboBox_region_role.setCurrentText(new_name)
            self.ui.txt_rrole_ident.setPlainText(new_id)

        dict_contr = dict_item.get(self.config_default["CONTRIBUTOR_TAG"], {})
        if dict_contr:

            success, idx = find_key_role(dict_item, self.config_default["CONTRIBUTOR_TAG"],
                                         self.get_config_role(object_type, 'region_creator_role'))
            if success:
                self.ui.contr_creator_name.setPlainText(dict_contr[idx]['Name'])
                self.ui.contr_creator_ident.setPlainText(dict_contr[idx]['Identifier'][-1])
                self.ui.contr_creator_role.setPlainText(dict_contr[idx]['Role'][-1])

            success, idx = find_key_role(dict_item, self.config_default["CONTRIBUTOR_TAG"],
                                         self.get_config_role(object_type, 'describer_role'))
            if success:
                self.ui.contr_describer_name.setPlainText(dict_contr[idx]['Name'])
                self.ui.contr_describer_ident.setPlainText(dict_contr[idx]['Identifier'][-1])
                self.ui.contr_describer_role.setPlainText(dict_contr[idx]['Role'][-1])

            success, idx = find_key_role(dict_item, self.config_default["CONTRIBUTOR_TAG"],
                                         self.get_config_role(object_type, 'transcriber_role'))
            if success:
                self.ui.contr_transcriber_name.setPlainText(dict_contr[idx]['Name'])
                self.ui.contr_transcriber_ident.setPlainText(dict_contr[idx]['Identifier'][-1])
                self.ui.contr_transcriber_role.setPlainText(dict_contr[idx]['Role'][-1])

        dict_rctype = dict_item.get('RCtype', {})
        if dict_rctype:
            self.ui.txt_rctype_name.setPlainText(dict_rctype[0]['Name'])
            self.ui.txt_rctype_indent.setPlainText(dict_rctype[0]['Identifier'][0])

        xmp_dc = dict_item.get(self.config_default["TAG_DESCRIBER"], '')
        self.ui.xmp_dc.setPlainText(xmp_dc)

        xmp_trans = dict_item.get(self.config_default["TAG_TRANSCRIBER"], '')
        self.ui.xmp_dc_transcriber.setPlainText(xmp_trans)

    def delete_object(self):
        if not self.db.is_locked:
            if self.current_item:

                self.digitizer_scene.delete_object(self.current_item['id'])
                self.db.db_delete_geometry(self.current_item['id'])

                if self.current_item['object_type'] == 'rectangle':
                    self.count_rectangle -= 1
                    self.model.remove_number(self.current_image['id'], 'rectangle')
                    self.ui.lbl_rectangle_number.setText(str(self.count_rectangle))
                elif self.current_item['object_type'] == 'polygon':
                    self.count_polygon -= 1
                    self.model.remove_number(self.current_image['id'], 'polygon')
                    self.ui.lbl_polygon_number.setText(str(self.count_polygon))
                else:
                    self.count_circle -= 1
                    self.model.remove_number(self.current_image['id'], 'circle')
                    self.ui.lbl_circle_number.setText(str(self.count_circle))
                self.current_item = None
                self.clear_entries()
                self.image_region_view_load_all_image()
        else:
            print("Database is locked")

    def set_instruction(self, action: str):
        self.clear_entries()
        self.model_image_region.clear()

        if not self.digitizer_scene.instruction_active:
            self.ui.btn_create_rectangle.setIcon(QtGui.QIcon(u":/icons/icons/rectangle.svg"))
            self.ui.btn_create_polygon.setIcon(QtGui.QIcon(u":/icons/icons/polygon.svg"))
            self.ui.btn_create_circle.setIcon(QtGui.QIcon(u":/icons/icons/circle.svg"))
            self.ui.btn_geometry_move.setIcon(QtGui.QIcon(u":/icons/icons/move.svg"))
            self.ui.btn_geometry_resize.setIcon(QtGui.QIcon(u":/icons/icons/resize.svg"))
            self.ui.btn_geometry_add_vertex.setIcon(QtGui.QIcon(u":/icons/icons/add_node.svg"))
            self.ui.btn_geometry_remove_vertex.setIcon(QtGui.QIcon(u":/icons/icons/remove_node.svg"))

            if action == 'create_rectangle':
                self.current_item = None
                self.digitizer_scene.current_instruction = Instructions.Rectangle_Instruction
                self.ui.btn_create_rectangle.setIcon(QtGui.QIcon(u":/icons/icons/rectangle_active.svg"))
            elif action == 'create_polygon':
                self.current_item = None
                self.digitizer_scene.current_instruction = Instructions.Polygon_Instruction
                self.ui.btn_create_polygon.setIcon(QtGui.QIcon(u":/icons/icons/polygon_active.svg"))
            elif action == 'create_circle':
                self.digitizer_scene.current_instruction = Instructions.Circle_Instruction
                self.ui.btn_create_circle.setIcon(QtGui.QIcon(u":/icons/icons/circle_active.svg"))
            elif action == 'move_geometry':
                self.digitizer_scene.current_instruction = Instructions.Move_Instruction
                self.ui.btn_geometry_move.setIcon(QtGui.QIcon(u":/icons/icons/move_active.svg"))
            elif action == 'change_geometry':
                self.digitizer_scene.current_instruction = Instructions.Change_Instruction
                self.ui.btn_geometry_resize.setIcon(QtGui.QIcon(u":/icons/icons/resize_active.svg"))
            elif action == 'add_vertex':
                self.digitizer_scene.current_instruction = Instructions.Add_Vertex
                self.ui.btn_geometry_add_vertex.setIcon(QtGui.QIcon(u":/icons/icons/add_node_active.svg"))
            elif action == 'remove_vertex':
                self.digitizer_scene.current_instruction = Instructions.Remove_Vertex
                self.ui.btn_geometry_remove_vertex.setIcon(QtGui.QIcon(u":/icons/icons/remove_node_active.svg"))

    def clean_all_views_and_tables(self, db_save=False):
        self.digitizer_scene.clear()

        self.clear_entries()
        self.model_image_region_all.clear()
        self.ui.lbl_image_name.setText('')
        self.ui.lbl_image_path.setText('')
        self.ui.table_preview.setModel(None)
        self.image_list = []
        self.current_image = None
        self.current_item = None
        self.count_rectangle = 0
        self.count_polygon = 0
        self.count_circle = 0
        self.ui.lbl_rectangle_number.setText(str(0))
        self.ui.lbl_polygon_number.setText(str(0))
        self.ui.lbl_circle_number.setText(str(0))
        self.ui.lbl_image_number.setText(str(0))
        if self.db.db_is_set and not self.db.is_locked and not db_save:
            self.db.db_close()
            self.db.db_is_set = False
        self.ui.lbl_sqlite_name.setText('')

    def load_existing_db(self):
        if not self.db.is_locked:
            self.digitizer_scene.instruction_active = False
            db_path, _ = QFileDialog.getOpenFileName(self, caption="Load Database",
                                                     dir='.', filter='SQLITE Files (*.sqlite)')
            # clear scene GIS and digitizer
            self.clean_all_views_and_tables()

            if db_path:
                self.db.db_load(Path(db_path), self.user)

                # self.db.db_check_abs_path()

                self.digitizer_scene.db = self.db
                print('Existing database was loaded: ' + Path(db_path).name)
                self.loader_all()
                self.ui.lbl_sqlite_name.setText(Path(db_path).name)

    def loader_all(self):

        images = self.db.db_load_images_list()

        if not images:
            return

        self.model = PreviewModel()
        self.ui.table_preview.setModel(self.model)

        self.image_list = []

        for x in images:
            if x['preview'] is not None:
                # rel = os.path.relpath(x['path'], self.db.db_path)

                new_path = os.path.normpath(os.path.join(self.db.db_path, x['path']))
                self.image_list.append([Path(new_path), x['id']])
                pixmap = QPixmap()
                pixmap.loadFromData(x['preview'], "JPG")
                # image = QImage(pixmap)
                item = PreviewModelData(x['id'], new_path, Path(new_path).name, pixmap,
                                        x['polygon_count'], x['rectangle_count'], x['circle_count'])
                self.model.appendData(item)

            else:
                print("\tEmpty Preview in database image: ", x['path'])

        # items = []
        # self.abstractModel = QStandardItemModel()
        # self.abstractModel.setHorizontalHeaderLabels(['Level', 'Values'])

        objects = self.db.db_load_objects_all()
        if objects:

            #    qq = {}
            #    qq['rectangle'] = {}
            #    qq['polygon'] = {}
            #    qq['circle'] = {}
            #    for img in images:
            #        img_name = Path(img['path']).name
            #        if not qq['rectangle'].get(img_name):
            #            qq['rectangle'][img_name] = {}
            #            qq['polygon'][img_name] = {}
            #            qq['circle'][img_name] = {}
            #    for i in objects:
            #        obj_type = i['object_type']
            #        image = i['image_name']
            #        if obj_type == 'rectangle':
            #            self.count_rectangle += 1
            #        else:
            #            self.count_polygon += 1
            #        data = json.loads(i['data'])
            #        region_id = data["attributes"].get("RId", '')
            #        if region_id:
            #            qq[obj_type][image][i['id']] = region_id
            #        else:
            #            qq[obj_type][image][i['id']] = ''

            for i in objects:
                obj_type = i['object_type']
                # image = i['image_name']
                if obj_type == 'rectangle':
                    self.count_rectangle += 1
                elif obj_type == 'polygon':
                    self.count_polygon += 1
                elif obj_type == 'circle':
                    self.count_circle += 1

        self.ui.table_preview.resizeRowsToContents()
        self.ui.table_preview.resizeColumnsToContents()
        self.db.is_locked = False

        self.ui.lbl_image_number.setText(str(len(self.model.previews)))
        self.ui.lbl_rectangle_number.setText(str(self.count_rectangle))
        self.ui.lbl_polygon_number.setText(str(self.count_polygon))
        self.ui.lbl_circle_number.setText(str(self.count_circle))

    def create_new_db(self):
        if not self.db.is_locked:
            self.clear_entries()
            self.model_image_region.clear()
            self.digitizer_scene.instruction_active = False
            db_path, _ = QFileDialog.getSaveFileName(caption="Create Database",
                                                     dir='.', filter='SQLITE Files (*.sqlite)')

            self.clean_all_views_and_tables()

            if db_path:
                path = Path(db_path)
                if path.exists():
                    try:
                        path.unlink()
                        print('DB File was overwritten!')
                    except:
                        print('DB File seems to be locked!', file=sys.stderr)
                        print('Maybe opened by program. Otherwise try restart of computer', file=sys.stderr)
                        return

                success = self.db.db_create(Path(db_path), self.user)

                if success:
                    self.digitizer_scene.db = self.db
                    print('New database was created: ' + Path(db_path).name)
                    self.model = PreviewModel()
                    self.ui.table_preview.setModel(self.model)
                    self.ui.lbl_sqlite_name.setText(path.name)

        else:
            print('Database is locked')

    def load_input_image_folder(self, subfolder=False, single_image=False):

        if self.db.db_is_set and not self.db.is_locked:
            self.db.is_locked = True
            image_path, _ = QFileDialog.getOpenFileName(self,
                                                        caption="Click on one image. Only identical file formats are "
                                                                "imported")
            if image_path:
                print("Importing images")
                image_path = Path(image_path)

                image_path_parent = image_path.parent
                # self.image_list=[file for file in image_path_parent.iterdir() if file.suffix in image_path.suffix]

                if subfolder:
                    image_list = list(image_path_parent.rglob('*' + image_path.suffix))
                elif single_image:
                    image_list = [image_path]
                else:
                    image_list = list(image_path_parent.glob('*' + image_path.suffix))

                worker = Worker(image_loader, image_list[0].as_posix())
                worker.signals.result.connect(self.thread_output_image_importer)
                worker.signals.error.connect(self.thread_output_image_error)
                self.image_importer_list = image_list
                self.thread_pool.start(worker)
                self.ui.waiting_spinner.start()
                # image = image_loader(image_list[0].as_posix())

            else:
                self.db.is_locked = False
        else:
            msg = QMessageBox(self, text="Seems no database is active or database is locked")
            msg.setWindowTitle('Warning')
            msg.exec()

    def save_image_regions(self, keep_orig=False):

        if self.db.db_is_set and not self.db.is_locked:
            self.db.is_locked = True

            worker = Worker(meta_writer, self.db, self.user, keep_orig)
            worker.signals.result.connect(self.thread_output_exif)
            self.ui.waiting_spinner.start()
            self.thread_pool.start(worker)

    def save_csv(self):
        if self.db.db_is_set:
            objs = self.db.db_load_objects_all()

            if objs:
                image_path, _ = QFileDialog.getSaveFileName(self, caption="Export rectangle CSV",
                                                            filter='CSV (*.csv)')
                if image_path:
                    with open(image_path, 'w', newline='', encoding='utf-8') as fid:

                        csv_writer = csv.writer(fid, delimiter=',', quotechar='"',
                                                quoting=csv.QUOTE_MINIMAL)

                        csv_writer.writerow(['image', 'type', 'RId', 'UpperLeftX', 'UpperLeftY',
                                             'Width', 'Height', self.config_default["TAG_DESCRIBER"],
                                             self.config_default["TAG_TRANSCRIBER"], 'Polygon'])
                        for obj in objs:  #

                            image = obj['image_name']
                            data = json.loads(obj['data'])
                            np_coords = numpy.array(data["coords"])
                            if obj['object_type'] == 'circle':

                                uplx = np_coords[0] - np_coords[2]
                                uply = np_coords[1] - np_coords[2]
                                w = np_coords[0] + np_coords[2]
                                h = np_coords[1] + np_coords[2]

                            else:
                                min_rec = numpy.min(np_coords, axis=0)
                                max_rec = numpy.max(np_coords, axis=0)
                                uplx = min_rec[0]
                                uply = min_rec[1]
                                w = max_rec[0] - min_rec[0]
                                h = max_rec[1] - min_rec[1]

                            polygon = ''
                            if obj['object_type'] == 'polygon':
                                polygon = str(numpy.array(data["coords"]).tolist())

                            description = ''
                            transcription = ''
                            rid = ''

                            if data.get("attributes", ''):
                                if data["attributes"].get("RId", ''):
                                    rid = data["attributes"]["RId"]

                            if data.get("attributes", ''):
                                if data["attributes"].get(self.config_default["TAG_DESCRIBER"], ''):
                                    description = data["attributes"][self.config_default["TAG_DESCRIBER"]]

                            if data.get("attributes", ''):
                                if data["attributes"].get(self.config_default["TAG_TRANSCRIBER"], ''):
                                    transcription = data["attributes"][self.config_default["TAG_TRANSCRIBER"]]

                            csv_writer.writerow([image, obj['object_type'], rid, str(int(uplx)), str(int(uply)),
                                                 str(int(w)), str(int(h)), description, transcription, polygon])


            else:
                print("\tNothing to export")


def add_preview(image_list, db1: DBHandler, user, contributor_tag):
    # Add a bunch of images.
    # item_all = []

    db = DBHandler()
    db.db_load(db1.db_path, user)
    db.db_user = user

    try:
        et = ExifTool(r"app\bin\exiftool-12.52.exe", encoding='utf8')
        et.run()
    except OSError as err:
        print("\t\tStart running Exiftool failed")
        print("\t\tOS error:", err)

        return False

    for n, fn in enumerate(image_list):

        rel = os.path.relpath(fn[0].as_posix(), db1.db_path)
        new_path = os.path.normpath(os.path.join(db1.db_path, rel))
        image = image_loader(new_path)
        scaled = image.scaledToHeight(PREVIEW_HEIGHT)

        # item = PreviewModelData(fn[1], fn[0].as_posix(), fn[0].name, scaled, 0, 0, 0)
        # item_all.append(item)

        ba = QtCore.QByteArray()
        buff = QtCore.QBuffer(ba)
        buff.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        ok = scaled.save(buff, "JPG")
        img_width = image.width()
        img_height = image.height()
        if ok:
            pix_map_bytes = ba.data()
            db.db_store_blob(fn[1], pix_map_bytes, img_width, img_height)
        else:
            db.db_store_size(fn[1], img_width, img_height)
            print('\t\tCorrupt Image present. Scaling for Preview not possible')

        if et.running:
            exif_tags = et.execute_json(*["-struct", "-ImageRegion", fn[0].as_posix()])

            regions = exif_tags[0].get('XMP:ImageRegion', False)
            if regions:

                not_used_region = []
                for region in regions:

                    if region:
                        if region.get('Contributor', ''):
                            region[contributor_tag] = region.pop('Contributor')
                        object_type, data, user = parse_img_region(region, img_width, img_height)

                        db.db_store_object_imgregion(fn[1], object_type, data, user=user,
                                                     orig_img_region=region)
                        if data is None:
                            not_used_region.append(region)
                if len(not_used_region) > 0:
                    db.db_store_image_region(fn[1], orig_image_region=not_used_region)
        else:
            print('\t\tSeems Exiftool is not running')

    et.terminate()
    return True


def main():
    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

    # QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.Floor)
    freeze_support()
    app = QApplication()
    window = MainWindow()
    #  app.installEventFilter(window)
    app.setWindowIcon(QtGui.QIcon("app/icons/icon.png"))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
