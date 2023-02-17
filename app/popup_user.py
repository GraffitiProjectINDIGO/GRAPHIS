import pickle
import os
from PySide2 import QtCore
from PySide2.QtWidgets import *

from app.ui_user import Ui_popup_user


class POPUPUser(QWidget):

    got_user = QtCore.Signal(str, str)

    def __init__(self):
        QWidget.__init__(self, parent=None)
        self.ui3 = Ui_popup_user()
        self.ui3.setupUi(self)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.ui3.save_user.clicked.connect(self.save_user)
        self.user_dict = {}

        try:
            if os.path.exists("user.pickle"):
                fid = open("user.pickle", 'rb')
                self.user_dict = pickle.load(fid)

                for users in self.user_dict:
                    self.ui3.combo_user.addItem(users)
                fid.close()
            else:
                self.ui3.combo_user.show(False)
        except:
            pass

        self.ui3.combo_user.currentIndexChanged.connect(self.change_user)

    def change_user(self):
        user = self.sender().currentText()
        if user != 'Choose existing User':
            self.ui3.input_user.setText(user)
            self.ui3.input_uri.setText(self.user_dict[user])

    def save_user(self):
        if not self.ui3.input_user.text().lower() == 'your name':
            uri = ''
            if not self.ui3.input_uri.text().lower() == 'uri/orcid':
                uri = self.ui3.input_uri.text().lower()
            self.got_user.emit(self.ui3.input_user.text().lower(), uri)


            self.user_dict[self.ui3.input_user.text()]=uri

            try:
                fid = open("user.pickle", 'wb')
                pickle.dump(self.user_dict, fid)
            except:
                pass

            self.close()
        else:
            self.ui3.user_error.setText('Please enter your name')
