#!/usr/bin/python3
# -*- coding: utf-8 -*-

import numpy as np

from segmentacion_core.model.cytoplasm import Cytoplasm
from segmentacion_core.model.nuclei import Nuclei
from segmentacion_core.model.micronuclei import Micronuclei

__email__ = "oscarmtzp93@gmail.com"
__license__ = "GPL"
__maintainer__ = "Oscar Martinez"
__status__ = "Developing"

__version__ = "1.0"

__date__ = "oct/13/2021"

__author__ = "Oscar Martinez"

__credits__ = "UDG"


class Mask:
    """Class description (DocString)"""

    # ____________________________Class attributes_____________________________

    CYTOPLASM = 0
    NUCLEI = 1
    MICRONUCLEI = 2

    # ____________________________Class attributes_____________________________

    # ______________________________MAGIC METHODS______________________________

    # _____________________________Generic methods_____________________________

    def __init__(self, data: np.ndarray, type: int):
        """Method description  (DocString)"""
        self.__data = None
        self.__elements = []
        self.__type = None
        self.__total_elements = 0
        self.__total_binucleate = 0
        self.__total_trinucleate = 0
        self.__total_micronucleus = 0

        self.data = data
        self.type = type

    def __len__(self):
        """Method description  (DocString)
        return len(self.elements)"""
        return len(self.elements)

    def __str__(self):
        """Method description  (DocString)
        return str(self.elements)"""
        return str(self.data)

    # _____________________________Generic methods_____________________________

    # ______________________________MAGIC METHODS______________________________

    # _________________________________Getters_________________________________

    @property
    def data(self) -> np.ndarray:
        """Method description (DocString)"""
        return self.__data

    @property
    def elements(self) -> list:
        """Method description (DocString)"""
        return self.__elements

    @property
    def type(self) -> int:
        """Returns the type (int)"""
        return self.__type

    @property
    def total_elements(self) -> int:
        """Returns the total_elements (int)"""
        return self.__total_elements

    @property
    def total_binucleate(self) -> int:
        """Returns the total_binucleate (int)"""
        return self.__total_binucleate

    @property
    def total_trinucleate(self) -> int:
        """Returns the total_trinucleate (int)"""
        return self.__total_trinucleate

    @property
    def total_micronucleus(self) -> int:
        """Returns the total_micronucleus (int)"""
        return self.__total_micronucleus

    # _________________________________Getters_________________________________

    # _________________________________Setters_________________________________

    @data.setter
    def data(self, data: np.ndarray):
        """Method description (DocString)"""
        self.__data = data

    @elements.setter
    def elements(self, elements: list):
        """Method description (DocString)"""
        self.__elements = elements

    @type.setter
    def type(self, type: int):
        """Sets the type (int)"""
        self.__type = type

    @total_elements.setter
    def total_elements(self, total_elements: int):
        """Sets the total_elements (int)"""
        self.__total_elements = total_elements

    @total_binucleate.setter
    def total_binucleate(self, total_binucleate: int):
        """Sets the total_binucleate (int)"""
        self.__total_binucleate = total_binucleate

    @total_trinucleate.setter
    def total_trinucleate(self, total_trinucleate: int):
        """Sets the total_trinucleate (int)"""
        self.__total_trinucleate = total_trinucleate

    @total_micronucleus.setter
    def total_micronucleus(self, total_micronucleus: int):
        """Sets the total_micronucleus (int)"""
        self.__total_micronucleus = total_micronucleus

    # _________________________________Setters_________________________________

    # _____________________________Public methods______________________________

    def add_elements(self, **kwargs) -> None:
        """Searches for elements in the mask and adds them to the list of elements.
        parameters:
           nucleus> cytoplasms: list[elements].
           micronucleus> """
        self.elements = []

        if self.type == Mask.CYTOPLASM:
            for i in range(self.data.max()):
                pos_x_y = np.where(self.data == i + 1)

                x_min = np.min(pos_x_y[1])
                x_max = np.max(pos_x_y[1])
                y_min = np.min(pos_x_y[0])
                y_max = np.max(pos_x_y[0])

                element = Cytoplasm(np.where(self.data[y_min:y_max, x_min:x_max] == i+1, i+1, 0).astype('uint8'), x_min, y_min)

                self.elements.append(element)

        elif self.type == Mask.NUCLEI:
            for e in kwargs['cytoplasms']:
                self.elements.append(Nuclei(e.mask, e.pos_x, e.pos_y))

        elif self.type == Mask.MICRONUCLEI:
            for e in kwargs['cytoplasms']:
                self.elements.append(Micronuclei(e.mask, e.pos_x, e.pos_y))

    def select_elements(self, **kwargs: dict):
        """Removes elements that do not meet the specifications of the element, either cytoplasm,
        nucleus or micronucleus.
        parameters:
           nucleus> img: np.ndarray.
           micronucleus> img: np.ndarray"""

        index = self.elements.__len__()
        while index > 0:
            index -= 1
            if self.type == Mask.CYTOPLASM:
                if not self.elements[index].is_a_element(shape=self.data.shape):
                    self.elements.pop(index)
            elif self.type == Mask.NUCLEI:
                #self.__data = np.zeros(kwargs['img'].shape, np.uint8)
                elements = self.elements[index].is_a_element(img=kwargs['img'], cytoplasm=kwargs['cytoplasms'][index], mask=self.__data)
                self.total_elements += elements
                if not elements:
                    self.elements.pop(index)
                    kwargs['cytoplasms'].pop(index)
                elif elements == 2:
                    self.total_binucleate += 1
                elif elements == 3:
                    self.total_trinucleate += 1
            elif self.type == Mask.MICRONUCLEI:
                #self.__data = np.zeros((kwargs['img'].shape[0], kwargs['img'].shape[1]), np.uint8)
                elements = self.elements[index].is_a_element(img=kwargs['img'], cytoplasm=kwargs['cytoplasms'][index])
                self.total_micronucleus += elements

    # _____________________________Public methods______________________________

    # ______________________________Inner classes______________________________

    class MaskError(Exception):
        def __init__(self, msg: str):
            super().__init__(msg)

    # ______________________________Inner classes______________________________


if __name__ == "__main__":
    import doctest
    doctest.testmod()
