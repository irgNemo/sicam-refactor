#!/usr/bin/python3
# -*- coding: utf-8 -*-

import numpy as np
import cv2

from segmentacion_core.model.mask import Mask

__email__ = "oscarmtzp93@gmail.com"
__license__ = "GPL"
__maintainer__ = "Oscar Martinez"
__status__ = "Developing"

__version__ = "1.0"

__date__ = "oct/05/2021"

__author__ = "Oscar Martinez"

__credits__ = "UDG"


class Image:
    """This class represents an image in RGB."""

    # ______________________________MAGIC METHODS______________________________

    # _____________________________Generic methods_____________________________

    def __init__(self, name: str, data: np.ndarray = None):
        """Initializes the properties
        name: str > Is the name of the image.
        data: np.ndarray[R, G, B] > Array with the RGB colors.
        mask_cytoplasm: Mask > Is an object that represents the masks in the cytoplasm.
        mask_nucleus: Mask > Is an object that represents the masks in the nucleus.
        mask_micronucleus: Mask > Is an object that represents the masks in the micronucleus."""
        self.__name = None
        self.__data = None
        self.__mask_cytoplasm = Mask(None, Mask.CYTOPLASM)
        self.__mask_nucleus = Mask(None, Mask.NUCLEI)
        self.__mask_micronucleus = Mask(None, Mask.MICRONUCLEI)

        self.name = name
        self.data = data

    def __len__(self):
        """Returns the total number of elements.
        return len(self.elements)"""
        return len(self.elements)

    def __str__(self):
        """Returns the name of the image.
        return str(self.elements)"""
        return self.name

    # _____________________________Generic methods_____________________________

    # ____________________________Arithmetic methods___________________________

    '''def __add__(self, other):
        """Method description (DocString)"""
        return self.name + other.name

    def __sub__(self, other):
        """Method description (DocString)"""
        return self.name - other.name

    def __mul__(self, other):
        """Method description (DocString)"""
        return self.name * other.name

    def __truediv__(self, other):
        """Method description (DocString)"""
        return self.name / other.name'''

    # ____________________________Arithmetic methods___________________________

    # _____________________________Logical methods_____________________________

    '''def __lt__(self, other):
        """Method description (DocString)
        return self.name < other.name"""
        return self.name < other.name

    def __le__(self, other):
        """Method description (DocString)
        return self.name <= other.name"""
        return self.name <= other.name

    def __eq__(self, other):
        """Method description (DocString)
        return self.name == other.name"""
        return self.name == other.name'''

    # _____________________________Logical methods_____________________________

    # ______________________________MAGIC METHODS______________________________

    # _________________________________Getters_________________________________

    @property
    def name(self) -> str:
        """Returns the name of the image."""
        return self.__name

    @property
    def data(self) -> np.ndarray:
        """Returns the data image RGB."""
        return self.__data

    @property
    def mask_cytoplasm(self) -> Mask:
        """Returns an object mask cytoplasm."""
        return self.__mask_cytoplasm

    @property
    def mask_nucleus(self) -> Mask:
        """Returns an object mask nucleus."""
        return self.__mask_nucleus

    @property
    def mask_micronucleus(self) -> Mask:
        """Returns an object mask micronucleus."""
        return self.__mask_micronucleus

    # _________________________________Getters_________________________________

    # _________________________________Setters_________________________________

    @name.setter
    def name(self, name: str):
        """Sets the attribute name."""
        self.__name = name

    @data.setter
    def data(self, data: np.ndarray):
        """Sets the data (np.ndarray)"""
        self.__data = data

    @mask_cytoplasm.setter
    def mask_cytoplasm(self, mask_cytoplams: Mask):
        """Sets the mask cytoplasm (Mask)"""
        self.__mask_cytoplasm = mask_cytoplams

    @mask_nucleus.setter
    def mask_nucleus(self, mask_nucleus: Mask):
        """Sets the mask nucleus (Mask)"""
        self.__mask_nucleus = mask_nucleus
        
    @mask_micronucleus.setter
    def mask_micronucleus(self, mask_micronucleus: Mask):
        """Sets the micronucleus (Mask)"""
        self.__mask_micronucleus = mask_micronucleus

    # _________________________________Setters_________________________________

    # _____________________________Private methods_____________________________

    def __filter_moda(self, mask: np.ndarray) -> np.ndarray:
        """Descritpion"""
        mask = cv2.medianBlur(mask, 7)
        for i in range(mask.max()):
            mask_i = np.where(mask == i + 1, 1, 0).astype('uint8')

            contours, _ = cv2.findContours(mask_i, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

            max = contours[0].__len__()
            max_index = 0
            for index, j in enumerate(contours):
                if j.__len__() > max:
                    max = j.__len__()
                    max_index = index

            for index, j in enumerate(contours):
                if index != max_index:
                    for k in j:
                        mask[k[0][1], k[0][0]] = 0

        return mask

    def __draw_masks(self, flag_mask: bin) -> np.ndarray:
        """Draws the masks in the image.
        0b0001 > only image.
        0b0010 > shows cytoplams mask.
        0b0100 > shows nucleus mask.
        0b1000 > shows micronucleus mask.
        """
        img = np.zeros(self.data.shape, np.uint8)

        if flag_mask & 0b0001:
            img = self.data.copy()

        if flag_mask & 0b0010 and self.mask_cytoplasm:
            aux_mask = np.zeros(self.mask_cytoplasm.data.shape, 'uint8')
            for e in self.mask_cytoplasm.elements:
                aux_mask[e.pos_y: e.pos_y + e.mask.shape[0], e.pos_x: e.pos_x + e.mask.shape[1]] |= e.mask

            for i in range(aux_mask.max()):
                mask = np.where(aux_mask == i + 1, 1, 0).astype('uint8')
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                img = cv2.drawContours(img, contours, -1, (0, 0, 255), 1)

        if flag_mask & 0b0100 and self.mask_cytoplasm:
            aux_mask = np.zeros(self.mask_cytoplasm.data.shape, 'uint8')
            for e in self.__mask_nucleus.elements:
                aux_mask[e.pos_y: e.pos_y + e.mask.shape[0], e.pos_x: e.pos_x + e.mask.shape[1]] |= e.nucleis

            contours, _ = cv2.findContours(aux_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            img = cv2.drawContours(img, contours, -1, (255, 0, 0), 1)

        if flag_mask & 0b1000 and self.mask_cytoplasm:
            aux_mask = np.zeros(self.mask_cytoplasm.data.shape, 'uint8')
            for e in self.__mask_micronucleus.elements:
                aux_mask[e.pos_y: e.pos_y + e.mask.shape[0], e.pos_x: e.pos_x + e.mask.shape[1]] |= e.micronucleis

            contours, _ = cv2.findContours(aux_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            img = cv2.drawContours(img, contours, -1, (0, 255, 0), 3)

        return img

    def get_masks(self, flag_mask: bin) -> np.ndarray:
        """Draws the masks in the image.
        0b0001 > only image.
        0b0010 > shows cytoplams mask.
        0b0100 > shows nucleus mask.
        0b1000 > shows micronucleus mask.
        """
        img = np.zeros(self.data.shape, np.uint8)

        if flag_mask & 0b0001:
            img = self.data.copy()

        if flag_mask & 0b0010 and self.mask_cytoplasm:
            aux_mask = np.zeros(self.mask_cytoplasm.data.shape, 'uint8')
            for e in self.mask_cytoplasm.elements:
                aux_mask[e.pos_y: e.pos_y + e.mask.shape[0], e.pos_x: e.pos_x + e.mask.shape[1]] |= e.mask

            for i in range(aux_mask.max()):
                mask = np.where(aux_mask == i + 1, 1, 0).astype('uint8')
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                img = cv2.drawContours(img, contours, -1, (255, 255, 255), cv2.FILLED)

        if flag_mask & 0b0100 and self.mask_cytoplasm:
            aux_mask = np.zeros(self.mask_cytoplasm.data.shape, 'uint8')
            for e in self.__mask_nucleus.elements:
                aux_mask[e.pos_y: e.pos_y + e.mask.shape[0], e.pos_x: e.pos_x + e.mask.shape[1]] |= e.nucleis

            contours, _ = cv2.findContours(aux_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            img = cv2.drawContours(img, contours, -1, (255, 255, 255), cv2.FILLED)

        if flag_mask & 0b1000 and self.mask_cytoplasm:
            aux_mask = np.zeros(self.mask_cytoplasm.data.shape, 'uint8')
            for e in self.__mask_micronucleus.elements:
                aux_mask[e.pos_y: e.pos_y + e.mask.shape[0], e.pos_x: e.pos_x + e.mask.shape[1]] |= e.micronucleis

            contours, _ = cv2.findContours(aux_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            img = cv2.drawContours(img, contours, -1, (255, 255, 255), cv2.FILLED)

        return img


    # _____________________________Private methods_____________________________

    # _____________________________Public methods______________________________

    def upload_image(self, absolute_path: str) -> None:
        """Upload a image in the absolute path in the attribute data.
        >>> 2 + 2
        5
        """
        img = cv2.imread(absolute_path, cv2.IMREAD_COLOR)
        cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.data = img

    def upload_mask_cytoplasm(self, absolute_path: str) -> None:
        """Loads the cytoplasm mask with the cellpose format.
        >>> 2 + 3
        5
        """
        mask = np.load(absolute_path, allow_pickle=True)

        try:
            mask = mask.item()['masks'].astype('uint8')
        except ValueError:
            mask = mask.astype('uint8')

        self.mask_cytoplasm = Mask(mask, Mask.CYTOPLASM)

    def upload_mask_nucleus(self, absolute_path: str) -> None:
        """Loads the nucleus mask with the cellpose format."""
        mask = np.load(absolute_path, allow_pickle=True)

        try:
            mask = mask.item()['masks'].astype('uint8')
        except ValueError:
            mask = mask.astype('uint8')

        self.mask_nucleus = Mask(mask, Mask.NUCLEI)

    def upload_mask_micronucleus(self, absolute_path: str) -> None:
        """Loads the micronucleus mask with the cellpose format."""
        mask = np.load(absolute_path, allow_pickle=True)

        try:
            mask = mask.item()['masks'].astype('uint8')
        except ValueError:
            mask = mask.astype('uint8')

        self.mask_micronucleus = Mask(mask, Mask.MICRONUCLEI)

    def save(self, absolute_path: str, flag_mask: bin = 0b0001, extension: str = '.jpg') -> None:
        """Saves the image in the absolute_path with the activate flag masks.
        0b0001 > only image.
        0b0010 > shows cytoplams mask.
        0b0100 > shows nucleus mask.
        0b1000 > shows micronucleus mask."""

        if absolute_path[-1] != '/':
            absolute_path = absolute_path + '/'

        img = self.__draw_masks(flag_mask)

        cv2.imwrite(absolute_path + self.name + extension, img)

    def scale(self, fx: float, fy: float) -> None:
        """Scale the image and the masks."""

        if type(self.data) == np.ndarray:
            self.data = cv2.resize(self.data, (0, 0), fx=fx, fy=fy)
        if type(self.mask_cytoplasm.data) == np.ndarray:
            aux = cv2.resize(self.mask_cytoplasm.data, (0, 0), fx=fx, fy=fy).astype('uint8')
            self.mask_cytoplasm.data = self.__filter_moda(aux)
        if type(self.mask_nucleus.data) == np.ndarray:
            aux = cv2.resize(self.mask_nucleus.data, (0, 0), fx=fx, fy=fy)
            self.mask_nucleus.data = self.__filter_moda(aux)
        if type(self.mask_micronucleus.data) == np.ndarray:
            aux = cv2.resize(self.mask_micronucleus.data, (0, 0), fx=fx, fy=fy)
            self.mask_micronucleus.data = self.__filter_moda(aux)

    def show_image(self, flag_mask: bin = 0b0001):
        """Shows the image with the masks.
        0b0001 > only image.
        0b0010 > shows cytoplams mask.
        0b0100 > shows nucleus mask.
        0b1000 > shows micronucleus mask."""

        img = self.__draw_masks(flag_mask)

        cv2.imshow(self.name, img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # _____________________________Public methods______________________________

    # ______________________________Inner classes______________________________

    class ImageError(Exception):
        def __init__(self, msg: str):
            super().__init__(msg)

    # ______________________________Inner classes______________________________


if __name__ == "__main__":
    import doctest
    doctest.testmod()
