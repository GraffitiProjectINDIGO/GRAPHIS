import sys
import traceback
import json
from pathlib import Path
import numpy
from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtWidgets import *
from PySide2.QtCore import Slot
from PySide2.QtGui import (QColor, Qt,  QPixmap)
import datetime

from exiftool import ExifTool

from app.preview_class import PreviewModel, PreviewDelegate
from app.var_classes import (software_version, Instructions, image_list_provided, PreviewModelData,
							 image_region_role, put_struct_to_dict_or_remove, put_text_to_dict_or_remove,
							 put_struc_tag, find_key_role, PREVIEW_HEIGHT, CONFIG_FILE, load_config)
from app.ui_main import Ui_MainWindow
from app.digitizerscene import DIGITIZERScene
from app.db_handler import DBHandler
from app.popup_user import POPUPUser
from app.meta_exif import parse_img_region
from app.meta_exif import meta_writer
from app.json_model import JsonModel


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
		super(Worker, self).__init__()
		self.fn = fn
		self.args = args
		self.kwargs = kwargs
		self.signals = WorkerSignal()

	@QtCore.Slot()
	def run(self):
		try:
			result = self.fn(*self.args, **self.kwargs, )
		except:
			traceback.print_exc()
			exec_type, value = sys.exc_info()[:2]
			self.signals.error.emit((exec_type, value, traceback.format_exc()))
		else:
			self.signals.result.emit(result)




class MainWindow(QMainWindow):

	def __init__(self):
		QMainWindow.__init__(self)

		# try to load config File
		self.config_success, self.config = load_config(CONFIG_FILE)
		self.ui = Ui_MainWindow()
		self.ui.setupUi(self)
		self.ui.label_version.setText(str(software_version))

		# ----------------------------------------------------------
		# Appearance STUFF
		# Window size ==> default size
		# start_size = QSize(1000, 1000)
		# self.resize(start_size)
		# self.setMinimumSize(start_size)
		# frame, shadow
		self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
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
			if event.type() == QtCore.QEvent.MouseButtonDblClick:
				self.maximize_restore()

			self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

		self.ui.frame_label_top_btns.mouseDoubleClickEvent = double_click_maximize_restore

		# --------------------------------------------------------------
		# move window
		self.dragPos = None

		def drag_window(event):
			# MOVE WINDOW
			if event.buttons() == Qt.LeftButton and not self.isMaximized():
				self.move(self.pos() + event.globalPos() - self.dragPos)
				self.dragPos = event.globalPos()
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
		self.thread_pool = QtCore.QThreadPool()

		self.ui.image_region_view.header().setSectionResizeMode(0, QHeaderView.Stretch)
		self.ui.image_region_view.setAlternatingRowColors(True)
		self.model_image_region = JsonModel()

		self.ui.image_region_view.setModel(self.model_image_region)

		# Redirect Logger
		stdout = OutputWrapper(self, True)
		stdout.outputWritten.connect(self.handle_output)
		stderr = OutputWrapper(self, False)
		stderr.outputWritten.connect(self.handle_output)

		self.action_menue1 = QAction("Create new database", self)
		self.action_menue2 = QAction("Load database", self)
		self.action_menue3 = QAction("Add image folder", self)
		self.action_menue4 = QAction("Save BOX to CSV file", self)
		self.action_menue5 = QAction("Save image regions to files", self)

		self.alignMenu = QMenu(self)
		self.alignMenu.addAction(self.action_menue1)
		self.alignMenu.addAction(self.action_menue2)
		self.alignMenu.addSeparator()
		self.alignMenu.addAction(self.action_menue3)
		self.alignMenu.addSeparator()
		self.alignMenu.addAction(self.action_menue4)
		self.alignMenu.addAction(self.action_menue5)
		self.alignMenu.setStyleSheet("background: rgb(130, 130, 130);\n")

		self.ui.toolButton.setMenu(self.alignMenu)

		# ----------------------------------------------------------
		# VARIABLES
		self.color_rectangle = QColor(self.config["GEOMETRIE-COLOURS"]["COLOR_RECTANGLE_START"])
		self.color_polygon = QColor(self.config["GEOMETRIE-COLOURS"]["COLOR_POLYGON_START"])
		self.color_circle = QColor(self.config["GEOMETRIE-COLOURS"]["COLOR_CIRCLE_START"])

		self.ui.btn_color_circle.set_color(self.color_circle)
		self.ui.btn_color_rectangle.set_color(self.color_rectangle)
		self.ui.btn_color_polygon.set_color(self.color_polygon)

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
		self.delegate.rectangle_color = QColor(self.config["GEOMETRIE-COLOURS"]["COLOR_RECTANGLE_START"])
		self.delegate.polygon_color = QColor(self.config["GEOMETRIE-COLOURS"]["COLOR_POLYGON_START"])
		self.delegate.circle_color = QColor(self.config["GEOMETRIE-COLOURS"]["COLOR_CIRCLE_START"])
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

		# ------------------------------------------------------------------------------------------------------------
		# EVENTS #
		# Menue Action Items
		self.action_menue1.triggered.connect(self.create_new_db)
		self.action_menue2.triggered.connect(self.load_existing_db)
		self.action_menue3.triggered.connect(self.load_input_image_folder)
		self.action_menue4.triggered.connect(self.save_csv)
		self.action_menue5.triggered.connect(self.save_image_regions)

		# Connect double on image to load the image
		self.ui.table_preview.doubleClicked.connect(self.scene_load_image)

		# Geometry Creation
		self.ui.btn_create_rectangle.clicked.connect(lambda: self.set_instruction('create_rectangle'))
		self.ui.btn_create_polygon.clicked.connect(lambda: self.set_instruction('create_polygon'))
		self.ui.btn_create_circle.clicked.connect(lambda: self.set_instruction('create_circle'))
		self.ui.btn_geometry_move.clicked.connect(lambda: self.set_instruction('move_geometry'))
		self.ui.btn_geometry_resize.clicked.connect(lambda: self.set_instruction('change_geometry'))

		# self.ui.text_rectangle_attribute.focus_out.connect(self.save_data)

		self.digitizer_scene.object_att.connect(self.load_data)
		self.digitizer_scene.object_add.connect(self.add_data)
		self.digitizer_scene.change_object.connect(self.change_finetuner)
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
		if success:
			print('Finished successfully writing EXIF')

		self.ui.waiting_spinner.stop()
		self.db.is_locked = False

	@Slot(bool)
	def thread_output(self, success: bool):

		if success:
			self.clean_all_views_and_tables(db_save=True)
			self.loader_all()

		self.ui.waiting_spinner.stop()
		self.db.is_locked = False

	# ----------------------------------------------------------
	# Functions

	def maximize_restore(self):

		if not self.isMaximized():
			self.showMaximized()
			self.ui.horizontalLayout.setContentsMargins(0, 0, 0, 0)
			self.ui.btn_maximize_restore.setToolTip("Restore")
			self.ui.btn_maximize_restore.setIcon(QtGui.QIcon(u":/icons/icons/cil-window-restore.png"))
			self.ui.frame_top_btns.setStyleSheet("background-color: rgb(27, 29, 35)")
			self.ui.frame_size_grip.hide()
		else:
			self.showNormal()
			self.resize(self.width() + 1, self.height() + 1)
			self.ui.horizontalLayout.setContentsMargins(10, 10, 10, 10)
			self.ui.btn_maximize_restore.setToolTip("Maximize")
			self.ui.btn_maximize_restore.setIcon(QtGui.QIcon(u":/icons/icons/cil-window-maximize.png"))
			self.ui.frame_top_btns.setStyleSheet("background-color: rgba(27, 29, 35, 200)")
			self.ui.frame_size_grip.show()

	# def eventFilter(self, source, event):
	#	 return False

	# EVENT - KEY PRESSED
	# def keyPressEvent(self, event):
	#    super(MainWindow, self).keyPressEvent(event)
	# EVENT - MOUSE CLICK
	def mousePressEvent(self, event):
		self.dragPos = event.globalPos()
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
		print('Welcome ' + self.user.upper() + '. Enjoy working')
		if not self.config_success:
			print('Config file parsing failed. Please create or fix file "graffilabel.conf" ', file=sys.stderr)
		self.show()

	def handle_output(self, text, stdout):
		self.ui.info_screen.moveCursor(QtGui.QTextCursor.End)
		self.ui.info_screen.setTextColor(QColor(255, 255, 255) if stdout else QColor(255, 0, 0))
		self.ui.info_screen.insertPlainText(text)
		self.ui.info_screen.setTextColor(QColor(255, 255, 255))

	def combo_change(self):
		new_name = self.sender().currentText()
		for x in image_region_role:
			if x[0] == new_name:
				new_id = x[1]
		self.ui.txt_rrole_ident.setPlainText(new_id)

	def scene_load_image(self, index):

		self.clear_entries()
		self.digitizer_scene.current_instruction = Instructions.No_Instruction
		self.digitizer_scene.instruction_active = False
		self.digitizer_scene.clear()

		self.model_image_region.clear()

		self.current_item = None

		# set icon of hiding for objects
		# self.ui.radio_show_polygon.setChecked(False)
		# self.ui.btn.setChecked(False)

		self.digitizer_scene.open_image(index.data(Qt.UserRole))
		self.ui.view_digizizer.fitInView(self.digitizer_scene.image_item, QtCore.Qt.KeepAspectRatio)
		self.digitizer_scene.image_id_db = index.data(Qt.UserRole + 1)
		self.ui.image_name.setText(index.data(Qt.ToolTipRole))
		self.current_image = {'id': index.data(Qt.UserRole + 1) - 1, 'name': index.data(Qt.ToolTipRole)}
		data = self.db.db_load_objects_image(index.data(Qt.UserRole + 1))

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

	def change_visibility(self, objects_type):
		self.digitizer_scene.hide_item(objects_type)
		self.current_item = None

	# self.change_color_items(lambda: self.color_rectangle)
	# self.change_color_polygon(self.color_polygon)

	@Slot(object)
	def change_color(self, color, object_type):

		if object_type == "circle":
			self.color_circle = color
			self.digitizer_scene.color_circle = color
			self.delegate.circle_color = color
		elif object_type == "rectangle":
			self.color_rectangle = color
			self.digitizer_scene.color_rectangle = color
			self.delegate.rectangle_color = color
		elif object_type == "polygon":
			self.color_polygon = color
			self.digitizer_scene.color_polygon = color
			self.delegate.polygon_color = color

		self.digitizer_scene.change_color(object_type, color)

	@Slot()
	def save_data(self):

		if self.current_item is None:
			self.clear_entries()

		if self.digitizer_scene.image_item is not None:
			if self.current_item is not None:

				data = self.current_item['data']['attributes']

				data = put_text_to_dict_or_remove(data, 'RId', self.ui.txt_rid.toPlainText())
				data = put_text_to_dict_or_remove(data, 'Name', self.ui.txt_rname.toPlainText())

				data = put_struct_to_dict_or_remove(data, 'RCtype', self.ui.txt_rctype_indent.toPlainText(),
													self.ui.txt_rctype_name.toPlainText())

				data = put_struct_to_dict_or_remove(data, 'RRole', self.ui.txt_rrole_ident.toPlainText(),
													self.ui.comboBox_region_role.currentText())

				data = put_struc_tag(data, self.config["CONTRIBUTOR"]["CONTRIBUTOR_TAG"],
											   self.ui.contr_creator_role.toPlainText(),
											   self.ui.contr_creator_ident.toPlainText(),
											   self.ui.contr_creator_name.toPlainText())
				data = put_struc_tag(data, self.config["CONTRIBUTOR"]["CONTRIBUTOR_TAG"],
											   self.ui.contr_tuner_role.toPlainText(),
											   self.ui.contr_tuner_ident.toPlainText(),
											   self.ui.contr_tuner_name.toPlainText())

				describer_text = self.ui.xmp_dc.toPlainText()
				descr_ident = self.ui.txt_user_indent.toPlainText()
				descr_name = self.ui.txt_user_name.toPlainText()

				if not data.get(self.config["DEFAULT"]["EXTRA_STRING_TAG"], ''):

					# If no describer text is written set indent and name to empty
					# then the put_struc_tag will delete it
					if describer_text:
						data = put_struc_tag(data, self.config["CONTRIBUTOR"]["CONTRIBUTOR_TAG"],
										 self.config["CONTRIBUTOR"]["DESCRIBER_ROLE"],
										 descr_ident,
										 descr_name)
				else:
					if describer_text != data[self.config["DEFAULT"]["EXTRA_STRING_TAG"]]:
						if not describer_text:
							descr_ident = ''
							descr_name = ''
						data = put_struc_tag(data, self.config["CONTRIBUTOR"]["CONTRIBUTOR_TAG"],
											 self.ui.contr_describer_role.toPlainText(),
											 descr_ident,
											 descr_name)

				data = put_text_to_dict_or_remove(data, self.config["DEFAULT"]["EXTRA_STRING_TAG"], self.ui.xmp_dc.toPlainText())

				self.digitizer_scene.set_tooltip(self.current_item['id'], data['RId'])
				self.current_item['data']['attributes'] = data
				self.model_image_region.load(data)
				self.db.update_object(obj_id=self.current_item['id'], data=self.current_item['data'])

				self.change_color(self.color_rectangle, 'rectangle')
				self.change_color(self.color_polygon, 'polygon')
				self.change_color(self.color_circle, 'circle')
				self.current_item = None
				self.clear_entries()

	def clear_entries(self):
		self.current_item = None
		self.digitizer_scene.instruction_active = False
		self.digitizer_scene.current_instruction = Instructions.No_Instruction
		self.model_image_region.clear()
		self.ui.txt_rid.setPlainText('')
		self.ui.txt_rname.setPlainText('')

		self.ui.contr_creator_name.setPlainText('')
		self.ui.contr_creator_ident.setPlainText('')
		self.ui.contr_creator_role.setPlainText('')

		self.ui.contr_tuner_name.setPlainText('')
		self.ui.contr_tuner_ident.setPlainText('')
		self.ui.contr_tuner_role.setPlainText('')

		self.ui.contr_describer_name.setPlainText('')
		self.ui.contr_describer_ident.setPlainText('')
		self.ui.contr_describer_role.setPlainText('')

		self.ui.txt_rctype_name.setPlainText('')
		self.ui.txt_rctype_indent.setPlainText('')

		self.ui.xmp_dc.setPlainText('')

	@Slot(int)
	def change_finetuner(self, object_id):

		self.clear_entries()
		data = self.db.db_load_object(object_id)
		jdata = json.loads(data['data'])

		jdata['attributes'] = put_struc_tag(jdata['attributes'],
											tag=self.config["CONTRIBUTOR"]["CONTRIBUTOR_TAG"],
							  				role=self.config["CONTRIBUTOR"]["FINE_TUNER_ROLE"],
							  				indentifier=self.ui.txt_user_indent.toPlainText(),
							  				name=self.ui.txt_user_name.toPlainText())

		self.current_item = {'id': object_id, 'data': jdata, 'object_type': data['object_type']}
		self.db.update_object(obj_id=object_id, data=self.current_item['data'])

		self.change_color(self.color_rectangle, 'rectangle')
		self.change_color(self.color_polygon, 'polygon')
		self.change_color(self.color_circle, 'circle')
		self.current_item = None
		self.clear_entries()

	@Slot(int)
	def load_data(self, object_id):
		self.clear_entries()
		data = self.db.db_load_object(object_id)

		jdata = json.loads(data['data'])

		self.model_image_region.load(jdata['attributes'])

		self.current_item = {'id': object_id, 'data': jdata, 'object_type': data['object_type']}

		self.parse_show_data(self.current_item['data']['attributes'])

	@Slot(int)
	def add_data(self, object_id):
		self.clear_entries()
		data = self.db.db_load_object(object_id)
		jdata = json.loads(data['data'])

		image = Path(self.current_image['name'])

		self.model_image_region.load(jdata['attributes'])
		img_region_dict = {}
		if data['object_type'] == 'rectangle':
			img_region_dict['RCtype'] = [{'Identifier': [self.config["GEOMETRIE-RCTYPES"]["RCTYPE_RECTANGLE_IDENTIFIER"]],
										  'Name': self.config["GEOMETRIE-RCTYPES"]["RCTYPE_RECTANGLE_NAME"]}]


			self.ui.comboBox_region_role.setCurrentText("area of interest")
			self.ui.txt_rrole_ident.setPlainText("http://cv.iptc.org/newscodes/imageregionrole/areaOfInterest")
		elif data['object_type'] == 'polygon':

			img_region_dict['RCtype'] = [{'Identifier': [self.config["GEOMETRIE-RCTYPES"]["RCTYPE_POLYGON_IDENTIFIER"]],
										  'Name': self.config["GEOMETRIE-RCTYPES"]["RCTYPE_POLYGON_NAME"]}]
			self.ui.comboBox_region_role.setCurrentText("area of interest")
			self.ui.txt_rrole_ident.setPlainText("http://cv.iptc.org/newscodes/imageregionrole/areaOfInterest")

		else:
			img_region_dict['RCtype'] = [{'Identifier': [self.config["GEOMETRIE-RCTYPES"]["RCTYPE_CIRCLE_IDENTIFIER"]],
										  'Name': self.config["GEOMETRIE-RCTYPES"]["RCTYPE_CIRCLE_NAME"]}]
			self.ui.comboBox_region_role.setCurrentText("main subject area")
			self.ui.txt_rrole_ident.setPlainText("http://cv.iptc.org/newscodes/imageregionrole/mainSubjectArea")

		# RC type

		# RId
		rid = image.stem + '_' + data['object_type'] + '_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
		img_region_dict = put_text_to_dict_or_remove(img_region_dict, 'RId', rid)

		# Role
		img_region_dict = put_struct_to_dict_or_remove(img_region_dict, tag='RRole',
													   indentifier=self.ui.txt_rrole_ident.toPlainText(),
													   name=self.ui.comboBox_region_role.currentText())

		# Region Creator
		img_region_dict = put_struc_tag(img_region_dict, self.config["CONTRIBUTOR"]["CONTRIBUTOR_TAG"],
										self.config["CONTRIBUTOR"]["REGION_CREATOR_ROLE"],
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
		self.parse_show_data(self.current_item['data']['attributes'])
		self.model_image_region.load(self.current_item['data']['attributes'])


	def parse_show_data(self, dict_item: dict):

		region_id = dict_item.get("RId", '')
		name = dict_item.get("Name", '')

		self.ui.txt_rid.setPlainText(region_id)
		self.ui.txt_rname.setPlainText(name)

		dict_role = dict_item.get('RRole', '')
		if dict_role:
			new_id = image_region_role[0][1]
			new_name = image_region_role[0][0]
			for x in image_region_role:
				if x[0] == dict_role[0]['Name']:
					new_id = x[1]
					new_name = x[0]

			self.ui.comboBox_region_role.setCurrentText(new_name)
			self.ui.txt_rrole_ident.setPlainText(new_id)

		dict_contr = dict_item.get(self.config["CONTRIBUTOR"]["CONTRIBUTOR_TAG"], '')
		if dict_contr:

			success, idx = find_key_role(dict_item, self.config["CONTRIBUTOR"]["CONTRIBUTOR_TAG"],
										 self.config["CONTRIBUTOR"]["REGION_CREATOR_ROLE"])
			if success:
				self.ui.contr_creator_name.setPlainText(dict_contr[idx]['Name'])
				self.ui.contr_creator_ident.setPlainText(dict_contr[idx]['Identifier'][0])
				self.ui.contr_creator_role.setPlainText(dict_contr[idx]['Role'][0])

			success, idx = find_key_role(dict_item, self.config["CONTRIBUTOR"]["CONTRIBUTOR_TAG"], self.config["CONTRIBUTOR"]["FINE_TUNER_ROLE"])
			if success:
				self.ui.contr_tuner_name.setPlainText(dict_contr[idx]['Name'])
				self.ui.contr_tuner_ident.setPlainText(dict_contr[idx]['Identifier'][0])
				self.ui.contr_tuner_role.setPlainText(dict_contr[idx]['Role'][0])

			success, idx = find_key_role(dict_item, self.config["CONTRIBUTOR"]["CONTRIBUTOR_TAG"], self.config["CONTRIBUTOR"]["DESCRIBER_ROLE"])
			if success:
				self.ui.contr_describer_name.setPlainText(dict_contr[idx]['Name'])
				self.ui.contr_describer_ident.setPlainText(dict_contr[idx]['Identifier'][0])
				self.ui.contr_describer_role.setPlainText(dict_contr[idx]['Role'][0])

		dict_rctype = dict_item.get('RCtype', '')
		if dict_rctype:
			self.ui.txt_rctype_name.setPlainText(dict_rctype[0]['Name'])
			self.ui.txt_rctype_indent.setPlainText(dict_rctype[0]['Identifier'][0])

		xmp_dc = dict_item.get(self.config["DEFAULT"]["EXTRA_STRING_TAG"], '')
		self.ui.xmp_dc.setPlainText(xmp_dc)

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
		else:
			print("Database is locked")

	def set_instruction(self, action: str):
		self.clear_entries()
		self.model_image_region.clear()

		if not self.digitizer_scene.instruction_active:
			if action == 'create_rectangle':
				self.current_item = None
				self.digitizer_scene.current_instruction = Instructions.Rectangle_Instruction
			elif action == 'create_polygon':
				self.current_item = None
				self.digitizer_scene.current_instruction = Instructions.Polygon_Instruction
			elif action == 'create_circle':
				self.digitizer_scene.current_instruction = Instructions.Circle_Instruction
			elif action == 'move_geometry':
				self.digitizer_scene.current_instruction = Instructions.Move_Instruction
			elif action == 'change_geometry':
				self.digitizer_scene.current_instruction = Instructions.Change_Instruction

			else:
				return

	def clean_all_views_and_tables(self, db_save=False):
		self.digitizer_scene.clear()
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
			db_path, _ = QtWidgets.QFileDialog.getOpenFileName(caption="Load Database",
															   dir='.', filter='SQLITE Files (*.sqlite)')
			# clear scene GIS and digitizer
			self.clean_all_views_and_tables()

			if db_path:
				self.db.db_load(Path(db_path), self.user)
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
				self.image_list.append([Path(x['path']), x['id']])
				pixmap = QPixmap()
				pixmap.loadFromData(x['preview'], "JPG")
				# image = QImage(pixmap)
				item = PreviewModelData(x['id'], Path(x['path']).as_posix(), Path(x['path']).name, pixmap,
										x['polygon_count'], x['rectangle_count'], x['circle_count'])
				self.model.previews.append(item)
				self.model.layoutChanged.emit()
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
			db_path, _ = QtWidgets.QFileDialog.getSaveFileName(caption="Create Database",
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

	def load_input_image_folder(self):

		if self.db.db_is_set and not self.db.is_locked:
			self.db.is_locked = True
			image_path, _ = QtWidgets.QFileDialog.getOpenFileName(caption="Click on one Image")
			if image_path:
				print("Read Image Folder")
				image_path = Path(image_path)
				if image_path.suffix.lower() not in image_list_provided:
					self.db.is_locked = False
					print("Image Format not provided")
					return
				image_path_parent = image_path.parent
				# self.image_list=[file for file in image_path_parent.iterdir() if file.suffix in image_path.suffix]
				added_images = []
				for image in image_path_parent.iterdir():
					if image.suffix:
						if image.suffix in image_path.suffix:

							image_id = self.db.db_store_image(image)
							if image_id >= 0:
								self.image_list.append([image, image_id])
								added_images.append([image, image_id])
							else:
								print("Image could not be stored in DB")

				len_image_list = len(added_images)
				self.len_image_list = len_image_list

				print("\tFound Nr. of image: ", len_image_list)
				# self.ui.lbl_image_nr.setText(str(len_image_list))

				if len_image_list > 0:

					worker = Worker(add_preview, added_images, self.db, self.user, self.config)
					worker.signals.result.connect(self.thread_output)
					self.ui.waiting_spinner.start()
					self.thread_pool.start(worker)
				else:
					self.db.is_locked = False
			else:
				self.db.is_locked = False

	def save_image_regions(self):

		if self.db.db_is_set and not self.db.is_locked:
			self.db.is_locked = True

			worker = Worker(meta_writer, self.db, self.user)
			worker.signals.result.connect(self.thread_output_exif)
			self.ui.waiting_spinner.start()
			self.thread_pool.start(worker)

	def save_csv(self):
		if self.db.db_is_set:
			objs = self.db.db_load_objects_all()

			if objs:
				image_path, _ = QtWidgets.QFileDialog.getSaveFileName(caption="Export rectangle CSV",
																	  filter='CSV (*.csv)')
				if image_path:
					with open(image_path, 'w') as fid:
						fid.write("image,type,RId,UpperLeftX,UpperLeftY,Width,Height,Description\n")
						for obj in objs:

							image = obj['image_name']
							data = json.loads(obj['data'])
							np_coords = numpy.array(data["coords"])
							if obj['object_type']=='circle':

								uplx = np_coords[0] - np_coords[2]
								uply = np_coords[1] - np_coords[2]
								w = np_coords[0] + np_coords[2]
								h = np_coords[1] + np_coords[2]

							else:
								min_rec = np_coords.min(axis=0)
								max_rec = np_coords.max(axis=0)
								uplx = min_rec[0]
								uply = max_rec[1]
								w = max_rec[0] - min_rec[0]
								h = max_rec[1] - min_rec[1]

							description = ''
							rid = ''

							if data.get("attributes", ''):
								if data["attributes"].get("RId", ''):
									rid = data["attributes"]["RId"].replace(',', '_')

							if data.get("attributes", ''):
								if data["attributes"].get(self.config["DEFAULT"]["EXTRA_STRING_TAG"], ''):
									description = data["attributes"][self.config["DEFAULT"]["EXTRA_STRING_TAG"]].replace(',', '_')

							fid.write(",".join([image, obj['object_type'], rid, str(int(uplx)), str(int(uply)),
												str(int(w)), str(int(h)), description]) + "\n")

			else:
				print("\tNothing to export")


def add_preview(image_list, db1: DBHandler, user, config_dict):
	# Add a bunch of images.
	item_all = []

	db = DBHandler()
	db.db_load(db1.db_path, user)
	db.db_user = user

	try:
		et = ExifTool(r"app\bin\exiftool-12.52.exe")
		et.run()
		print("Start running Exiftool")
	except OSError as err:
		print("\tStart running Exiftool failed")
		print("\tOS error:", err)

		return False

	for n, fn in enumerate(image_list):
		image = QPixmap(fn[0].as_posix())
		scaled = image.scaledToHeight(PREVIEW_HEIGHT)

		item = PreviewModelData(fn[1], fn[0].as_posix(), fn[0].name, scaled, 0, 0, 0)
		item_all.append(item)

		ba = QtCore.QByteArray()
		buff = QtCore.QBuffer(ba)
		buff.open(QtCore.QIODevice.WriteOnly)
		ok = scaled.save(buff, "JPG")
		img_width = image.width()
		img_height = image.height()
		if ok:
			pix_map_bytes = ba.data()
			db.db_store_blob(fn[1], pix_map_bytes, img_width, img_height)
		else:
			db.db_store_size(fn[1], img_width, img_height)
			print('Corrupt Image present. Scaling for Preview not possible')

		if et.running:
			exif_tags = et.execute_json(*["-struct", "-ImageRegion", fn[0].as_posix()])

			regions = exif_tags[0].get('XMP:ImageRegion', False)
			if regions:

				not_used_region = []
				for region in regions:

					if region:
						if region.get('Contributor', ''):
							region[config_dict["CONTRIBUTOR"]["CONTRIBUTOR_TAG"]] = region.pop('Contributor')
						object_type, data, user = parse_img_region(region, img_width, img_height)

						db.db_store_object_imgregion(fn[1], object_type, data, user=user,
													 orig_img_region=region)
						if data is None:
							not_used_region.append(region)
				if len(not_used_region) > 0:
					db.db_store_image_region(fn[1], orig_image_region=not_used_region)
		else:
			print('\tSeems Exiftool is not running')

	et.terminate()
	return True


if __name__ == "__main__":
	QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
	app = QApplication()
	window = MainWindow()
	app.setWindowIcon(QtGui.QIcon("app/icons/top_icon.png"))
	sys.exit(app.exec_())
