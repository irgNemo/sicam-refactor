#!/usr/bin/python3
# -*- coding: utf-8 -*-

import numpy as np

from segmentacion_core.model.element import Element

__email__ = "oscarmtzp93@gmail.com"
__license__ = "GPL"
__maintainer__ = "Oscar Martinez"
__status__ = "Developing"

__version__ = "1.0"

__date__ = "oct/19/2021"

__author__ = "Oscar Martinez"

__credits__ = "UDG"


class Cytoplasm(Element):
    """Class description (DocString)"""

    # ______________________________MAGIC METHODS______________________________

    # _____________________________Generic methods_____________________________

    def __init__(self, mask: np.ndarray = None, pos_x: int = None, pos_y: int = None):
        """Method description  (DocString)"""
        super(Cytoplasm, self).__init__(mask, pos_x, pos_y)
        self.color_nuclei = None

    '''def __len__(self):
        """Method description  (DocString)
        return len(self.)"""
        return len(super(Element, self).__len__())'''

    '''def __str__(self):
        """Method description  (DocString)
        return str(self.)"""
        return str(self.)'''

    # _____________________________Generic methods_____________________________

    # ____________________________Arithmetic methods___________________________

    '''def __add__(self, other):
        """Method description (DocString)"""
        return self. + other.

    def __sub__(self, other):
        """Method description (DocString)"""
        return self. - other.

    def __mul__(self, other):
        """Method description (DocString)"""
        return self. * other.

    def __truediv__(self, other):
        """Method description (DocString)"""
        return self. / other.'''

    # ____________________________Arithmetic methods___________________________

    # _____________________________Logical methods_____________________________

    '''def __lt__(self, other):
        """Method description (DocString)
        return self. < other."""
        return self. < other.

    def __le__(self, other):
        """Method description (DocString)
        return self. <= other."""
        return self. <= other.

    def __eq__(self, other):
        """Method description (DocString)
        return self. == other."""
        return self. == other.'''

    # _____________________________Logical methods_____________________________

    # ______________________________MAGIC METHODS______________________________

    # _________________________________Getters_________________________________

    '''@property
    def (self) -> :
        """Method description (DocString)"""
        return self.__

    @property
    def (self) -> :
        """Method description (DocString)"""
        return self.__'''

    # _________________________________Getters_________________________________

    # _________________________________Setters_________________________________

    '''@.setter
    def (self, : ):
        """Method description (DocString)"""
        self.__ = 

    @.setter
    def (self, : ):
        """Method description (DocString)"""
        self.__ = '''

    # _________________________________Setters_________________________________

    # _____________________________Private methods_____________________________

    def __valid_limits(self, shape: tuple) -> bool:
        """Parses cells that touch the margin and removes them from the list of items.
        >>> 2 + 3
        5
        """
        margin = 2

        if self.pos_x - margin <= 0 or self.pos_y - margin <= 0 or self.pos_x + self.mask.shape[1] + margin >= \
                shape[1] or self.pos_y + self.mask.shape[0] + margin >= shape[0]:
            return False
        return True

    # _____________________________Private methods_____________________________

    # _____________________________Public methods______________________________

    def is_a_element(self, **kwargs) -> bool:
        """Searches for cytoplasms and adds them to the elements list.
        >>> 2 + 3
        5
        """
        is_a_element = True
        is_a_element &= self.__valid_limits(kwargs['shape'])

        return is_a_element

    # _____________________________Public methods______________________________

    # ______________________________Inner classes______________________________

    class CytoplasmError(Exception):
        def __init__(self, msg: str):
            super().__init__(msg)

    # ______________________________Inner classes______________________________


if __name__ == "__main__":
    import doctest
    doctest.testmod()
