#!/usr/bin/python3
# -*- coding: utf-8 -*-

import numpy as np

__email__ = "oscarmtzp93@gmail.com"
__license__ = "GPL"
__maintainer__ = "Oscar Martinez"
__status__ = "Developing"

__version__ = "1.0"

__date__ = "oct/06/2021"

__author__ = "Oscar Martinez"

__credits__ = "UDG"


class Element:
    """Class description (DocString)"""

    # ______________________________MAGIC METHODS______________________________

    # _____________________________Generic methods_____________________________

    def __init__(self, mask: np.ndarray = None, pos_x: int = None, pos_y: int = None):
        """Method description  (DocString)"""
        self.__mask = None
        self.__pos_x = None
        self.__pos_y = None

        self.mask = mask
        self.pos_x = pos_x
        self.pos_y = pos_y

    '''def __len__(self):
        """Method description  (DocString)
        return len(self.)"""
        return self.mask.shape'''

    '''def __str__(self):
        """Method description  (DocString)
        return str(self.)"""
        pass'''

    # _____________________________Generic methods_____________________________

    # ____________________________Arithmetic methods___________________________

    '''def __add__(self, other):
        """Method description (DocString)"""
        return self.mask + other.mask

    def __sub__(self, other):
        """Method description (DocString)"""
        return self.mask - other.mask

    def __mul__(self, other):
        """Method description (DocString)"""
        return self.mask * other.mask

    def __truediv__(self, other):
        """Method description (DocString)"""
        return self.mask / other.mask'''

    # ____________________________Arithmetic methods___________________________

    # _____________________________Logical methods_____________________________

    '''def __lt__(self, other):
        """Method description (DocString)
        return self.mask < other.mask"""
        return self.mask < other.mask

    def __le__(self, other):
        """Method description (DocString)
        return self.mask <= other.mask"""
        return self.mask <= other.mask

    def __eq__(self, other):
        """Method description (DocString)
        return self.mask == other.mask"""
        return self.mask == other.mask'''

    # _____________________________Logical methods_____________________________

    # ______________________________MAGIC METHODS______________________________

    # _________________________________Getters_________________________________

    @property
    def mask(self) -> np.ndarray:
        """Method description (DocString)"""
        return self.__mask

    @property
    def pos_x(self) -> int:
        """Returns the pos_x (int)"""
        return self.__pos_x

    @property
    def pos_y(self) -> int:
        """Returns the pos_y (int)"""
        return self.__pos_y

    # _________________________________Getters_________________________________

    # _________________________________Setters_________________________________

    @mask.setter
    def mask(self, mask: np.ndarray):
        """Method description (DocString)"""
        self.__mask = mask

    @pos_x.setter
    def pos_x(self, pos_x: int):
        """Sets the pos_x (int)"""
        self.__pos_x = pos_x

    @pos_y.setter
    def pos_y(self, pos_y: int):
        """Sets the pos_y (int)"""
        self.__pos_y = pos_y

    # _________________________________Setters_________________________________

    # _____________________________Private methods_____________________________

    def __method_private(self) -> bool:
        """Method description (DocString)
        >>> 2 + 3
        5
        """
        pass

    # _____________________________Private methods_____________________________

    # _____________________________Public methods______________________________

    def area(self, img: np.ndarray) -> int:
        """Returns the area in the attribute mask.
        >>> 2 + 3
        5
        """
        pass

    def is_a_element(self, **kwargs) -> bool:
        """Doc"""
        pass

    # _____________________________Public methods______________________________

    # ______________________________Inner classes______________________________

    class ElementError(Exception):
        def __init__(self, msg: str):
            super().__init__(msg)

    # ______________________________Inner classes______________________________


if __name__ == "__main__":
    import doctest
    doctest.testmod()
