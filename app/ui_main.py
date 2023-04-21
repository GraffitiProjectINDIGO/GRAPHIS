# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'gui_main.ui'
##
## Created by: Qt User Interface Compiler version 5.15.8
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *  # type: ignore
from PySide2.QtGui import *  # type: ignore
from PySide2.QtWidgets import *  # type: ignore

from app.digitizerview import DIGITIZERView
from app.spinningwaiter import SPINNINGWaiter
from app.colorbutton import COLORButton

import files_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1125, 1000)
        MainWindow.setMinimumSize(QSize(1125, 1000))
        palette = QPalette()
        brush = QBrush(QColor(255, 255, 255, 255))
        brush.setStyle(Qt.SolidPattern)
        palette.setBrush(QPalette.Active, QPalette.WindowText, brush)
        brush1 = QBrush(QColor(0, 0, 0, 0))
        brush1.setStyle(Qt.SolidPattern)
        palette.setBrush(QPalette.Active, QPalette.Button, brush1)
        brush2 = QBrush(QColor(66, 73, 90, 255))
        brush2.setStyle(Qt.SolidPattern)
        palette.setBrush(QPalette.Active, QPalette.Light, brush2)
        brush3 = QBrush(QColor(55, 61, 75, 255))
        brush3.setStyle(Qt.SolidPattern)
        palette.setBrush(QPalette.Active, QPalette.Midlight, brush3)
        brush4 = QBrush(QColor(22, 24, 30, 255))
        brush4.setStyle(Qt.SolidPattern)
        palette.setBrush(QPalette.Active, QPalette.Dark, brush4)
        brush5 = QBrush(QColor(29, 32, 40, 255))
        brush5.setStyle(Qt.SolidPattern)
        palette.setBrush(QPalette.Active, QPalette.Mid, brush5)
        brush6 = QBrush(QColor(210, 210, 210, 255))
        brush6.setStyle(Qt.SolidPattern)
        palette.setBrush(QPalette.Active, QPalette.Text, brush6)
        palette.setBrush(QPalette.Active, QPalette.BrightText, brush)
        palette.setBrush(QPalette.Active, QPalette.ButtonText, brush)
        palette.setBrush(QPalette.Active, QPalette.Base, brush1)
        palette.setBrush(QPalette.Active, QPalette.Window, brush1)
        brush7 = QBrush(QColor(0, 0, 0, 255))
        brush7.setStyle(Qt.SolidPattern)
        palette.setBrush(QPalette.Active, QPalette.Shadow, brush7)
        brush8 = QBrush(QColor(85, 170, 255, 255))
        brush8.setStyle(Qt.SolidPattern)
        palette.setBrush(QPalette.Active, QPalette.Highlight, brush8)
        palette.setBrush(QPalette.Active, QPalette.Link, brush8)
        brush9 = QBrush(QColor(255, 0, 127, 255))
        brush9.setStyle(Qt.SolidPattern)
        palette.setBrush(QPalette.Active, QPalette.LinkVisited, brush9)
        palette.setBrush(QPalette.Active, QPalette.AlternateBase, brush4)
        brush10 = QBrush(QColor(44, 49, 60, 255))
        brush10.setStyle(Qt.SolidPattern)
        palette.setBrush(QPalette.Active, QPalette.ToolTipBase, brush10)
        palette.setBrush(QPalette.Active, QPalette.ToolTipText, brush6)
        palette.setBrush(QPalette.Inactive, QPalette.WindowText, brush)
        palette.setBrush(QPalette.Inactive, QPalette.Button, brush1)
        palette.setBrush(QPalette.Inactive, QPalette.Light, brush2)
        palette.setBrush(QPalette.Inactive, QPalette.Midlight, brush3)
        palette.setBrush(QPalette.Inactive, QPalette.Dark, brush4)
        palette.setBrush(QPalette.Inactive, QPalette.Mid, brush5)
        palette.setBrush(QPalette.Inactive, QPalette.Text, brush6)
        palette.setBrush(QPalette.Inactive, QPalette.BrightText, brush)
        palette.setBrush(QPalette.Inactive, QPalette.ButtonText, brush)
        palette.setBrush(QPalette.Inactive, QPalette.Base, brush1)
        palette.setBrush(QPalette.Inactive, QPalette.Window, brush1)
        palette.setBrush(QPalette.Inactive, QPalette.Shadow, brush7)
        palette.setBrush(QPalette.Inactive, QPalette.Highlight, brush8)
        palette.setBrush(QPalette.Inactive, QPalette.Link, brush8)
        palette.setBrush(QPalette.Inactive, QPalette.LinkVisited, brush9)
        palette.setBrush(QPalette.Inactive, QPalette.AlternateBase, brush4)
        palette.setBrush(QPalette.Inactive, QPalette.ToolTipBase, brush10)
        palette.setBrush(QPalette.Inactive, QPalette.ToolTipText, brush6)
        palette.setBrush(QPalette.Disabled, QPalette.WindowText, brush4)
        palette.setBrush(QPalette.Disabled, QPalette.Button, brush1)
        palette.setBrush(QPalette.Disabled, QPalette.Light, brush2)
        palette.setBrush(QPalette.Disabled, QPalette.Midlight, brush3)
        palette.setBrush(QPalette.Disabled, QPalette.Dark, brush4)
        palette.setBrush(QPalette.Disabled, QPalette.Mid, brush5)
        palette.setBrush(QPalette.Disabled, QPalette.Text, brush4)
        palette.setBrush(QPalette.Disabled, QPalette.BrightText, brush)
        palette.setBrush(QPalette.Disabled, QPalette.ButtonText, brush4)
        palette.setBrush(QPalette.Disabled, QPalette.Base, brush1)
        palette.setBrush(QPalette.Disabled, QPalette.Window, brush1)
        palette.setBrush(QPalette.Disabled, QPalette.Shadow, brush7)
        brush11 = QBrush(QColor(51, 153, 255, 255))
        brush11.setStyle(Qt.SolidPattern)
        palette.setBrush(QPalette.Disabled, QPalette.Highlight, brush11)
        palette.setBrush(QPalette.Disabled, QPalette.Link, brush8)
        palette.setBrush(QPalette.Disabled, QPalette.LinkVisited, brush9)
        palette.setBrush(QPalette.Disabled, QPalette.AlternateBase, brush10)
        palette.setBrush(QPalette.Disabled, QPalette.ToolTipBase, brush10)
        palette.setBrush(QPalette.Disabled, QPalette.ToolTipText, brush6)
        MainWindow.setPalette(palette)
        font = QFont()
        font.setFamily(u"Segoe UI")
        font.setPointSize(10)
        MainWindow.setFont(font)
        MainWindow.setStyleSheet(u"QMainWindow {background: transparent; }\n"
"QToolTip {\n"
"	color: #ffffff;\n"
"	background-color: rgba(27, 29, 35, 160);\n"
"	border: 1px solid rgb(40, 40, 40);\n"
"	border-radius: 2px;\n"
"}")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.centralwidget.setMinimumSize(QSize(1120, 1000))
        self.centralwidget.setStyleSheet(u"background: transparent;\n"
"color: rgb(210, 210, 210);")
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setSpacing(0)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.frame_main = QFrame(self.centralwidget)
        self.frame_main.setObjectName(u"frame_main")
        self.frame_main.setMinimumSize(QSize(1120, 0))
        self.frame_main.setStyleSheet(u"/* LINE EDIT */\n"
"QLineEdit {\n"
"	background-color: rgb(27, 29, 35);\n"
"	border-radius: 5px;\n"
"	border: 2px solid rgb(27, 29, 35);\n"
"	padding-left: 10px;\n"
"}\n"
"QLineEdit:hover {\n"
"	border: 2px solid rgb(64, 71, 88);\n"
"}\n"
"QLineEdit:focus {\n"
"	border: 2px solid rgb(91, 101, 124);\n"
"}\n"
"\n"
"/* SCROLL BARS */\n"
"QScrollBar:horizontal {\n"
"    border: none;\n"
"    background: rgb(52, 59, 72);\n"
"    height: 14px;\n"
"    margin: 0px 21px 0 21px;\n"
"	border-radius: 0px;\n"
"}\n"
"QScrollBar::handle:horizontal {\n"
"	background: rgb(178, 186, 87);\n"
"    min-width: 25px;\n"
"	border-radius: 7px\n"
"}\n"
"QScrollBar::add-line:horizontal {\n"
"    border: none;\n"
"    background: rgb(55, 63, 77);\n"
"    width: 20px;\n"
"	border-top-right-radius: 7px;\n"
"    border-bottom-right-radius: 7px;\n"
"    subcontrol-position: right;\n"
"    subcontrol-origin: margin;\n"
"}\n"
"QScrollBar::sub-line:horizontal {\n"
"    border: none;\n"
"    background: rgb(55, 63, 77);\n"
"    width: 20px;\n"
""
                        "	border-top-left-radius: 7px;\n"
"    border-bottom-left-radius: 7px;\n"
"    subcontrol-position: left;\n"
"    subcontrol-origin: margin;\n"
"}\n"
"QScrollBar::up-arrow:horizontal, QScrollBar::down-arrow:horizontal\n"
"{\n"
"     background: none;\n"
"}\n"
"QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal\n"
"{\n"
"     background: none;\n"
"}\n"
" QScrollBar:vertical {\n"
"	border: none;\n"
"    background: rgb(52, 59, 72);\n"
"    width: 14px;\n"
"    margin: 21px 0 21px 0;\n"
"	border-radius: 0px;\n"
" }\n"
" QScrollBar::handle:vertical {	\n"
"	background: rgb(178, 186, 87);\n"
"    min-height: 25px;\n"
"	border-radius: 7px\n"
" }\n"
" QScrollBar::add-line:vertical {\n"
"     border: none;\n"
"    background: rgb(55, 63, 77);\n"
"     height: 20px;\n"
"	border-bottom-left-radius: 7px;\n"
"    border-bottom-right-radius: 7px;\n"
"     subcontrol-position: bottom;\n"
"     subcontrol-origin: margin;\n"
" }\n"
" QScrollBar::sub-line:vertical {\n"
"	border: none;\n"
"    background: rgb(55, 63"
                        ", 77);\n"
"     height: 20px;\n"
"	border-top-left-radius: 7px;\n"
"    border-top-right-radius: 7px;\n"
"     subcontrol-position: top;\n"
"     subcontrol-origin: margin;\n"
" }\n"
" QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {\n"
"     background: none;\n"
" }\n"
"\n"
" QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {\n"
"     background: none;\n"
" }\n"
"\n"
"/* CHECKBOX */\n"
"QCheckBox::indicator {\n"
"    border: 3px solid rgb(52, 59, 72);\n"
"	width: 15px;\n"
"	height: 15px;\n"
"	border-radius: 10px;\n"
"    background: rgb(44, 49, 60);\n"
"}\n"
"QCheckBox::indicator:hover {\n"
"    border: 3px solid rgb(58, 66, 81);\n"
"}\n"
"QCheckBox::indicator:checked {\n"
"    background: 3px solid rgb(52, 59, 72);\n"
"	border: 3px solid rgb(52, 59, 72);	\n"
"}\n"
"\n"
"/* RADIO BUTTON */\n"
"QRadioButton::indicator {\n"
"    border: 3px solid rgb(52, 59, 72);\n"
"	width: 15px;\n"
"	height: 15px;\n"
"	border-radius: 10px;\n"
"    background: rgb(44, 49, 60);\n"
"}\n"
"QRadioButton"
                        "::indicator:hover {\n"
"    border: 3px solid rgb(58, 66, 81);\n"
"}\n"
"QRadioButton::indicator:checked {\n"
"    background: 3px solid rgb(94, 106, 130);\n"
"	border: 3px solid rgb(52, 59, 72);	\n"
"}\n"
"\n"
"/* COMBOBOX */\n"
"QComboBox{\n"
"	background-color: rgb(27, 29, 35);\n"
"	border-radius: 5px;\n"
"	border: 2px solid rgb(27, 29, 35);\n"
"	padding: 5px;\n"
"	padding-left: 10px;\n"
"}\n"
"QComboBox:hover{\n"
"	border: 2px solid rgb(64, 71, 88);\n"
"}\n"
"QComboBox::drop-down {\n"
"	subcontrol-origin: padding;\n"
"	subcontrol-position: top right;\n"
"	width: 25px; \n"
"	border-left-width: 3px;\n"
"	border-left-color: rgba(39, 44, 54, 150);\n"
"	border-left-style: solid;\n"
"	border-top-right-radius: 3px;\n"
"	border-bottom-right-radius: 3px;	\n"
"	background-image: url(:/icons/icons/cil-arrow-bottom.png);\n"
"	background-position: center;\n"
"	background-repeat: no-reperat;\n"
" }\n"
"QComboBox QAbstractItemView {\n"
"	color: rgb(178, 186, 87);	\n"
"	background-color: rgb(27, 29, 35);\n"
"	padding: 10p"
                        "x;\n"
"	selection-background-color: rgb(39, 44, 54);\n"
"}\n"
"\n"
"/* SLIDERS */\n"
"QSlider::groove:horizontal {\n"
"    border-radius: 9px;\n"
"    height: 18px;\n"
"	margin: 0px;\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QSlider::groove:horizontal:hover {\n"
"	background-color: rgb(55, 62, 76);\n"
"}\n"
"QSlider::handle:horizontal {\n"
"    background-color: rgb(85, 170, 255);\n"
"    border: none;\n"
"    height: 18px;\n"
"    width: 18px;\n"
"    margin: 0px;\n"
"	border-radius: 9px;\n"
"}\n"
"QSlider::handle:horizontal:hover {\n"
"    background-color: rgb(105, 180, 255);\n"
"}\n"
"QSlider::handle:horizontal:pressed {\n"
"    background-color: rgb(65, 130, 195);\n"
"}\n"
"\n"
"QSlider::groove:vertical {\n"
"    border-radius: 9px;\n"
"    width: 18px;\n"
"    margin: 0px;\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QSlider::groove:vertical:hover {\n"
"	background-color: rgb(55, 62, 76);\n"
"}\n"
"QSlider::handle:vertical {\n"
"    background-color: rgb(85, 170, 255);\n"
"	border: none;\n"
""
                        "    height: 18px;\n"
"    width: 18px;\n"
"    margin: 0px;\n"
"	border-radius: 9px;\n"
"}\n"
"QSlider::handle:vertical:hover {\n"
"    background-color: rgb(105, 180, 255);\n"
"}\n"
"QSlider::handle:vertical:pressed {\n"
"    background-color: rgb(65, 130, 195);\n"
"}\n"
"QPlainTextEdit {\n"
"	background-color: rgb(92,99, 112);\n"
"	border-radius: 5px;\n"
"	border: 2px solid rgb(27, 29, 35);\n"
"	padding-left: 10px;\n"
"}\n"
"QPlainTextEdit:hover {\n"
"	border: 2px solid rgb(64, 71, 88);\n"
"}\n"
"QPlainTextEdit:focus {\n"
"	border: 2px solid rgb(91, 101, 124);\n"
"}\n"
"")
        self.frame_main.setFrameShape(QFrame.NoFrame)
        self.frame_main.setFrameShadow(QFrame.Raised)
        self.verticalLayout = QVBoxLayout(self.frame_main)
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.frame_top = QFrame(self.frame_main)
        self.frame_top.setObjectName(u"frame_top")
        self.frame_top.setMinimumSize(QSize(1120, 40))
        self.frame_top.setMaximumSize(QSize(16777215, 40))
        self.frame_top.setStyleSheet(u"background-color: transparent;")
        self.frame_top.setFrameShape(QFrame.NoFrame)
        self.frame_top.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_3 = QHBoxLayout(self.frame_top)
        self.horizontalLayout_3.setSpacing(0)
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.frame_top_right = QFrame(self.frame_top)
        self.frame_top_right.setObjectName(u"frame_top_right")
        self.frame_top_right.setMaximumSize(QSize(16777215, 50))
        self.frame_top_right.setStyleSheet(u"background: transparent;")
        self.frame_top_right.setFrameShape(QFrame.NoFrame)
        self.frame_top_right.setFrameShadow(QFrame.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.frame_top_right)
        self.verticalLayout_2.setSpacing(0)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.frame_top_btns = QFrame(self.frame_top_right)
        self.frame_top_btns.setObjectName(u"frame_top_btns")
        self.frame_top_btns.setMaximumSize(QSize(16777215, 42))
        self.frame_top_btns.setStyleSheet(u"background-color: rgba(27, 29, 35, 255)")
        self.frame_top_btns.setFrameShape(QFrame.NoFrame)
        self.frame_top_btns.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_4 = QHBoxLayout(self.frame_top_btns)
        self.horizontalLayout_4.setSpacing(0)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.frame_label_top_btns = QFrame(self.frame_top_btns)
        self.frame_label_top_btns.setObjectName(u"frame_label_top_btns")
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.frame_label_top_btns.sizePolicy().hasHeightForWidth())
        self.frame_label_top_btns.setSizePolicy(sizePolicy)
        self.frame_label_top_btns.setFrameShape(QFrame.NoFrame)
        self.frame_label_top_btns.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_10 = QHBoxLayout(self.frame_label_top_btns)
        self.horizontalLayout_10.setSpacing(6)
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.horizontalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.label_6 = QLabel(self.frame_label_top_btns)
        self.label_6.setObjectName(u"label_6")
        sizePolicy1 = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.label_6.sizePolicy().hasHeightForWidth())
        self.label_6.setSizePolicy(sizePolicy1)
        self.label_6.setMinimumSize(QSize(35, 30))
        self.label_6.setMaximumSize(QSize(30, 30))
        self.label_6.setPixmap(QPixmap(u":/icons/icons/INDIGO_logoGRAPHIS.png"))
        self.label_6.setScaledContents(True)

        self.horizontalLayout_10.addWidget(self.label_6)

        self.toolButton = QToolButton(self.frame_label_top_btns)
        self.toolButton.setObjectName(u"toolButton")
        self.toolButton.setMinimumSize(QSize(60, 40))
        self.toolButton.setMaximumSize(QSize(20, 16777215))
        font1 = QFont()
        font1.setPointSize(12)
        font1.setBold(True)
        font1.setWeight(75)
        self.toolButton.setFont(font1)
        self.toolButton.setStyleSheet(u"background: transparent;\n"
"")
        self.toolButton.setIconSize(QSize(40, 40))
        self.toolButton.setCheckable(False)
        self.toolButton.setPopupMode(QToolButton.InstantPopup)
        self.toolButton.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.toolButton.setAutoRaise(False)
        self.toolButton.setArrowType(Qt.NoArrow)

        self.horizontalLayout_10.addWidget(self.toolButton)

        self.frame_12 = QFrame(self.frame_label_top_btns)
        self.frame_12.setObjectName(u"frame_12")
        self.frame_12.setMaximumSize(QSize(40, 16777215))
        self.frame_12.setStyleSheet(u"background: transparent;\n"
"")
        self.frame_12.setFrameShape(QFrame.StyledPanel)
        self.frame_12.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_8 = QHBoxLayout(self.frame_12)
        self.horizontalLayout_8.setSpacing(0)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.waiting_spinner = SPINNINGWaiter(self.frame_12)
        self.waiting_spinner.setObjectName(u"waiting_spinner")
        sizePolicy2 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.waiting_spinner.sizePolicy().hasHeightForWidth())
        self.waiting_spinner.setSizePolicy(sizePolicy2)
        self.waiting_spinner.setMinimumSize(QSize(30, 0))
        self.waiting_spinner.setMaximumSize(QSize(40, 16777215))
        self.waiting_spinner.setStyleSheet(u"background: transparent;\n"
"")

        self.horizontalLayout_8.addWidget(self.waiting_spinner)


        self.horizontalLayout_10.addWidget(self.frame_12)

        self.lbl_sqlite_name = QLabel(self.frame_label_top_btns)
        self.lbl_sqlite_name.setObjectName(u"lbl_sqlite_name")
        sizePolicy3 = QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.lbl_sqlite_name.sizePolicy().hasHeightForWidth())
        self.lbl_sqlite_name.setSizePolicy(sizePolicy3)
        self.lbl_sqlite_name.setMinimumSize(QSize(0, 0))
        self.lbl_sqlite_name.setMaximumSize(QSize(2000, 16777215))
        self.lbl_sqlite_name.setFont(font1)
        self.lbl_sqlite_name.setStyleSheet(u"background: transparent;\n"
"")
        self.lbl_sqlite_name.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)

        self.horizontalLayout_10.addWidget(self.lbl_sqlite_name)

        self.label_title_bar_top = QLabel(self.frame_label_top_btns)
        self.label_title_bar_top.setObjectName(u"label_title_bar_top")
        self.label_title_bar_top.setMaximumSize(QSize(200, 31))
        font2 = QFont()
        font2.setFamily(u"Segoe UI")
        font2.setPointSize(12)
        font2.setBold(True)
        font2.setWeight(75)
        self.label_title_bar_top.setFont(font2)
        self.label_title_bar_top.setStyleSheet(u"background: transparent;\n"
"")
        self.label_title_bar_top.setPixmap(QPixmap(u":/icons/icons/INDIGO_logoGRAPHIS_text.png"))
        self.label_title_bar_top.setScaledContents(True)
        self.label_title_bar_top.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_10.addWidget(self.label_title_bar_top)


        self.horizontalLayout_4.addWidget(self.frame_label_top_btns)

        self.frame_btns_right = QFrame(self.frame_top_btns)
        self.frame_btns_right.setObjectName(u"frame_btns_right")
        sizePolicy.setHeightForWidth(self.frame_btns_right.sizePolicy().hasHeightForWidth())
        self.frame_btns_right.setSizePolicy(sizePolicy)
        self.frame_btns_right.setMaximumSize(QSize(120, 16777215))
        self.frame_btns_right.setFrameShape(QFrame.NoFrame)
        self.frame_btns_right.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_5 = QHBoxLayout(self.frame_btns_right)
        self.horizontalLayout_5.setSpacing(0)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.horizontalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.btn_minimize = QPushButton(self.frame_btns_right)
        self.btn_minimize.setObjectName(u"btn_minimize")
        sizePolicy4 = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        sizePolicy4.setHorizontalStretch(0)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.btn_minimize.sizePolicy().hasHeightForWidth())
        self.btn_minimize.setSizePolicy(sizePolicy4)
        self.btn_minimize.setMinimumSize(QSize(40, 0))
        self.btn_minimize.setMaximumSize(QSize(40, 16777215))
        self.btn_minimize.setStyleSheet(u"QPushButton {	\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(85, 170, 255);\n"
"}")
        icon = QIcon()
        icon.addFile(u":/icons/icons/cil-window-minimize.png", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_minimize.setIcon(icon)

        self.horizontalLayout_5.addWidget(self.btn_minimize)

        self.btn_maximize_restore = QPushButton(self.frame_btns_right)
        self.btn_maximize_restore.setObjectName(u"btn_maximize_restore")
        sizePolicy4.setHeightForWidth(self.btn_maximize_restore.sizePolicy().hasHeightForWidth())
        self.btn_maximize_restore.setSizePolicy(sizePolicy4)
        self.btn_maximize_restore.setMinimumSize(QSize(40, 0))
        self.btn_maximize_restore.setMaximumSize(QSize(40, 16777215))
        self.btn_maximize_restore.setStyleSheet(u"QPushButton {	\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(85, 170, 255);\n"
"}")
        icon1 = QIcon()
        icon1.addFile(u":/icons/icons/cil-window-maximize.png", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_maximize_restore.setIcon(icon1)

        self.horizontalLayout_5.addWidget(self.btn_maximize_restore)

        self.btn_close = QPushButton(self.frame_btns_right)
        self.btn_close.setObjectName(u"btn_close")
        sizePolicy4.setHeightForWidth(self.btn_close.sizePolicy().hasHeightForWidth())
        self.btn_close.setSizePolicy(sizePolicy4)
        self.btn_close.setMinimumSize(QSize(40, 0))
        self.btn_close.setMaximumSize(QSize(40, 16777215))
        self.btn_close.setStyleSheet(u"QPushButton {	\n"
"	border: none;\n"
"	background-color: transparent;\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(150, 40, 23);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(250, 39, 10);\n"
"}")
        icon2 = QIcon()
        icon2.addFile(u":/icons/icons/cil-x.png", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_close.setIcon(icon2)

        self.horizontalLayout_5.addWidget(self.btn_close)


        self.horizontalLayout_4.addWidget(self.frame_btns_right, 0, Qt.AlignRight)


        self.verticalLayout_2.addWidget(self.frame_top_btns)


        self.horizontalLayout_3.addWidget(self.frame_top_right)


        self.verticalLayout.addWidget(self.frame_top)

        self.frame_center = QFrame(self.frame_main)
        self.frame_center.setObjectName(u"frame_center")
        sizePolicy5 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.frame_center.sizePolicy().hasHeightForWidth())
        self.frame_center.setSizePolicy(sizePolicy5)
        self.frame_center.setMinimumSize(QSize(1120, 0))
        self.frame_center.setStyleSheet(u"background-color: rgb(40, 44, 52);")
        self.frame_center.setFrameShape(QFrame.NoFrame)
        self.frame_center.setFrameShadow(QFrame.Raised)
        self.verticalLayout_4 = QVBoxLayout(self.frame_center)
        self.verticalLayout_4.setSpacing(0)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.frame_7 = QFrame(self.frame_center)
        self.frame_7.setObjectName(u"frame_7")
        sizePolicy5.setHeightForWidth(self.frame_7.sizePolicy().hasHeightForWidth())
        self.frame_7.setSizePolicy(sizePolicy5)
        self.frame_7.setFrameShape(QFrame.StyledPanel)
        self.frame_7.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_7)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.frame_2 = QFrame(self.frame_7)
        self.frame_2.setObjectName(u"frame_2")
        sizePolicy2.setHeightForWidth(self.frame_2.sizePolicy().hasHeightForWidth())
        self.frame_2.setSizePolicy(sizePolicy2)
        self.frame_2.setMinimumSize(QSize(0, 0))
        self.frame_2.setMaximumSize(QSize(250, 16777215))
        self.frame_2.setFont(font1)
        self.verticalLayout_6 = QVBoxLayout(self.frame_2)
        self.verticalLayout_6.setSpacing(0)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.groupBox = QGroupBox(self.frame_2)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setMaximumSize(QSize(16777215, 200))
        self.groupBox.setFont(font1)
        self.groupBox.setAlignment(Qt.AlignCenter)
        self.label_2 = QLabel(self.groupBox)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(20, 150, 91, 30))
        self.label_2.setFont(font1)
        self.lbl_polygon_number = QLabel(self.groupBox)
        self.lbl_polygon_number.setObjectName(u"lbl_polygon_number")
        self.lbl_polygon_number.setGeometry(QRect(160, 150, 81, 30))
        font3 = QFont()
        font3.setPointSize(20)
        font3.setBold(True)
        font3.setWeight(75)
        self.lbl_polygon_number.setFont(font3)
        self.lbl_polygon_number.setStyleSheet(u"color: purple;")
        self.lbl_polygon_number.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)
        self.label_3 = QLabel(self.groupBox)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(20, 110, 101, 26))
        self.label_3.setFont(font1)
        self.lbl_circle_number = QLabel(self.groupBox)
        self.lbl_circle_number.setObjectName(u"lbl_circle_number")
        self.lbl_circle_number.setGeometry(QRect(160, 70, 81, 30))
        self.lbl_circle_number.setFont(font3)
        self.lbl_circle_number.setStyleSheet(u"color: lightblue;")
        self.lbl_circle_number.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)
        self.label_18 = QLabel(self.groupBox)
        self.label_18.setObjectName(u"label_18")
        self.label_18.setGeometry(QRect(20, 70, 101, 30))
        self.label_18.setFont(font1)
        self.lbl_rectangle_number = QLabel(self.groupBox)
        self.lbl_rectangle_number.setObjectName(u"lbl_rectangle_number")
        self.lbl_rectangle_number.setGeometry(QRect(160, 110, 71, 30))
        self.lbl_rectangle_number.setFont(font3)
        self.lbl_rectangle_number.setStyleSheet(u"color: orange;")
        self.lbl_rectangle_number.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)
        self.label_5 = QLabel(self.groupBox)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setGeometry(QRect(20, 30, 121, 20))
        self.label_5.setFont(font1)
        self.label_5.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)
        self.lbl_image_number = QLabel(self.groupBox)
        self.lbl_image_number.setObjectName(u"lbl_image_number")
        self.lbl_image_number.setGeometry(QRect(160, 20, 81, 41))
        self.lbl_image_number.setFont(font3)
        self.lbl_image_number.setStyleSheet(u"color: #d7191c;")
        self.lbl_image_number.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignVCenter)

        self.verticalLayout_6.addWidget(self.groupBox)

        self.groupBox_3 = QGroupBox(self.frame_2)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.groupBox_3.setMaximumSize(QSize(16777215, 200))
        self.groupBox_3.setFont(font1)
        self.groupBox_3.setAlignment(Qt.AlignCenter)
        self.btn_color_polygon = COLORButton(self.groupBox_3)
        self.btn_color_polygon.setObjectName(u"btn_color_polygon")
        self.btn_color_polygon.setGeometry(QRect(170, 40, 51, 51))
        self.btn_color_polygon.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")
        icon3 = QIcon()
        icon3.addFile(u":/icons/icons/polygon_color.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_color_polygon.setIcon(icon3)
        self.btn_color_polygon.setIconSize(QSize(50, 50))
        self.btn_color_circle = COLORButton(self.groupBox_3)
        self.btn_color_circle.setObjectName(u"btn_color_circle")
        self.btn_color_circle.setGeometry(QRect(30, 40, 51, 51))
        self.btn_color_circle.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")
        icon4 = QIcon()
        icon4.addFile(u":/icons/icons/circle_color.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_color_circle.setIcon(icon4)
        self.btn_color_circle.setIconSize(QSize(50, 50))
        self.btn_color_rectangle = COLORButton(self.groupBox_3)
        self.btn_color_rectangle.setObjectName(u"btn_color_rectangle")
        self.btn_color_rectangle.setGeometry(QRect(100, 40, 51, 51))
        self.btn_color_rectangle.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")
        icon5 = QIcon()
        icon5.addFile(u":/icons/icons/rectangle_color.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_color_rectangle.setIcon(icon5)
        self.btn_color_rectangle.setIconSize(QSize(50, 50))
        self.btn_show_polygon = QPushButton(self.groupBox_3)
        self.btn_show_polygon.setObjectName(u"btn_show_polygon")
        self.btn_show_polygon.setGeometry(QRect(170, 120, 51, 51))
        self.btn_show_polygon.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")
        icon6 = QIcon()
        icon6.addFile(u":/icons/icons/polygon_show.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_show_polygon.setIcon(icon6)
        self.btn_show_polygon.setIconSize(QSize(50, 50))
        self.btn_show_circle = QPushButton(self.groupBox_3)
        self.btn_show_circle.setObjectName(u"btn_show_circle")
        self.btn_show_circle.setGeometry(QRect(30, 120, 51, 51))
        self.btn_show_circle.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")
        icon7 = QIcon()
        icon7.addFile(u":/icons/icons/circle_show.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_show_circle.setIcon(icon7)
        self.btn_show_circle.setIconSize(QSize(50, 50))
        self.btn_show_rectangle = QPushButton(self.groupBox_3)
        self.btn_show_rectangle.setObjectName(u"btn_show_rectangle")
        self.btn_show_rectangle.setGeometry(QRect(100, 120, 51, 51))
        self.btn_show_rectangle.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")
        icon8 = QIcon()
        icon8.addFile(u":/icons/icons/rectangle_show.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_show_rectangle.setIcon(icon8)
        self.btn_show_rectangle.setIconSize(QSize(50, 50))

        self.verticalLayout_6.addWidget(self.groupBox_3)

        self.groupBox_2 = QGroupBox(self.frame_2)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.groupBox_2.setMaximumSize(QSize(16777215, 200))
        self.groupBox_2.setFont(font1)
        self.groupBox_2.setAlignment(Qt.AlignCenter)
        self.btn_create_circle = QPushButton(self.groupBox_2)
        self.btn_create_circle.setObjectName(u"btn_create_circle")
        self.btn_create_circle.setGeometry(QRect(10, 50, 51, 51))
        self.btn_create_circle.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")
        icon9 = QIcon()
        icon9.addFile(u":/icons/icons/circle.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_create_circle.setIcon(icon9)
        self.btn_create_circle.setIconSize(QSize(50, 50))
        self.btn_create_rectangle = QPushButton(self.groupBox_2)
        self.btn_create_rectangle.setObjectName(u"btn_create_rectangle")
        self.btn_create_rectangle.setGeometry(QRect(70, 50, 51, 51))
        self.btn_create_rectangle.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")
        icon10 = QIcon()
        icon10.addFile(u":/icons/icons/rectangle.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_create_rectangle.setIcon(icon10)
        self.btn_create_rectangle.setIconSize(QSize(50, 50))
        self.btn_create_polygon = QPushButton(self.groupBox_2)
        self.btn_create_polygon.setObjectName(u"btn_create_polygon")
        self.btn_create_polygon.setGeometry(QRect(130, 50, 51, 51))
        self.btn_create_polygon.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")
        icon11 = QIcon()
        icon11.addFile(u":/icons/icons/polygon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_create_polygon.setIcon(icon11)
        self.btn_create_polygon.setIconSize(QSize(50, 50))
        self.btn_geometry_move = QPushButton(self.groupBox_2)
        self.btn_geometry_move.setObjectName(u"btn_geometry_move")
        self.btn_geometry_move.setGeometry(QRect(10, 120, 51, 51))
        self.btn_geometry_move.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")
        icon12 = QIcon()
        icon12.addFile(u":/icons/icons/move.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_geometry_move.setIcon(icon12)
        self.btn_geometry_move.setIconSize(QSize(50, 50))
        self.btn_geometry_resize = QPushButton(self.groupBox_2)
        self.btn_geometry_resize.setObjectName(u"btn_geometry_resize")
        self.btn_geometry_resize.setGeometry(QRect(70, 120, 51, 51))
        self.btn_geometry_resize.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")
        icon13 = QIcon()
        icon13.addFile(u":/icons/icons/resize.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_geometry_resize.setIcon(icon13)
        self.btn_geometry_resize.setIconSize(QSize(50, 50))
        self.btn_geometry_remove = QPushButton(self.groupBox_2)
        self.btn_geometry_remove.setObjectName(u"btn_geometry_remove")
        self.btn_geometry_remove.setGeometry(QRect(190, 120, 51, 51))
        self.btn_geometry_remove.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")
        icon14 = QIcon()
        icon14.addFile(u":/icons/icons/Flat_cross_icon.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_geometry_remove.setIcon(icon14)
        self.btn_geometry_remove.setIconSize(QSize(50, 50))

        self.verticalLayout_6.addWidget(self.groupBox_2)

        self.frame_11 = QFrame(self.frame_2)
        self.frame_11.setObjectName(u"frame_11")
        self.frame_11.setMaximumSize(QSize(16777215, 200))
        self.frame_11.setFrameShape(QFrame.StyledPanel)
        self.frame_11.setFrameShadow(QFrame.Raised)
        self.verticalLayout_12 = QVBoxLayout(self.frame_11)
        self.verticalLayout_12.setSpacing(0)
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.verticalLayout_12.setContentsMargins(6, 0, 0, 0)
        self.tabWidget_2 = QTabWidget(self.frame_11)
        self.tabWidget_2.setObjectName(u"tabWidget_2")
        self.tabWidget_2.setStyleSheet(u"\n"
"\n"
"/* Style the tab using the tab sub-control. Note that\n"
"    it reads QTabBar _not_ QTabWidget */\n"
"QTabBar::tab {\n"
"  \n"
"    border: 2px solid #C4C4C3;\n"
"    border-bottom-color: #C2C7CB; /* same as the pane color */\n"
"    border-top-left-radius: 4px;\n"
"    border-top-right-radius: 4px;\n"
"    min-width: 8ex;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"QTabWidget::pane\n"
"{\n"
"border-top: 0px solid rgb(0, 0, 0);\n"
"border-left: 0px solid rgb(0, 0, 0);\n"
"border-right: 0px solid rgb(0, 0, 0);\n"
"border-bottom: 0px solid rgb(0, 0, 0);\n"
"}\n"
"\n"
"QTabBar::tab:selected {\n"
"    border-color:  #C2C7CB;\n"
"    border-bottom-color: #C2C7CB; /* same as pane color */\n"
"}\n"
"\n"
"QTabBar::tab:!selected {\n"
"    margin-top:5px; /* make non-selected tabs look smaller */\n"
"}\n"
"")
        self.tabWidget_2.setTabPosition(QTabWidget.South)
        self.tabWidget_2.setIconSize(QSize(25, 25))
        self.tabWidget_2.setElideMode(Qt.ElideMiddle)
        self.tab_3 = QWidget()
        self.tab_3.setObjectName(u"tab_3")
        self.plainTextEdit = QPlainTextEdit(self.tab_3)
        self.plainTextEdit.setObjectName(u"plainTextEdit")
        self.plainTextEdit.setGeometry(QRect(0, 0, 241, 151))
        self.plainTextEdit.setFrameShape(QFrame.NoFrame)
        self.plainTextEdit.setFrameShadow(QFrame.Plain)
        self.plainTextEdit.setLineWidth(0)
        icon15 = QIcon()
        icon15.addFile(u":/icons/icons/Question.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.tabWidget_2.addTab(self.tab_3, icon15, "")
        self.tab_4 = QWidget()
        self.tab_4.setObjectName(u"tab_4")
        self.info_screen = QTextEdit(self.tab_4)
        self.info_screen.setObjectName(u"info_screen")
        self.info_screen.setGeometry(QRect(0, 0, 251, 151))
        sizePolicy6 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        sizePolicy6.setHorizontalStretch(0)
        sizePolicy6.setVerticalStretch(0)
        sizePolicy6.setHeightForWidth(self.info_screen.sizePolicy().hasHeightForWidth())
        self.info_screen.setSizePolicy(sizePolicy6)
        self.info_screen.setMinimumSize(QSize(0, 0))
        self.info_screen.setMaximumSize(QSize(16777215, 16777215))
        self.info_screen.setBaseSize(QSize(0, 0))
        self.info_screen.setStyleSheet(u"QTextEdit {\n"
"	background-color: rgb(27, 29, 35);\n"
"	border-radius: 5px;\n"
"	padding: 10px;\n"
"}\n"
"QPTextEdit:hover {\n"
"	border: 2px solid rgb(64, 71, 88);\n"
"}\n"
"QPTextEdit:focus {\n"
"	border: 2px solid rgb(91, 101, 124);\n"
"}")
        self.info_screen.setUndoRedoEnabled(False)
        self.info_screen.setReadOnly(True)
        self.info_screen.setTabStopDistance(5.000000000000000)
        icon16 = QIcon()
        icon16.addFile(u":/icons/icons/console.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.tabWidget_2.addTab(self.tab_4, icon16, "")

        self.verticalLayout_12.addWidget(self.tabWidget_2)


        self.verticalLayout_6.addWidget(self.frame_11)


        self.horizontalLayout_2.addWidget(self.frame_2)

        self.splitter_main = QSplitter(self.frame_7)
        self.splitter_main.setObjectName(u"splitter_main")
        self.splitter_main.setOrientation(Qt.Horizontal)
        self.splitter_main.setChildrenCollapsible(False)
        self.frame = QFrame(self.splitter_main)
        self.frame.setObjectName(u"frame")
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.verticalLayout_5 = QVBoxLayout(self.frame)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.lbl_image_name = QLabel(self.frame)
        self.lbl_image_name.setObjectName(u"lbl_image_name")
        self.lbl_image_name.setFont(font1)

        self.verticalLayout_5.addWidget(self.lbl_image_name)

        self.lbl_image_path = QLabel(self.frame)
        self.lbl_image_path.setObjectName(u"lbl_image_path")
        self.lbl_image_path.setMinimumSize(QSize(0, 30))
        self.lbl_image_path.setWordWrap(False)

        self.verticalLayout_5.addWidget(self.lbl_image_path)

        self.splitter_images = QSplitter(self.frame)
        self.splitter_images.setObjectName(u"splitter_images")
        self.splitter_images.setOrientation(Qt.Vertical)
        self.splitter_images.setChildrenCollapsible(False)
        self.view_digizizer = DIGITIZERView(self.splitter_images)
        self.view_digizizer.setObjectName(u"view_digizizer")
        sizePolicy2.setHeightForWidth(self.view_digizizer.sizePolicy().hasHeightForWidth())
        self.view_digizizer.setSizePolicy(sizePolicy2)
        self.view_digizizer.setMinimumSize(QSize(400, 0))
        self.view_digizizer.setFocusPolicy(Qt.NoFocus)
        self.splitter_images.addWidget(self.view_digizizer)
        self.table_preview = QTableView(self.splitter_images)
        self.table_preview.setObjectName(u"table_preview")
        self.table_preview.setSelectionMode(QAbstractItemView.NoSelection)
        self.table_preview.setShowGrid(False)
        self.splitter_images.addWidget(self.table_preview)
        self.table_preview.horizontalHeader().setVisible(False)
        self.table_preview.verticalHeader().setVisible(False)

        self.verticalLayout_5.addWidget(self.splitter_images)

        self.splitter_main.addWidget(self.frame)
        self.frame_3 = QFrame(self.splitter_main)
        self.frame_3.setObjectName(u"frame_3")
        self.frame_3.setMinimumSize(QSize(430, 0))
        self.frame_3.setMaximumSize(QSize(16777215, 16777215))
        self.frame_3.setFrameShape(QFrame.StyledPanel)
        self.frame_3.setFrameShadow(QFrame.Raised)
        self.verticalLayout_7 = QVBoxLayout(self.frame_3)
        self.verticalLayout_7.setSpacing(0)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.groupBox_9 = QGroupBox(self.frame_3)
        self.groupBox_9.setObjectName(u"groupBox_9")
        self.groupBox_9.setMinimumSize(QSize(0, 80))
        self.groupBox_9.setMaximumSize(QSize(16777215, 150))
        self.groupBox_9.setFont(font1)
        self.formLayout_4 = QFormLayout(self.groupBox_9)
        self.formLayout_4.setObjectName(u"formLayout_4")
        self.formLayout_4.setContentsMargins(12, -1, -1, -1)
        self.label_17 = QLabel(self.groupBox_9)
        self.label_17.setObjectName(u"label_17")
        self.label_17.setFont(font1)

        self.formLayout_4.setWidget(0, QFormLayout.LabelRole, self.label_17)

        self.txt_user_name = QPlainTextEdit(self.groupBox_9)
        self.txt_user_name.setObjectName(u"txt_user_name")
        font4 = QFont()
        font4.setPointSize(10)
        self.txt_user_name.setFont(font4)
        self.txt_user_name.setStyleSheet(u"background-color: rgb(52, 70, 72);")

        self.formLayout_4.setWidget(0, QFormLayout.FieldRole, self.txt_user_name)

        self.label_16 = QLabel(self.groupBox_9)
        self.label_16.setObjectName(u"label_16")
        self.label_16.setFont(font1)

        self.formLayout_4.setWidget(1, QFormLayout.LabelRole, self.label_16)

        self.txt_user_indent = QPlainTextEdit(self.groupBox_9)
        self.txt_user_indent.setObjectName(u"txt_user_indent")
        self.txt_user_indent.setFont(font4)
        self.txt_user_indent.setStyleSheet(u"background-color: rgb(52, 70, 72);")

        self.formLayout_4.setWidget(1, QFormLayout.FieldRole, self.txt_user_indent)


        self.verticalLayout_7.addWidget(self.groupBox_9)

        self.tabWidget = QTabWidget(self.frame_3)
        self.tabWidget.setObjectName(u"tabWidget")
        font5 = QFont()
        font5.setPointSize(9)
        font5.setBold(True)
        font5.setWeight(75)
        self.tabWidget.setFont(font5)
        self.tabWidget.setStyleSheet(u"\n"
"\n"
"/* Style the tab using the tab sub-control. Note that\n"
"    it reads QTabBar _not_ QTabWidget */\n"
"QTabBar::tab {\n"
"    background:  rgb(70, 50,72);\n"
"    border: 2px solid #C4C4C3;\n"
"    border-bottom-color: #C2C7CB; /* same as the pane color */\n"
"    border-top-left-radius: 4px;\n"
"    border-top-right-radius: 4px;\n"
"    min-width: 8ex;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"\n"
"QTabWidget::pane\n"
"{\n"
"border-top: 0px solid rgb(0, 0, 0);\n"
"border-left: 0px solid rgb(0, 0, 0);\n"
"border-right: 0px solid rgb(0, 0, 0);\n"
"border-bottom: 0px solid rgb(0, 0, 0);\n"
"}\n"
"\n"
"\n"
"QTabBar::tab:selected {\n"
"    border-color:  #C2C7CB;\n"
"    border-bottom-color: #C2C7CB; /* same as pane color */\n"
"}\n"
"\n"
"QTabBar::tab:!selected {\n"
"    margin-top:5px; /* make non-selected tabs look smaller */\n"
"}\n"
"\n"
"")
        self.tab = QWidget()
        self.tab.setObjectName(u"tab")
        self.verticalLayout_8 = QVBoxLayout(self.tab)
        self.verticalLayout_8.setSpacing(0)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.frame_10 = QFrame(self.tab)
        self.frame_10.setObjectName(u"frame_10")
        self.frame_10.setMinimumSize(QSize(0, 0))
        self.frame_10.setMaximumSize(QSize(16777215, 16777215))
        self.frame_10.setFrameShape(QFrame.StyledPanel)
        self.frame_10.setFrameShadow(QFrame.Raised)
        self.verticalLayout_10 = QVBoxLayout(self.frame_10)
        self.verticalLayout_10.setSpacing(6)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_10.setContentsMargins(0, 0, 0, 0)
        self.btn_object_save = QPushButton(self.frame_10)
        self.btn_object_save.setObjectName(u"btn_object_save")
        self.btn_object_save.setMinimumSize(QSize(50, 50))
        self.btn_object_save.setMaximumSize(QSize(50, 50))
        font6 = QFont()
        font6.setPointSize(10)
        font6.setBold(True)
        font6.setWeight(75)
        self.btn_object_save.setFont(font6)
        self.btn_object_save.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")
        icon17 = QIcon()
        icon17.addFile(u":/icons/icons/save.svg", QSize(), QIcon.Normal, QIcon.Off)
        self.btn_object_save.setIcon(icon17)
        self.btn_object_save.setIconSize(QSize(50, 50))

        self.verticalLayout_10.addWidget(self.btn_object_save)

        self.frame_5 = QFrame(self.frame_10)
        self.frame_5.setObjectName(u"frame_5")
        sizePolicy7 = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy7.setHorizontalStretch(0)
        sizePolicy7.setVerticalStretch(0)
        sizePolicy7.setHeightForWidth(self.frame_5.sizePolicy().hasHeightForWidth())
        self.frame_5.setSizePolicy(sizePolicy7)
        self.frame_5.setMaximumSize(QSize(16777215, 350))
        self.frame_5.setStyleSheet(u"background-color: rgb(0, 74, 117);")
        self.frame_5.setFrameShape(QFrame.StyledPanel)
        self.frame_5.setFrameShadow(QFrame.Raised)
        self.verticalLayout_11 = QVBoxLayout(self.frame_5)
        self.verticalLayout_11.setSpacing(0)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_11.setContentsMargins(-1, 3, -1, 3)
        self.groupBox_5 = QGroupBox(self.frame_5)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.groupBox_5.setMaximumSize(QSize(16777215, 16777215))
        self.groupBox_5.setBaseSize(QSize(0, 0))
        self.groupBox_5.setFont(font6)
        self.formLayout_5 = QFormLayout(self.groupBox_5)
        self.formLayout_5.setObjectName(u"formLayout_5")
        self.formLayout_5.setVerticalSpacing(10)
        self.formLayout_5.setContentsMargins(-1, 9, -1, 3)
        self.label = QLabel(self.groupBox_5)
        self.label.setObjectName(u"label")
        font7 = QFont()
        font7.setPointSize(11)
        font7.setBold(True)
        font7.setWeight(75)
        self.label.setFont(font7)

        self.formLayout_5.setWidget(0, QFormLayout.LabelRole, self.label)

        self.txt_rid = QPlainTextEdit(self.groupBox_5)
        self.txt_rid.setObjectName(u"txt_rid")
        sizePolicy2.setHeightForWidth(self.txt_rid.sizePolicy().hasHeightForWidth())
        self.txt_rid.setSizePolicy(sizePolicy2)
        self.txt_rid.setMaximumSize(QSize(16777215, 35))
        self.txt_rid.setFont(font4)
        self.txt_rid.setStyleSheet(u"background-color: rgb(52, 70, 72);")
        self.txt_rid.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.formLayout_5.setWidget(0, QFormLayout.FieldRole, self.txt_rid)

        self.label_4 = QLabel(self.groupBox_5)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setFont(font7)

        self.formLayout_5.setWidget(1, QFormLayout.LabelRole, self.label_4)

        self.txt_rname = QPlainTextEdit(self.groupBox_5)
        self.txt_rname.setObjectName(u"txt_rname")
        sizePolicy2.setHeightForWidth(self.txt_rname.sizePolicy().hasHeightForWidth())
        self.txt_rname.setSizePolicy(sizePolicy2)
        self.txt_rname.setMaximumSize(QSize(16777215, 35))
        self.txt_rname.setFont(font4)
        self.txt_rname.setStyleSheet(u"background-color: rgb(52, 90, 72);")
        self.txt_rname.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.formLayout_5.setWidget(1, QFormLayout.FieldRole, self.txt_rname)


        self.verticalLayout_11.addWidget(self.groupBox_5)

        self.groupBox_11 = QGroupBox(self.frame_5)
        self.groupBox_11.setObjectName(u"groupBox_11")
        self.groupBox_11.setMaximumSize(QSize(16777215, 16777215))
        self.groupBox_11.setBaseSize(QSize(0, 0))
        self.groupBox_11.setFont(font6)
        self.formLayout_8 = QFormLayout(self.groupBox_11)
        self.formLayout_8.setObjectName(u"formLayout_8")
        self.formLayout_8.setVerticalSpacing(10)
        self.formLayout_8.setContentsMargins(-1, 9, -1, 3)
        self.label_21 = QLabel(self.groupBox_11)
        self.label_21.setObjectName(u"label_21")
        self.label_21.setFont(font7)

        self.formLayout_8.setWidget(0, QFormLayout.LabelRole, self.label_21)

        self.txt_rrole_ident = QPlainTextEdit(self.groupBox_11)
        self.txt_rrole_ident.setObjectName(u"txt_rrole_ident")
        sizePolicy2.setHeightForWidth(self.txt_rrole_ident.sizePolicy().hasHeightForWidth())
        self.txt_rrole_ident.setSizePolicy(sizePolicy2)
        self.txt_rrole_ident.setMaximumSize(QSize(16777215, 35))
        self.txt_rrole_ident.setFont(font4)
        self.txt_rrole_ident.setStyleSheet(u"background-color: rgb(52, 70, 72);")
        self.txt_rrole_ident.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.formLayout_8.setWidget(0, QFormLayout.FieldRole, self.txt_rrole_ident)

        self.label_22 = QLabel(self.groupBox_11)
        self.label_22.setObjectName(u"label_22")
        self.label_22.setFont(font7)

        self.formLayout_8.setWidget(1, QFormLayout.LabelRole, self.label_22)

        self.comboBox_region_role = QComboBox(self.groupBox_11)
        self.comboBox_region_role.setObjectName(u"comboBox_region_role")
        sizePolicy2.setHeightForWidth(self.comboBox_region_role.sizePolicy().hasHeightForWidth())
        self.comboBox_region_role.setSizePolicy(sizePolicy2)
        self.comboBox_region_role.setMaximumSize(QSize(16777215, 35))
        font8 = QFont()
        font8.setPointSize(11)
        self.comboBox_region_role.setFont(font8)
        self.comboBox_region_role.setLayoutDirection(Qt.RightToLeft)
        self.comboBox_region_role.setStyleSheet(u"background-color: rgb(52, 90, 72);")

        self.formLayout_8.setWidget(1, QFormLayout.FieldRole, self.comboBox_region_role)


        self.verticalLayout_11.addWidget(self.groupBox_11)

        self.groupBox_10 = QGroupBox(self.frame_5)
        self.groupBox_10.setObjectName(u"groupBox_10")
        self.groupBox_10.setMaximumSize(QSize(16777215, 16777215))
        self.groupBox_10.setBaseSize(QSize(0, 0))
        self.groupBox_10.setFont(font6)
        self.formLayout_6 = QFormLayout(self.groupBox_10)
        self.formLayout_6.setObjectName(u"formLayout_6")
        self.formLayout_6.setVerticalSpacing(10)
        self.formLayout_6.setContentsMargins(-1, 9, -1, 3)
        self.label_19 = QLabel(self.groupBox_10)
        self.label_19.setObjectName(u"label_19")
        self.label_19.setFont(font7)

        self.formLayout_6.setWidget(0, QFormLayout.LabelRole, self.label_19)

        self.txt_rctype_indent = QPlainTextEdit(self.groupBox_10)
        self.txt_rctype_indent.setObjectName(u"txt_rctype_indent")
        sizePolicy2.setHeightForWidth(self.txt_rctype_indent.sizePolicy().hasHeightForWidth())
        self.txt_rctype_indent.setSizePolicy(sizePolicy2)
        self.txt_rctype_indent.setMaximumSize(QSize(16777215, 35))
        self.txt_rctype_indent.setFont(font4)
        self.txt_rctype_indent.setStyleSheet(u"background-color: rgb(52, 70, 72);")
        self.txt_rctype_indent.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.formLayout_6.setWidget(0, QFormLayout.FieldRole, self.txt_rctype_indent)

        self.label_20 = QLabel(self.groupBox_10)
        self.label_20.setObjectName(u"label_20")
        self.label_20.setFont(font7)

        self.formLayout_6.setWidget(1, QFormLayout.LabelRole, self.label_20)

        self.txt_rctype_name = QPlainTextEdit(self.groupBox_10)
        self.txt_rctype_name.setObjectName(u"txt_rctype_name")
        sizePolicy2.setHeightForWidth(self.txt_rctype_name.sizePolicy().hasHeightForWidth())
        self.txt_rctype_name.setSizePolicy(sizePolicy2)
        self.txt_rctype_name.setMaximumSize(QSize(16777215, 35))
        self.txt_rctype_name.setFont(font4)
        self.txt_rctype_name.setStyleSheet(u"background-color: rgb(52, 70, 72);")
        self.txt_rctype_name.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.formLayout_6.setWidget(1, QFormLayout.FieldRole, self.txt_rctype_name)


        self.verticalLayout_11.addWidget(self.groupBox_10)


        self.verticalLayout_10.addWidget(self.frame_5)

        self.tabWidget_3 = QTabWidget(self.frame_10)
        self.tabWidget_3.setObjectName(u"tabWidget_3")
        sizePolicy2.setHeightForWidth(self.tabWidget_3.sizePolicy().hasHeightForWidth())
        self.tabWidget_3.setSizePolicy(sizePolicy2)
        self.tabWidget_3.setMinimumSize(QSize(0, 0))
        self.tabWidget_3.setMaximumSize(QSize(16777215, 500))
        self.tabWidget_3.setFont(font5)
        self.tabWidget_3.setStyleSheet(u"\n"
"\n"
"/* Style the tab using the tab sub-control. Note that\n"
"    it reads QTabBar _not_ QTabWidget */\n"
"QTabBar::tab {\n"
"    background:  rgb(70, 50,72);\n"
"    border: 2px solid #C4C4C3;\n"
"    border-bottom-color: #C2C7CB; /* same as the pane color */\n"
"    border-top-left-radius: 4px;\n"
"    border-top-right-radius: 4px;\n"
"    min-width: 8ex;\n"
"    padding: 3px;\n"
"}\n"
"\n"
"\n"
"QTabWidget::pane\n"
"{\n"
"border-top: 0px solid rgb(0, 0, 0);\n"
"border-left: 0px solid rgb(0, 0, 0);\n"
"border-right: 0px solid rgb(0, 0, 0);\n"
"border-bottom: 0px solid rgb(0, 0, 0);\n"
"}\n"
"\n"
"\n"
"QTabBar::tab:selected {\n"
"    border-color:  #C2C7CB;\n"
"    border-bottom-color: #C2C7CB; /* same as pane color */\n"
"}\n"
"\n"
"QTabBar::tab:!selected {\n"
"    margin-top:5px; /* make non-selected tabs look smaller */\n"
"}\n"
"\n"
"")
        self.tab_7 = QWidget()
        self.tab_7.setObjectName(u"tab_7")
        self.verticalLayout_15 = QVBoxLayout(self.tab_7)
        self.verticalLayout_15.setSpacing(0)
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.verticalLayout_15.setContentsMargins(0, 0, 0, 0)
        self.frame_9 = QFrame(self.tab_7)
        self.frame_9.setObjectName(u"frame_9")
        self.frame_9.setMaximumSize(QSize(16777215, 150))
        self.frame_9.setFrameShape(QFrame.StyledPanel)
        self.frame_9.setFrameShadow(QFrame.Raised)
        self.formLayout_7 = QFormLayout(self.frame_9)
        self.formLayout_7.setObjectName(u"formLayout_7")
        self.label_11 = QLabel(self.frame_9)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setFont(font7)

        self.formLayout_7.setWidget(0, QFormLayout.LabelRole, self.label_11)

        self.contr_creator_ident = QPlainTextEdit(self.frame_9)
        self.contr_creator_ident.setObjectName(u"contr_creator_ident")
        sizePolicy2.setHeightForWidth(self.contr_creator_ident.sizePolicy().hasHeightForWidth())
        self.contr_creator_ident.setSizePolicy(sizePolicy2)
        self.contr_creator_ident.setFont(font4)
        self.contr_creator_ident.setStyleSheet(u"background-color: rgb(52, 70, 72);")
        self.contr_creator_ident.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.formLayout_7.setWidget(0, QFormLayout.FieldRole, self.contr_creator_ident)

        self.label_10 = QLabel(self.frame_9)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setFont(font7)

        self.formLayout_7.setWidget(1, QFormLayout.LabelRole, self.label_10)

        self.contr_creator_name = QPlainTextEdit(self.frame_9)
        self.contr_creator_name.setObjectName(u"contr_creator_name")
        self.contr_creator_name.setFont(font4)
        self.contr_creator_name.setStyleSheet(u"background-color: rgb(52, 70, 72);")
        self.contr_creator_name.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.formLayout_7.setWidget(1, QFormLayout.FieldRole, self.contr_creator_name)

        self.label_12 = QLabel(self.frame_9)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setFont(font7)

        self.formLayout_7.setWidget(2, QFormLayout.LabelRole, self.label_12)

        self.contr_creator_role = QPlainTextEdit(self.frame_9)
        self.contr_creator_role.setObjectName(u"contr_creator_role")
        self.contr_creator_role.setFont(font4)
        self.contr_creator_role.setStyleSheet(u"background-color: rgb(90, 90, 90);")
        self.contr_creator_role.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.contr_creator_role.setReadOnly(True)

        self.formLayout_7.setWidget(2, QFormLayout.FieldRole, self.contr_creator_role)


        self.verticalLayout_15.addWidget(self.frame_9)

        self.tabWidget_3.addTab(self.tab_7, "")
        self.tab_6 = QWidget()
        self.tab_6.setObjectName(u"tab_6")
        self.verticalLayout_16 = QVBoxLayout(self.tab_6)
        self.verticalLayout_16.setSpacing(0)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.verticalLayout_16.setContentsMargins(0, 0, 0, 0)
        self.frame_13 = QFrame(self.tab_6)
        self.frame_13.setObjectName(u"frame_13")
        self.frame_13.setMaximumSize(QSize(16777215, 150))
        self.frame_13.setFrameShape(QFrame.StyledPanel)
        self.frame_13.setFrameShadow(QFrame.Raised)
        self.formLayout_2 = QFormLayout(self.frame_13)
        self.formLayout_2.setObjectName(u"formLayout_2")
        self.label_14 = QLabel(self.frame_13)
        self.label_14.setObjectName(u"label_14")
        self.label_14.setFont(font7)

        self.formLayout_2.setWidget(0, QFormLayout.LabelRole, self.label_14)

        self.contr_describer_ident = QPlainTextEdit(self.frame_13)
        self.contr_describer_ident.setObjectName(u"contr_describer_ident")
        self.contr_describer_ident.setFont(font4)
        self.contr_describer_ident.setStyleSheet(u"background-color: rgb(52, 70, 72);")
        self.contr_describer_ident.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.formLayout_2.setWidget(0, QFormLayout.FieldRole, self.contr_describer_ident)

        self.label_13 = QLabel(self.frame_13)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setFont(font7)

        self.formLayout_2.setWidget(1, QFormLayout.LabelRole, self.label_13)

        self.contr_describer_name = QPlainTextEdit(self.frame_13)
        self.contr_describer_name.setObjectName(u"contr_describer_name")
        self.contr_describer_name.setFont(font4)
        self.contr_describer_name.setStyleSheet(u"background-color: rgb(52, 70, 72);")
        self.contr_describer_name.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.formLayout_2.setWidget(1, QFormLayout.FieldRole, self.contr_describer_name)

        self.label_15 = QLabel(self.frame_13)
        self.label_15.setObjectName(u"label_15")
        self.label_15.setFont(font7)

        self.formLayout_2.setWidget(2, QFormLayout.LabelRole, self.label_15)

        self.contr_describer_role = QPlainTextEdit(self.frame_13)
        self.contr_describer_role.setObjectName(u"contr_describer_role")
        self.contr_describer_role.setFont(font4)
        self.contr_describer_role.setStyleSheet(u"background-color: rgb(90, 90, 90);")
        self.contr_describer_role.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.contr_describer_role.setReadOnly(True)

        self.formLayout_2.setWidget(2, QFormLayout.FieldRole, self.contr_describer_role)


        self.verticalLayout_16.addWidget(self.frame_13)

        self.groupBox_8 = QGroupBox(self.tab_6)
        self.groupBox_8.setObjectName(u"groupBox_8")
        self.groupBox_8.setMinimumSize(QSize(0, 0))
        self.groupBox_8.setMaximumSize(QSize(16777215, 16777215))
        self.groupBox_8.setFont(font6)
        self.horizontalLayout_13 = QHBoxLayout(self.groupBox_8)
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.xmp_dc = QTextEdit(self.groupBox_8)
        self.xmp_dc.setObjectName(u"xmp_dc")
        self.xmp_dc.setFont(font4)
        self.xmp_dc.setStyleSheet(u"background-color: rgb(52, 70, 72);")
        self.xmp_dc.setFrameShape(QFrame.NoFrame)
        self.xmp_dc.setFrameShadow(QFrame.Plain)

        self.horizontalLayout_13.addWidget(self.xmp_dc)


        self.verticalLayout_16.addWidget(self.groupBox_8)

        self.tabWidget_3.addTab(self.tab_6, "")
        self.tab_9 = QWidget()
        self.tab_9.setObjectName(u"tab_9")
        self.verticalLayout_14 = QVBoxLayout(self.tab_9)
        self.verticalLayout_14.setSpacing(0)
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.verticalLayout_14.setContentsMargins(0, 0, 0, 0)
        self.frame_8 = QFrame(self.tab_9)
        self.frame_8.setObjectName(u"frame_8")
        self.frame_8.setMaximumSize(QSize(16777215, 150))
        self.frame_8.setFrameShape(QFrame.StyledPanel)
        self.frame_8.setFrameShadow(QFrame.Raised)
        self.formLayout = QFormLayout(self.frame_8)
        self.formLayout.setObjectName(u"formLayout")
        self.label_26 = QLabel(self.frame_8)
        self.label_26.setObjectName(u"label_26")
        self.label_26.setFont(font7)

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label_26)

        self.contr_transcriber_ident = QPlainTextEdit(self.frame_8)
        self.contr_transcriber_ident.setObjectName(u"contr_transcriber_ident")
        self.contr_transcriber_ident.setFont(font4)
        self.contr_transcriber_ident.setStyleSheet(u"background-color: rgb(52, 70, 72);")
        self.contr_transcriber_ident.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.contr_transcriber_ident)

        self.label_27 = QLabel(self.frame_8)
        self.label_27.setObjectName(u"label_27")
        self.label_27.setFont(font7)

        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label_27)

        self.contr_transcriber_name = QPlainTextEdit(self.frame_8)
        self.contr_transcriber_name.setObjectName(u"contr_transcriber_name")
        self.contr_transcriber_name.setFont(font4)
        self.contr_transcriber_name.setStyleSheet(u"background-color: rgb(52, 70, 72);")
        self.contr_transcriber_name.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.contr_transcriber_name)

        self.label_28 = QLabel(self.frame_8)
        self.label_28.setObjectName(u"label_28")
        self.label_28.setFont(font7)

        self.formLayout.setWidget(2, QFormLayout.LabelRole, self.label_28)

        self.contr_transcriber_role = QPlainTextEdit(self.frame_8)
        self.contr_transcriber_role.setObjectName(u"contr_transcriber_role")
        self.contr_transcriber_role.setFont(font4)
        self.contr_transcriber_role.setStyleSheet(u"background-color: rgb(90, 90, 90);")
        self.contr_transcriber_role.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.contr_transcriber_role.setReadOnly(True)

        self.formLayout.setWidget(2, QFormLayout.FieldRole, self.contr_transcriber_role)


        self.verticalLayout_14.addWidget(self.frame_8)

        self.groupBox_7 = QGroupBox(self.tab_9)
        self.groupBox_7.setObjectName(u"groupBox_7")
        self.groupBox_7.setMinimumSize(QSize(0, 0))
        self.groupBox_7.setMaximumSize(QSize(16777215, 16777215))
        self.groupBox_7.setFont(font6)
        self.horizontalLayout_9 = QHBoxLayout(self.groupBox_7)
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.xmp_dc_transcriber = QTextEdit(self.groupBox_7)
        self.xmp_dc_transcriber.setObjectName(u"xmp_dc_transcriber")
        self.xmp_dc_transcriber.setFont(font4)
        self.xmp_dc_transcriber.setStyleSheet(u"background-color: rgb(52, 70, 72);")
        self.xmp_dc_transcriber.setFrameShape(QFrame.NoFrame)
        self.xmp_dc_transcriber.setFrameShadow(QFrame.Plain)

        self.horizontalLayout_9.addWidget(self.xmp_dc_transcriber)


        self.verticalLayout_14.addWidget(self.groupBox_7)

        self.tabWidget_3.addTab(self.tab_9, "")

        self.verticalLayout_10.addWidget(self.tabWidget_3)


        self.verticalLayout_8.addWidget(self.frame_10)

        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QWidget()
        self.tab_2.setObjectName(u"tab_2")
        self.verticalLayout_9 = QVBoxLayout(self.tab_2)
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.frame_4 = QFrame(self.tab_2)
        self.frame_4.setObjectName(u"frame_4")
        self.frame_4.setFrameShape(QFrame.StyledPanel)
        self.frame_4.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_11 = QHBoxLayout(self.frame_4)
        self.horizontalLayout_11.setSpacing(6)
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.horizontalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_11.addItem(self.horizontalSpacer)

        self.btn_expand_all = QPushButton(self.frame_4)
        self.btn_expand_all.setObjectName(u"btn_expand_all")
        sizePolicy8 = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy8.setHorizontalStretch(0)
        sizePolicy8.setVerticalStretch(0)
        sizePolicy8.setHeightForWidth(self.btn_expand_all.sizePolicy().hasHeightForWidth())
        self.btn_expand_all.setSizePolicy(sizePolicy8)
        self.btn_expand_all.setMaximumSize(QSize(100, 16777215))
        self.btn_expand_all.setLayoutDirection(Qt.RightToLeft)
        self.btn_expand_all.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")

        self.horizontalLayout_11.addWidget(self.btn_expand_all)

        self.btn_collapse_all = QPushButton(self.frame_4)
        self.btn_collapse_all.setObjectName(u"btn_collapse_all")
        sizePolicy8.setHeightForWidth(self.btn_collapse_all.sizePolicy().hasHeightForWidth())
        self.btn_collapse_all.setSizePolicy(sizePolicy8)
        self.btn_collapse_all.setMaximumSize(QSize(100, 16777215))
        self.btn_collapse_all.setLayoutDirection(Qt.RightToLeft)
        self.btn_collapse_all.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")

        self.horizontalLayout_11.addWidget(self.btn_collapse_all)


        self.verticalLayout_9.addWidget(self.frame_4)

        self.image_region_view = QTreeView(self.tab_2)
        self.image_region_view.setObjectName(u"image_region_view")
        self.image_region_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.image_region_view.setStyleSheet(u"QTreeView{alternate-background-color: #222222; background: transparent;}\n"
"\n"
"QTreeView::branch:has-children:!has-siblings:closed,\n"
"QTreeView::branch:closed:has-children:has-siblings {\n"
"        border-image: none;\n"
"        image: url(:/icons/icons/cil-size-grip.png);\n"
"}\n"
"\n"
"QTreeView::branch:open:has-children:!has-siblings,\n"
"QTreeView::branch:open:has-children:has-siblings  {\n"
"        border-image: none;\n"
"        image:url(:/icons/icons/circle.svg);\n"
"}\n"
"\n"
"")
        self.image_region_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.image_region_view.setAlternatingRowColors(True)
        self.image_region_view.setSelectionMode(QAbstractItemView.NoSelection)
        self.image_region_view.setIndentation(40)
        self.image_region_view.header().setVisible(False)
        self.image_region_view.header().setCascadingSectionResizes(False)
        self.image_region_view.header().setMinimumSectionSize(220)
        self.image_region_view.header().setDefaultSectionSize(220)
        self.image_region_view.header().setStretchLastSection(False)

        self.verticalLayout_9.addWidget(self.image_region_view)

        self.tabWidget.addTab(self.tab_2, "")
        self.tab_8 = QWidget()
        self.tab_8.setObjectName(u"tab_8")
        self.verticalLayout_13 = QVBoxLayout(self.tab_8)
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.frame_6 = QFrame(self.tab_8)
        self.frame_6.setObjectName(u"frame_6")
        self.frame_6.setFrameShape(QFrame.StyledPanel)
        self.frame_6.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_12 = QHBoxLayout(self.frame_6)
        self.horizontalLayout_12.setSpacing(6)
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.horizontalLayout_12.setContentsMargins(0, 0, 0, 0)
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)

        self.horizontalLayout_12.addItem(self.horizontalSpacer_2)

        self.btn_expand_all_all_region = QPushButton(self.frame_6)
        self.btn_expand_all_all_region.setObjectName(u"btn_expand_all_all_region")
        sizePolicy8.setHeightForWidth(self.btn_expand_all_all_region.sizePolicy().hasHeightForWidth())
        self.btn_expand_all_all_region.setSizePolicy(sizePolicy8)
        self.btn_expand_all_all_region.setMaximumSize(QSize(100, 16777215))
        self.btn_expand_all_all_region.setLayoutDirection(Qt.RightToLeft)
        self.btn_expand_all_all_region.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")

        self.horizontalLayout_12.addWidget(self.btn_expand_all_all_region)

        self.btn_collapse_all_all_region = QPushButton(self.frame_6)
        self.btn_collapse_all_all_region.setObjectName(u"btn_collapse_all_all_region")
        sizePolicy8.setHeightForWidth(self.btn_collapse_all_all_region.sizePolicy().hasHeightForWidth())
        self.btn_collapse_all_all_region.setSizePolicy(sizePolicy8)
        self.btn_collapse_all_all_region.setMaximumSize(QSize(100, 16777215))
        self.btn_collapse_all_all_region.setLayoutDirection(Qt.RightToLeft)
        self.btn_collapse_all_all_region.setStyleSheet(u"QPushButton {\n"
"	border: 2px solid rgb(52, 59, 72);\n"
"	border-radius: 5px;	\n"
"	background-color: rgb(52, 59, 72);\n"
"}\n"
"QPushButton:hover {\n"
"	background-color: rgb(57, 65, 80);\n"
"	border: 2px solid rgb(61, 70, 86);\n"
"}\n"
"QPushButton:pressed {	\n"
"	background-color: rgb(35, 40, 49);\n"
"	border: 2px solid rgb(43, 50, 61);\n"
"}")

        self.horizontalLayout_12.addWidget(self.btn_collapse_all_all_region)


        self.verticalLayout_13.addWidget(self.frame_6)

        self.image_all_region = QTreeView(self.tab_8)
        self.image_all_region.setObjectName(u"image_all_region")
        self.image_all_region.setContextMenuPolicy(Qt.CustomContextMenu)
        self.image_all_region.setStyleSheet(u"QTreeView{alternate-background-color: #222222; background: transparent;}\n"
"\n"
"QTreeView::branch:has-children:!has-siblings:closed,\n"
"QTreeView::branch:closed:has-children:has-siblings {\n"
"        border-image: none;\n"
"        image: url(:/icons/icons/cil-size-grip.png);\n"
"}\n"
"\n"
"QTreeView::branch:open:has-children:!has-siblings,\n"
"QTreeView::branch:open:has-children:has-siblings  {\n"
"        border-image: none;\n"
"        image:url(:/icons/icons/circle.svg);\n"
"}\n"
"\n"
"")
        self.image_all_region.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)
        self.image_all_region.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.image_all_region.setAlternatingRowColors(True)
        self.image_all_region.setSelectionMode(QAbstractItemView.NoSelection)
        self.image_all_region.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.image_all_region.setIndentation(40)
        self.image_all_region.header().setVisible(False)
        self.image_all_region.header().setCascadingSectionResizes(False)
        self.image_all_region.header().setMinimumSectionSize(220)
        self.image_all_region.header().setDefaultSectionSize(220)
        self.image_all_region.header().setStretchLastSection(False)

        self.verticalLayout_13.addWidget(self.image_all_region)

        self.tabWidget.addTab(self.tab_8, "")

        self.verticalLayout_7.addWidget(self.tabWidget)

        self.splitter_main.addWidget(self.frame_3)

        self.horizontalLayout_2.addWidget(self.splitter_main)


        self.verticalLayout_4.addWidget(self.frame_7)

        self.frame_grip = QFrame(self.frame_center)
        self.frame_grip.setObjectName(u"frame_grip")
        sizePolicy2.setHeightForWidth(self.frame_grip.sizePolicy().hasHeightForWidth())
        self.frame_grip.setSizePolicy(sizePolicy2)
        self.frame_grip.setMinimumSize(QSize(0, 40))
        self.frame_grip.setMaximumSize(QSize(16777215, 40))
        self.frame_grip.setStyleSheet(u"background-color: rgb(33, 37, 43);")
        self.frame_grip.setFrameShape(QFrame.NoFrame)
        self.frame_grip.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_6 = QHBoxLayout(self.frame_grip)
        self.horizontalLayout_6.setSpacing(0)
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.horizontalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.frame_label_bottom = QFrame(self.frame_grip)
        self.frame_label_bottom.setObjectName(u"frame_label_bottom")
        self.frame_label_bottom.setMinimumSize(QSize(0, 40))
        self.frame_label_bottom.setMouseTracking(False)
        self.frame_label_bottom.setAutoFillBackground(False)
        self.frame_label_bottom.setFrameShape(QFrame.NoFrame)
        self.frame_label_bottom.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_7 = QHBoxLayout(self.frame_label_bottom)
        self.horizontalLayout_7.setSpacing(0)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_7.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.horizontalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.label_credits = QLabel(self.frame_label_bottom)
        self.label_credits.setObjectName(u"label_credits")
        self.label_credits.setMaximumSize(QSize(16777215, 40))
        font9 = QFont()
        font9.setFamily(u"Segoe UI")
        self.label_credits.setFont(font9)
        self.label_credits.setCursor(QCursor(Qt.ArrowCursor))
        self.label_credits.setStyleSheet(u"color: rgb(98, 103, 111);")
        self.label_credits.setTextFormat(Qt.RichText)
        self.label_credits.setAlignment(Qt.AlignCenter)
        self.label_credits.setOpenExternalLinks(True)

        self.horizontalLayout_7.addWidget(self.label_credits)

        self.label_version = QLabel(self.frame_label_bottom)
        self.label_version.setObjectName(u"label_version")
        self.label_version.setMaximumSize(QSize(100, 16777215))
        self.label_version.setFont(font9)
        self.label_version.setStyleSheet(u"color: rgb(98, 103, 111);")
        self.label_version.setAlignment(Qt.AlignRight|Qt.AlignTrailing|Qt.AlignVCenter)

        self.horizontalLayout_7.addWidget(self.label_version)

        self.frame_size_grip = QFrame(self.frame_label_bottom)
        self.frame_size_grip.setObjectName(u"frame_size_grip")
        self.frame_size_grip.setMaximumSize(QSize(20, 20))
        self.frame_size_grip.setStyleSheet(u"QSizeGrip {\n"
"	background-image: url(:/icons/icons/cil-size-grip.png);\n"
"	background-position: center;\n"
"	background-repeat: no-reperat;\n"
"}")
        self.frame_size_grip.setFrameShape(QFrame.NoFrame)
        self.frame_size_grip.setFrameShadow(QFrame.Raised)

        self.horizontalLayout_7.addWidget(self.frame_size_grip)


        self.horizontalLayout_6.addWidget(self.frame_label_bottom)


        self.verticalLayout_4.addWidget(self.frame_grip)


        self.verticalLayout.addWidget(self.frame_center)


        self.horizontalLayout.addWidget(self.frame_main)

        MainWindow.setCentralWidget(self.centralwidget)
        QWidget.setTabOrder(self.btn_minimize, self.btn_maximize_restore)
        QWidget.setTabOrder(self.btn_maximize_restore, self.btn_close)

        self.retranslateUi(MainWindow)

        self.tabWidget_2.setCurrentIndex(0)
        self.tabWidget.setCurrentIndex(0)
        self.tabWidget_3.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.label_6.setText("")
        self.toolButton.setText(QCoreApplication.translate("MainWindow", u"MENU", None))
        self.lbl_sqlite_name.setText("")
#if QT_CONFIG(tooltip)
        self.label_title_bar_top.setToolTip(QCoreApplication.translate("MainWindow", u"Move window", None))
#endif // QT_CONFIG(tooltip)
        self.label_title_bar_top.setText("")
#if QT_CONFIG(tooltip)
        self.btn_minimize.setToolTip(QCoreApplication.translate("MainWindow", u"Minimize", None))
#endif // QT_CONFIG(tooltip)
        self.btn_minimize.setText("")
#if QT_CONFIG(tooltip)
        self.btn_maximize_restore.setToolTip(QCoreApplication.translate("MainWindow", u"Maximize", None))
#endif // QT_CONFIG(tooltip)
        self.btn_maximize_restore.setText("")
#if QT_CONFIG(tooltip)
        self.btn_close.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Close</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.btn_close.setText("")
        self.groupBox.setTitle(QCoreApplication.translate("MainWindow", u"Database statistics", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"Polygons", None))
        self.lbl_polygon_number.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"Rectangles", None))
        self.lbl_circle_number.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.label_18.setText(QCoreApplication.translate("MainWindow", u"Circles", None))
        self.lbl_rectangle_number.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.label_5.setText(QCoreApplication.translate("MainWindow", u"Nr. of  images", None))
        self.lbl_image_number.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("MainWindow", u"Region appearance", None))
        self.btn_color_polygon.setText("")
        self.btn_color_circle.setText("")
        self.btn_color_rectangle.setText("")
        self.btn_show_polygon.setText("")
        self.btn_show_circle.setText("")
        self.btn_show_rectangle.setText("")
        self.groupBox_2.setTitle(QCoreApplication.translate("MainWindow", u"Region operations", None))
        self.btn_create_circle.setText("")
        self.btn_create_rectangle.setText("")
        self.btn_create_polygon.setText("")
        self.btn_geometry_move.setText("")
        self.btn_geometry_resize.setText("")
        self.btn_geometry_remove.setText("")
        self.plainTextEdit.setPlainText(QCoreApplication.translate("MainWindow", u"https://projectindigo.eu/\n"
"\n"
"With this tool you can add and change IPTC Image Regions and add/change XMP tags to that region. All images from an folder will be loaded. All changes will be saved in a SQLITE database. Saving IPTC Regions back to images is possible.\n"
"@Martin Wieser \n"
"\n"
"Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the \u201cSoftware\u201d), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:\n"
"The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.\n"
"THE SOFTWARE IS PROVIDED \u201cAS IS\u201d, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHAN"
                        "TABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.", None))
        self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.tab_3), "")
        self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.tab_4), "")
        self.lbl_image_name.setText("")
        self.lbl_image_path.setText("")
        self.groupBox_9.setTitle(QCoreApplication.translate("MainWindow", u"User information", None))
        self.label_17.setText(QCoreApplication.translate("MainWindow", u"Name", None))
        self.label_16.setText(QCoreApplication.translate("MainWindow", u"Identifier", None))
        self.btn_object_save.setText("")
        self.groupBox_5.setTitle(QCoreApplication.translate("MainWindow", u"Region", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Region Identifier", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"Region Name", None))
        self.groupBox_11.setTitle(QCoreApplication.translate("MainWindow", u"Region Role", None))
        self.label_21.setText(QCoreApplication.translate("MainWindow", u"Identifier", None))
        self.label_22.setText(QCoreApplication.translate("MainWindow", u"Name", None))
        self.groupBox_10.setTitle(QCoreApplication.translate("MainWindow", u"Region Content Type", None))
        self.label_19.setText(QCoreApplication.translate("MainWindow", u"Identifier", None))
        self.label_20.setText(QCoreApplication.translate("MainWindow", u"Name", None))
        self.label_11.setText(QCoreApplication.translate("MainWindow", u"Identifier", None))
        self.label_10.setText(QCoreApplication.translate("MainWindow", u"Name", None))
        self.label_12.setText(QCoreApplication.translate("MainWindow", u"Role", None))
        self.tabWidget_3.setTabText(self.tabWidget_3.indexOf(self.tab_7), QCoreApplication.translate("MainWindow", u"Region Creator", None))
        self.label_14.setText(QCoreApplication.translate("MainWindow", u"Identifier", None))
        self.label_13.setText(QCoreApplication.translate("MainWindow", u"Name", None))
        self.label_15.setText(QCoreApplication.translate("MainWindow", u"Role", None))
        self.groupBox_8.setTitle(QCoreApplication.translate("MainWindow", u"XMP-DC Description", None))
        self.xmp_dc.setHtml(QCoreApplication.translate("MainWindow", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:'MS Shell Dlg 2'; font-size:10pt; font-weight:400; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:8.25pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:8.25pt;\"><br /></p></body></html>", None))
        self.tabWidget_3.setTabText(self.tabWidget_3.indexOf(self.tab_6), QCoreApplication.translate("MainWindow", u"Description", None))
        self.label_26.setText(QCoreApplication.translate("MainWindow", u"Identifier", None))
        self.label_27.setText(QCoreApplication.translate("MainWindow", u"Name", None))
        self.label_28.setText(QCoreApplication.translate("MainWindow", u"Role", None))
        self.groupBox_7.setTitle(QCoreApplication.translate("MainWindow", u"XMP-DC Title", None))
        self.xmp_dc_transcriber.setHtml(QCoreApplication.translate("MainWindow", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:'MS Shell Dlg 2'; font-size:10pt; font-weight:400; font-style:normal;\">\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:8.25pt;\"><br /></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; font-size:8.25pt;\"><br /></p></body></html>", None))
        self.tabWidget_3.setTabText(self.tabWidget_3.indexOf(self.tab_9), QCoreApplication.translate("MainWindow", u"Transcription", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), QCoreApplication.translate("MainWindow", u"Change region info", None))
        self.btn_expand_all.setText(QCoreApplication.translate("MainWindow", u"Expand all", None))
        self.btn_collapse_all.setText(QCoreApplication.translate("MainWindow", u"Collapse all", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), QCoreApplication.translate("MainWindow", u"View region info", None))
        self.btn_expand_all_all_region.setText(QCoreApplication.translate("MainWindow", u"Expand all", None))
        self.btn_collapse_all_all_region.setText(QCoreApplication.translate("MainWindow", u"Collapse all", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_8), QCoreApplication.translate("MainWindow", u"All region info", None))
        self.label_credits.setText(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Graphis @ Indigo 2023 - https://projectindigo.eu/</p></body></html>", None))
        self.label_version.setText(QCoreApplication.translate("MainWindow", u"v1.2", None))
#if QT_CONFIG(tooltip)
        self.frame_size_grip.setToolTip(QCoreApplication.translate("MainWindow", u"<html><head/><body><p>Change window size</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
    # retranslateUi

