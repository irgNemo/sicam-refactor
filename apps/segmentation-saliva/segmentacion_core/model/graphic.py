'''#!/usr/bin/python3
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib.pyplot as plt

__email__ = "oscarmtzp93@gmail.com"
__license__ = "GPL"
__maintainer__ = "Oscar Martinez"
__status__ = "Developing"

__version__ = "1.0"

__date__ = "nov/11/2021"

__author__ = "Oscar Martinez"

__credits__ = "UDG"


class Graphic:
    """Class description (DocString)"""

    # ____________________________Class attributes_____________________________

    '' '_ =
     ='' '

    # ____________________________Class attributes_____________________________

    # ______________________________Class methods______________________________

    '' '@classmethod
    def (cls) -> :
        """Method description  (DocString)"""
        return Graphic.' ''

    # ______________________________Class methods______________________________

    # ______________________________MAGIC METHODS______________________________

    # _____________________________Generic methods_____________________________

    def __init__(self, data: np.ndarray, projection: str = '3d'):
        """Method description  (DocString)
        parameters>
            projection> '3d' or 'rectilinear'
        """
        self.__data = None
        self.__projection = None
        self.__x_label = 'Blue'
        self.__y_label = 'Green'
        self.__fig = plt.figure()
        self.__axis = self.__fig.add_subplot(111, projection=projection)
        
        self.data = data
        self.projection = projection


    def __len__(self):
        """Method description  (DocString)
        return len(self.projection)"""
        return len(self.data)

    def __str__(self):
        """Method description  (DocString)
        return str(self.projection)"""
        return str(self.data)

    # _____________________________Generic methods_____________________________

    # ______________________________MAGIC METHODS______________________________

    # _________________________________Getters_________________________________

    @property
    def data(self) -> np.ndarray:
        """Method description (DocString)"""
        return self.__data

    @property
    def projection(self) -> str:
        """Method description (DocString)"""
        return self.__projection

    @property
    def x_label(self) -> str:
        """Returns the x_label (str)"""
        return self.__x_label

    @property
    def y_label(self) -> str:
        """Returns the y_label (str)"""
        return self.__y_label

    # _________________________________Getters_________________________________

    # _________________________________Setters_________________________________

    @data.setter
    def data(self, data: np.ndarray):
        """Method description (DocString)"""
        self.__data = data

    @projection.setter
    def projection(self, projection: str):
        """Method description (DocString)"""
        self.__projection = projection

    @x_label.setter
    def x_label(self, x_label: str):
        """Sets the x_label (str)"""
        self.__x_label = x_label

    @y_label.setter
    def y_label(self, y_label: str):
        """Sets the y_label (str)"""
        self.__y_label = y_label

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

    def show(self) -> bool:
        """Method description (DocString)
        >>> 2 + 3
        5
        """
        if self.projection == '3d':
            d = self.data
            print(d[:, :, 0].flatten())
            self.__axis.scatter(d[:, :, 0].flatten(), d[:, :, 1].flatten(), d[:, :, 2].flatten())



        plt.xlabel(self.x_label)
        plt.ylabel(self.y_label)

        plt.show()

    # _____________________________Public methods______________________________

    # ______________________________Inner classes______________________________

    class GraphicError(Exception):
        def __init__(self, msg: str):
            super().__init__(msg)

    # ______________________________Inner classes______________________________


if __name__ == "__main__":
    import doctest
    doctest.testmod()

'''