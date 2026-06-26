#!/usr/bin/python3
# -*- coding: utf-8 -*-

from config.app import App
from PySide2.QtCore import *
from PySide2.QtWidgets import QMainWindow, QMessageBox
from PySide2.QtGui import QIcon

from view.uiresize import Ui_Resize
from view.messages import Message

from segmentacion_core.model.folder import Folder

__email__ = "oscarmtzp93@gmail.com"
__license__ = "GPL"
__maintainer__ = "Oscar Martinez"
__status__ = "Developing"

__version__ = "1.0"

__date__ = "jan/30/2022"

__author__ = "Oscar Martinez"

__credits__ = "UDG"


class ControllerResize(QMainWindow):
    """Class description (DocString)"""

    # ______________________________MAGIC METHODS______________________________

    # _____________________________Generic methods_____________________________

    def __init__(self, parent=None, folder: Folder = None):
        """Method description  (DocString)"""
        super(ControllerResize, self).__init__(parent=parent)

        self.__folder = folder

        self.__setup = Ui_Resize()
        self.__setup.setupUi(self)
        self.__design()
        self.__listen_events()

    # _____________________________Generic methods_____________________________

    # ______________________________MAGIC METHODS______________________________

    # _____________________________Private methods_____________________________

    def __design(self):
        """Create or modify the initial design of the form."""
        icon = QIcon("img/resize.png")
        self.setWindowIcon(icon)

        self.setWindowTitle(QCoreApplication.translate("Resize", App._text['resize'], None))
        self.__update_labels_percentage()

    def __listen_events(self):
        """Puts all the events of the form to listen."""
        # self.__setup.spn_origin_x.valueChanged.connect(self.public_method)
        #
        # self.__setup.btn_add.clicked.connect(self.public_method)
        #
        self.__setup.btn_cancel.clicked.connect(self.close)
        self.__setup.btn_accept.clicked.connect(self.__resize_images)
        #
        self.__setup.hsl_porcenaje.valueChanged.connect(self.__update_percentage)
        #
        # self.__setup.txt_search.returnPressed.connect(self.public_method)
        # self.__setup.txt_search.textEdited.connect(self.public_method)
        #
        # self.__setup.ckb_next.stateChanged.connect(self.public_method)
        # self.__setup.cbo_id.currentIndexChanged.connect(self.public_method)
        # self.__setup.sld_size.valueChanged.connect(self.public_method)
        pass

    def __update_labels_percentage(self) -> None:
        """Description."""
        shape = self.__folder.images[0].data.shape
        self.__setup.lbl_actual_size.setText(f'{shape[1]} x {shape[0]} %')

        width = int(self.__folder.images[0].data.shape[1] * self.__setup.hsl_porcenaje.value() / 100)
        height = int(self.__folder.images[0].data.shape[0] * self.__setup.hsl_porcenaje.value() / 100)

        self.__setup.lbl_final_size.setText(f'{width} x {height} %')

    def __update_percentage(self, value: int) -> None:
        """Description."""
        self.__update_labels_percentage()
        self.__setup.lbl_porcentaje.setText(f'{value} %')

    def __resize_images(self, event) -> None:
        """Description."""
        if Message.resize(self):
            scale = self.__setup.hsl_porcenaje.value() / 100
            for img in self.__folder.images:
                img.scale(scale, scale)

            self.__update_labels_percentage()
            Message.resize_images(self)

    # _____________________________Private methods_____________________________

    # _____________________________Public methods______________________________

    def closeEvent(self, event):
        """It requests the user's confirmation to close the system."""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(App._text['close_window'])
        box.setText(App._text['msg_close_window'])
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        btn_y = box.button(QMessageBox.Yes)
        btn_y.setText(App._text['yes'])
        btn_n = box.button(QMessageBox.No)
        btn_n.setText(App._text['no'])
        box.exec_()

        if box.clickedButton() == btn_y:
            event.accept()
        else:
            event.ignore()

    def show_window(self, event):
        """Method description (DocString)"""
        pass

    # _____________________________Public methods______________________________
