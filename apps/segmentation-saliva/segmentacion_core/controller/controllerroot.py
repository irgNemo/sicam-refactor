#!/usr/bin/python3
# -*- coding: utf-8 -*-

import threading
import os
import openpyxl
import cv2
import pickle
import numpy as np
from PySide2.QtCore import *
from PySide2.QtWidgets import QMainWindow, QMessageBox, QFileDialog, QTreeWidgetItem, QTableWidgetItem
from PySide2.QtGui import QIcon, QBrush, QColor, QPixmap

from segmentacion_core.cellpose import models

from config.app import App

from view.uiroot import Ui_Root
from view.messages import Message

from segmentacion_core.model.mask import Mask
from segmentacion_core.model.image import Image
from segmentacion_core.model.folder import Folder

from controller.controllerresize import ControllerResize

__email__ = "oscarmtzp93@gmail.com"
__license__ = "GPL"
__maintainer__ = "Oscar Martinez"
__status__ = "Developing"

__version__ = "1.0"

__date__ = "nov/30/2021"

__author__ = "Oscar Martinez"

__credits__ = "UDG"


class ControllerRoot(QMainWindow):
    """Class description (DocString)"""

    # ______________________________MAGIC METHODS______________________________

    # _____________________________Generic methods_____________________________

    def __init__(self, parent=None):
        """Method description  (DocString)"""
        super(ControllerRoot, self).__init__(parent=parent)

        self.__folder = None
        self.__was_runned = False
        self.__img_selected = None
        self.__img_obj_selected = None
        self.__processors = os.cpu_count() // 2
        self.__max_threads = 8

        self.__setup = Ui_Root()
        self.__setup.setupUi(self)
        self.__design()
        self.__listen_events()
        self.__clear_tbl_summary()

    # _____________________________Generic methods_____________________________

    # ______________________________MAGIC METHODS______________________________

    # _____________________________Private methods_____________________________

    def __design(self):
        """Create or modify the initial design of the form."""
        icon = QIcon("img/cell.png")
        self.setWindowIcon(icon)

        self.setWindowTitle(QCoreApplication.translate("Root", App._text['root'], None))

        self.__setup.twg_folder.clear()

    def __listen_events(self):
        """Puts all the events of the form to listen."""
        # self.__setup.spn_origin_x.valueChanged.connect(self.public_method)
        #
        self.__setup.btn_run.clicked.connect(self.__run)
        #
        # self.__setup.rdb_speed.clicked.connect(self.public_method)
        #
        self.__setup.act_folder.triggered.connect(self.__select_folder)
        self.__setup.act_export_images.triggered.connect(self.__export_images)
        self.__setup.act_create_report.triggered.connect(self.__create_report)
        self.__setup.act_resize_images.triggered.connect(self.__resize_images)
        #self.__setup.act_select_processors.triggered.connect(self.__select_processors)
        self.__setup.act_export_study.triggered.connect(self.__export_study)
        self.__setup.act_import_study.triggered.connect(self.__import_study)
        self.__setup.act_about.triggered.connect(self.__about)
        #self.__setup.act_jaccard_index.triggered.connect(self.__jaccard_index)
        self.__setup.act_export_mask_nucleus.triggered.connect(self.__export_mask_nucleus)
        self.__setup.act_export_mask_micronucleus.triggered.connect(self.__export_mask_micronucleus)
        self.__setup.act_jaccard_index.triggered.connect(self.__jaccard_index)
        self.__setup.act_oscar_index.triggered.connect(self.__oscar_index)
        #self.__setup.act_jaccard_micronucleus.triggered.connect(self.__jaccard_micronucleus)
        #
        self.__setup.twg_folder.itemClicked.connect(self.__select_image_tree)
        # self.__setup.txt_search.returnPressed.connect(self.public_method)
        # self.__setup.txt_search.textEdited.connect(self.public_method)
        #
        self.__setup.chb_cytos.stateChanged.connect(self.__draw_image_selected)
        self.__setup.chb_nucleis.stateChanged.connect(self.__draw_image_selected)
        self.__setup.chb_micronucleis.stateChanged.connect(self.__draw_image_selected)
        # self.__setup.cbo_id.currentIndexChanged.connect(self.public_method)
        # self.__setup.sld_size.valueChanged.connect(self.public_method)
        pass

    def __about(self) -> None:
        """Description"""
        Message.about(self)

    def __compare_manual_automatic(self, coords_manual: list, coords_automatic: list, img_manual: np.ndarray, img_automatic: np.ndarray) -> int:
        """Compara 2 listas de puntos con los elementos (y_min, y_max, x_min, x_max),
        y determina el numero de elementos que coinciden"""

        margin_pixels = 5
        tp = 0
        for i, coord_manual in reversed(list(enumerate(coords_manual))):
            for j, coord_automatic in reversed(list(enumerate(coords_automatic))):
                if coord_manual[0] - margin_pixels <= coord_automatic[0] <= coord_manual[0] + margin_pixels:
                    if coord_manual[1] - margin_pixels <= coord_automatic[1] <= coord_manual[1] + margin_pixels:
                        if coord_manual[2] - margin_pixels <= coord_automatic[2] <= coord_manual[2] + margin_pixels:
                            if coord_manual[3] - margin_pixels <= coord_automatic[3] <= coord_manual[3] + margin_pixels:
                                coords_manual.pop(i)
                                coords_automatic.pop(j)
                                tp += 1
                                """manual = img_manual[coord_manual[0]: coord_manual[1], coord_manual[2]: coord_manual[3]]
                                automatic = img_automatic[coord_automatic[0]: coord_automatic[1], coord_automatic[2]: coord_automatic[3]]

                                cv2.imshow('manual', manual)
                                cv2.imshow('automatic', automatic)
                                cv2.waitKey(0)"""
        return tp

    def __oscar_index(self) -> None:
        """Description."""
        tp = 0
        fp = 0
        fn = 0

        # Selecionar carpetas donde se encuentran las imagenes
        path = QStandardPaths.standardLocations(
            QStandardPaths.DesktopLocation)
        folder_path_mask = QFileDialog.getExistingDirectory(self, "Select automatic segmentation (jpg)", path[0])
        folder_path_mask_2 = QFileDialog.getExistingDirectory(self, "Select manual segmentation (npy)", path[0])
        #

        # Cargar imagenes en memoria
        imgs_name = os.listdir(folder_path_mask)
        path_imgs = [folder_path_mask + '/' + p for p in imgs_name if p[-4:] == '.jpg']
        #

        intersection = 0
        union = 0

        # Recorre las imagenes de segmentación automatica
        for i in range(path_imgs.__len__()):
            img_name = imgs_name[i][0:2]
            try:
                img_automatic = cv2.imread(path_imgs[i], cv2.IMREAD_GRAYSCALE)
                image = Image(img_name)
                image.upload_mask_nucleus(f'{folder_path_mask_2}/{img_name}_seg.npy')
                mask_manual = image.mask_nucleus.data

                contours_manual, _ = cv2.findContours(mask_manual, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

                coord_manual = []
                # Recorre los elementos de la imagen manual y los almacena en coord_manual
                for i in contours_manual:
                    x_max = i[:, :, 0].max()
                    y_max = i[:, :, 1].max()
                    x_min = i[:, :, 0].min()
                    y_min = i[:, :, 1].min()

                    coord_manual.append((y_min, y_max, x_min, x_max))
                #

                # Recorre los elementos de la imagen automatica y los almacena en coord_automatic
                _, img_automatic = cv2.threshold(img_automatic, 10, 255, cv2.THRESH_BINARY)
                contours_automatic, _ = cv2.findContours(img_automatic, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

                coord_automatic = []
                for j in contours_automatic:
                    x_max = j[:, :, 0].max()
                    y_max = j[:, :, 1].max()
                    x_min = j[:, :, 0].min()
                    y_min = j[:, :, 1].min()

                    coord_automatic.append((y_min, y_max, x_min, x_max))

                    '''img_element = img_automatic[y_min: y_max, x_min: x_max]
                    cv2.imshow('element', img_element)
                    cv2.waitKey(0)'''
                #

                # Compara
                tp += self.__compare_manual_automatic(coord_manual, coord_automatic, mask_manual, img_automatic)
                fn += coord_manual.__len__()
                fp += coord_automatic.__len__()



                '''img_intersection = img_cellanalyzer & mask_manual
                img_union = img_cellanalyzer | mask_manual
                _intersection = np.count_nonzero(img_intersection)
                _union = np.count_nonzero(img_union)
    
                print(f"{img_name}: manual={np.count_nonzero(mask_manual)} "
                      f"cellanalyzer={np.count_nonzero(img_cellanalyzer)}... "
                      f"{_intersection} / {_union} = {_intersection / _union}")
                intersection += _intersection
                union += _union'''

            except FileNotFoundError:
                print(img_name + " sin máscara manual")

        print(f"TP>Segmentadas correctamente: {tp}")
        print(f"FN>No encontradas por cellanalyzer: {fn}")
        print(f"FP>Segmentadas incorrectamente: {fp}")

    def __jaccard_index(self) -> None:
        """Description."""
        path = QStandardPaths.standardLocations(
            QStandardPaths.DesktopLocation)
        folder_path_mask = QFileDialog.getExistingDirectory(self, "Select automatic segmentation (jpg)", path[0])
        folder_path_mask_2 = QFileDialog.getExistingDirectory(self, "Select manual segmentation (npy)", path[0])

        imgs_name = os.listdir(folder_path_mask)
        path_imgs = [folder_path_mask + '/' + p for p in imgs_name if p[-4:] == '.jpg']

        intersection = 0
        union = 0

        for i in range(path_imgs.__len__()):
            img_name = imgs_name[i][0:2]
            try:
                img_cellanalyzer = cv2.imread(path_imgs[i], cv2.IMREAD_GRAYSCALE)
                image = Image(img_name)
                image.upload_mask_nucleus(f'{folder_path_mask_2}/{img_name}_seg.npy')
                mask_manual = image.mask_nucleus.data

                img_intersection = img_cellanalyzer & mask_manual
                img_union = img_cellanalyzer | mask_manual
                _intersection = np.count_nonzero(img_intersection)
                _union = np.count_nonzero(img_union)

                """print(f"{img_name}: manual={np.count_nonzero(mask_manual)} "
                      f"cellanalyzer={np.count_nonzero(img_cellanalyzer)}... "
                      f"{_intersection} / {_union} = {_intersection / _union}")"""

                print(f"{img_name}, {_intersection / _union}")
                intersection += _intersection
                union += _union

            except:
                pass
                #print(img_name + " sin máscara manual")

        #print(f"total: {intersection / union}")
        print(f"total, {intersection / union}")

    def __export_mask_nucleus(self) -> None:
        """Description."""
        if self.__folder == None:
            Message.no_images(self)
        elif not self.__was_runned:
            Message.was_not_runned(self)
        else:
            path = QStandardPaths.standardLocations(
                QStandardPaths.DesktopLocation)
            folder_path = QFileDialog.getExistingDirectory(self, App._text["select_folder_to_save"], path[0])

            if folder_path:
                for img in self.__folder.images:
                    cv2.imwrite(f'{folder_path}/{img.name}_mask_nucleus.jpg', img.get_masks(0b0100))
                Message.images_were_exported(self)

    def __export_mask_micronucleus(self) -> None:
        """Description."""
        if self.__folder == None:
            Message.no_images(self)
        elif not self.__was_runned:
            Message.was_not_runned(self)
        else:
            path = QStandardPaths.standardLocations(
                QStandardPaths.DesktopLocation)
            folder_path = QFileDialog.getExistingDirectory(self, App._text["select_folder_to_save"], path[0])

            if folder_path:
                for img in self.__folder.images:
                    cv2.imwrite(f'{folder_path}/{img.name}_mask_micronucleus.jpg', img.get_masks(0b1000))
                Message.images_were_exported(self)

    def __resize_images(self) -> None:
        """Description."""
        if not self.__was_runned:
            if threading.active_count() <= self.__max_threads:
                if self.__folder == None or not self.__folder.images:
                    Message.no_images_resize(self)
                else:
                    controller_resize = ControllerResize(self, self.__folder)
                    controller_resize.show()
            else:
                Message.segmentation_is_runnig(self)
        else:
            Message.no_resize(self)

    def __export_images(self) -> None:
        """Description."""
        if self.__folder == None:
            Message.no_images(self)
        else:
            path = QStandardPaths.standardLocations(
                QStandardPaths.DesktopLocation)
            folder_path = QFileDialog.getExistingDirectory(self, App._text["select_folder_to_save"], path[0])

            if folder_path:
                flag_mask = 0b0001

                if self.__setup.chb_cytos.isChecked():
                    flag_mask |= 0b0010

                if self.__setup.chb_nucleis.isChecked():
                    flag_mask |= 0b0100

                if self.__setup.chb_micronucleis.isChecked():
                    flag_mask |= 0b1000

                for image in self.__folder.images:
                    image.save(folder_path, flag_mask)

                Message.images_were_exported(self)

    def __export_study(self) -> None:
        """Description."""
        if threading.active_count() <= self.__max_threads:
            if self.__folder == None:
                Message.no_images(self)
            else:
                path = QStandardPaths.standardLocations(
                    QStandardPaths.DesktopLocation)
                folder_path = QFileDialog.getExistingDirectory(self, App._text["select_folder_to_save"], path[0])

                if folder_path:
                    #self.__folder.save(folder_path, self.__setup.twg_folder.headerItem().text(0))
                    with open(folder_path + "/" + self.__setup.twg_folder.headerItem().text(0) + ".caz", "wb") as f:
                        pickle.dump(self.__folder, f)
                    Message.study_was_exported(self)
        else:
            Message.segmentation_is_runnig(self)

    def __import_study(self) -> None:
        """Description."""
        if threading.active_count() <= self.__max_threads:
            path = QStandardPaths.standardLocations(
                QStandardPaths.DesktopLocation)
            file_path = QFileDialog.getOpenFileName(self, App._text["select_folder_to_save"], path[0], "*.caz")[0]

            if file_path:
                try:
                    with open(file_path, "rb") as f:
                        folder = pickle.load(f)
                    f.close()

                    self.__folder = folder
                    self.__add_elements_tree_folder()
                    self.__clear_tbl_summary()
                    self.__write_resume()
                    self.__was_runned = folder.was_segmented
                    Message.study_was_imported(self)
                except:
                    Message.file_corrupt(self)
        else:
            Message.segmentation_is_runnig(self)

    def __create_report(self) -> None:
        """Description."""
        if threading.active_count() <= self.__max_threads:
            if self.__folder == None:
                Message.no_images_report(self)

            elif not self.__was_runned:
                Message.was_not_runned(self)

            else:
                path = QStandardPaths.standardLocations(
                    QStandardPaths.DesktopLocation)
                folder_path = QFileDialog.getExistingDirectory(self, App._text["select_folder_to_save"], path[0])

                folder_name = self.__setup.twg_folder.headerItem().text(0)

                if folder_path:
                    wb = openpyxl.Workbook()
                    sheet = wb.active

                    sheet.append(("Indice de citotoxicidad", ))
                    sheet.append(("Indice de genotoxicidad", ))
                    sheet.append(("Grupo", "Imágen", "Citoplasmas", "Núcleos", "Binucleadas", "Trinucleadas", "Micronúcleos"))

                    cytoplams = 0
                    nucleus = 0
                    binucleate = 0
                    trinucleate = 0
                    micronucleus = 0

                    for img in self.__folder.images:
                        record = (folder_name,
                                  img.name,
                                  img.mask_cytoplasm.elements.__len__(),
                                  img.mask_nucleus.total_elements,
                                  img.mask_nucleus.total_binucleate,
                                  img.mask_nucleus.total_trinucleate,
                                  img.mask_micronucleus.total_micronucleus)

                        cytoplams += img.mask_cytoplasm.elements.__len__()
                        nucleus += img.mask_nucleus.total_elements
                        binucleate += img.mask_nucleus.total_binucleate
                        trinucleate += img.mask_nucleus.total_trinucleate
                        micronucleus += img.mask_micronucleus.total_micronucleus

                        sheet.append(record)

                    sheet.append(("Total", "", cytoplams, nucleus, binucleate, trinucleate, micronucleus))
                    if cytoplams:
                        sheet["B1"] = (binucleate + trinucleate) / cytoplams
                        sheet["B2"] = micronucleus / cytoplams
                    else:
                        sheet["B1"] = "Indeterminación"
                        sheet["B2"] = "Indeterminación"

                    wb.save(folder_path + "/" + folder_name + ".xlsx")

                    Message.report_created(self)
        else:
            Message.segmentation_is_runnig(self)

    def __clear_tbl_summary(self) -> None:
        """Description."""
        for r in range(self.__setup.tbl_summary.rowCount()):
            for c in range(self.__setup.tbl_summary.columnCount()):
                item = self.__setup.tbl_summary.item(r, c)
                if item:
                    item.setText(QCoreApplication.translate("Root", u"", None))

    def __add_elements_tree_folder(self) -> None:
        """Description."""

        self.__setup.twg_folder.clear()

        folder_path = self.__folder.path
        if folder_path[-1] == '/':
            folder_path = folder_path[:-1]

        folder_name = folder_path[folder_path.rfind('/') + 1:]

        widget_header = self.__setup.twg_folder.headerItem()
        widget_header.setText(0, QCoreApplication.translate("Root", folder_name, None));

        for i, image in enumerate(self.__folder.images):
            brush = QBrush(QColor(0, 255, 0, 255))
            brush.setStyle(Qt.NoBrush)

            widget_item = QTreeWidgetItem(self.__setup.twg_folder)
            widget_item.setBackground(0, brush);
            widget_item.setText(0, QCoreApplication.translate("Root", image.name, None))

    def __select_folder(self, event) -> None:
        """Description."""
        if threading.active_count() <= self.__max_threads:
            path = QStandardPaths.standardLocations(
                QStandardPaths.DesktopLocation)
            folder_path = QFileDialog.getExistingDirectory(self, App._text["select_folder"], path[0])

            if folder_path:
                self.__folder = Folder(folder_path)
                self.__folder.upload_images()

                self.__add_elements_tree_folder()
                self.__clear_tbl_summary()

                self.__was_runned = False
                self.__folder.was_segmented = False

        else:
            Message.segmentation_is_runnig(self)

    def __draw_image(self) -> None:
        """Description"""
        if self.__img_selected:
            size = self.__setup.lbl_image.size()
            img = self.__img_selected.scaled(size.width(), size.height())
            self.__setup.lbl_image.setPixmap(img)

    def __write_resume(self) -> None:
        """Description."""
        cytoplasms = 0
        nucleus = 0
        binucleus = 0
        trinucleus = 0
        micronucleus = 0

        for i in self.__folder.images:
            cytoplasms += i.mask_cytoplasm.elements.__len__()
            nucleus += i.mask_nucleus.total_elements
            binucleus += i.mask_nucleus.total_binucleate
            trinucleus += i.mask_nucleus.total_trinucleate
            micronucleus += i.mask_micronucleus.total_micronucleus

        citotoxicity_index, genotoxicity_index = self.__folder.calculate_indices()

        item_cytos = QTableWidgetItem(str(cytoplasms))
        item_nucleus = QTableWidgetItem(str(nucleus))
        item_binucleus = QTableWidgetItem(str(binucleus))
        item_trinucleus = QTableWidgetItem(str(trinucleus))
        item_micronucleus = QTableWidgetItem(str(micronucleus))
        item_citotoxicity = QTableWidgetItem(str(citotoxicity_index)[0:7])
        item_genotoxicity = QTableWidgetItem(str(genotoxicity_index)[0:7])

        self.__setup.tbl_summary.setItem(1, 0, item_cytos)
        self.__setup.tbl_summary.setItem(1, 1, item_nucleus)
        self.__setup.tbl_summary.setItem(1, 2, item_binucleus)
        self.__setup.tbl_summary.setItem(1, 3, item_trinucleus)
        self.__setup.tbl_summary.setItem(1, 4, item_micronucleus)
        self.__setup.tbl_summary.setItem(1, 5, item_citotoxicity)
        self.__setup.tbl_summary.setItem(1, 6, item_genotoxicity)

    def __select_image_tree(self, event):
        """Description..."""
        self.__img_selected = None
        self.__img_obj_selected = None
        for i in self.__folder.images:
            if event.text(0) == i.name:
                self.__img_obj_selected = i
                self.__draw_image_selected()

    def __draw_image_selected(self) -> None:
        """Description."""
        if self.__img_obj_selected != None:
            flag_mask = 0b0001

            if self.__was_runned:
                if self.__setup.chb_cytos.isChecked():
                    flag_mask |= 0b0010

                if self.__setup.chb_nucleis.isChecked():
                    flag_mask |= 0b0100

                if self.__setup.chb_micronucleis.isChecked():
                    flag_mask |= 0b1000

            path = QStandardPaths.standardLocations(QStandardPaths.DesktopLocation)[0]
            index = path.rfind('/')
            path = path[:index + 1] + 'cellanalizer/'
            os.makedirs(path, exist_ok=True)

            self.__img_obj_selected.save(path, flag_mask)

            self.__img_selected = QPixmap(path + self.__img_obj_selected.name + '.jpg')
            self.__draw_image()

            item_cytos = QTableWidgetItem(str(self.__img_obj_selected.mask_cytoplasm.elements.__len__()))
            item_nucleus = QTableWidgetItem(str(self.__img_obj_selected.mask_nucleus.total_elements))
            item_micronucleus = QTableWidgetItem(str(self.__img_obj_selected.mask_micronucleus.total_micronucleus))
            item_binucleus = QTableWidgetItem(str(self.__img_obj_selected.mask_nucleus.total_binucleate))
            item_trinucleus = QTableWidgetItem(str(self.__img_obj_selected.mask_nucleus.total_trinucleate))

            self.__setup.tbl_summary.setItem(0, 0, item_cytos)
            self.__setup.tbl_summary.setItem(0, 1, item_nucleus)
            self.__setup.tbl_summary.setItem(0, 2, item_binucleus)
            self.__setup.tbl_summary.setItem(0, 3, item_trinucleus)
            self.__setup.tbl_summary.setItem(0, 4, item_micronucleus)

    def __split_image_list(self, num_processes: int) -> list:
        """Description."""
        images = self.__folder.get_images_data()
        images_split = []
        index_image = 0
        num_images = self.__folder.images.__len__()

        quotient = num_images // num_processes
        remainder = num_images % num_processes

        for i in range(num_processes):
            if remainder:
                batch_len = quotient + 1
                remainder -= 1
            else:
                batch_len = quotient

            aux_images = images[index_image:index_image+batch_len]
            images_split.append(aux_images)
            index_image += batch_len

        return images_split

    def __controller_processes(self):
        """Description"""
        self.__was_runned = True
        self.__folder.was_segmented = True

        #with multiprocessing.Pool(self.__processors) as p:
        #    images = p.map(self.__segmentation, self.__split_image_list(self.__processors))
        images = self.segmentation(self.__folder.get_images_data())

        for i, image in enumerate(images):
            self.__folder.images[i].mask_cytoplasm = image.mask_cytoplasm
            self.__folder.images[i].mask_nucleus = image.mask_nucleus
            self.__folder.images[i].mask_micronucleus = image.mask_micronucleus
        '''index = 0
        for i in images:
            for image in i:
                self.__folder.images[index].mask_cytoplasm = image.mask_cytoplasm
                self.__folder.images[index].mask_nucleus = image.mask_nucleus
                self.__folder.images[index].mask_micronucleus = image.mask_micronucleus
                index += 1'''

        self.__write_resume()
        self.__was_runned = True
        self.__folder.was_segmented = True
        self.__draw_image_selected()
        self.__setup.statusbar.showMessage(App._text['finished'])
        # Message.completed_process(self)

    def __run(self, event) -> None:
        """Description."""
        if threading.active_count() <= self.__max_threads:
            if isinstance(self.__folder, Folder):  # revisa si hay imagenes que analizar
                if not self.__was_runned:  # entra si no ha sido ejecutado aún
                    if self.__folder.images.__len__() > 0:
                        if Message.run(self):
                            thread_processes = threading.Thread(target=self.__controller_processes, daemon=True)
                            thread_processes.start()
                    else:
                        Message.completed_process(self)
                else:
                    Message.was_runned(self)
            else:
                Message.select_folder(self)
        else:
            Message.segmentation_is_runnig(self)

    # _____________________________Private methods_____________________________

    # _____________________________Public methods______________________________

    def segmentation(self, images: list):
        mod = None  # 'cyto'  # Que modelo utilizara 'nuclei' o 'cyto'
        diameter = 125  # Diametro del nucleo(30) o membrana(125) segun sea la resolucion  de la imagen
        path_pretrained_model = os.getcwd() + '\\membranas_500_125'  # ruta al archivo del modelo que se desea utilizar
        channels = [[1, 0]]

        model = models.CellposeModel(model_type=mod, pretrained_model=path_pretrained_model)
        masks, flows, styles = model.eval(images, diameter=diameter, channels=channels, statusbar=self.__setup.statusbar)

        list_images = []

        for i in range(masks.__len__()):
            image = Image("img", images[i], )
            image.mask_cytoplasm = Mask(masks[i].astype(dtype=np.uint8), Mask.CYTOPLASM)

            image.mask_cytoplasm.add_elements()
            image.mask_cytoplasm.select_elements()

            image.mask_nucleus.add_elements(cytoplasms=image.mask_cytoplasm.elements)
            image.mask_nucleus.select_elements(img=image.data,
                                               cytoplasms=image.mask_cytoplasm.elements)

            image.mask_micronucleus.add_elements(cytoplasms=image.mask_cytoplasm.elements)
            image.mask_micronucleus.select_elements(img=image.data,
                                                    cytoplasms=image.mask_cytoplasm.elements)

            list_images.append(image)

        return list_images

    def resizeEvent(self, event) -> None:
        """Description."""
        self.__draw_image()

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
            path = QStandardPaths.standardLocations(QStandardPaths.DesktopLocation)[0]
            index = path.rfind('/')
            path = path[:index + 1] + 'cellanalizer/'
            files = os.listdir(path)
            for f in files:
                os.remove(path + f)
            event.accept()
        else:
            event.ignore()

    def show_window(self):
        """Method description (DocString)"""
        pass

    # _____________________________Public methods______________________________
