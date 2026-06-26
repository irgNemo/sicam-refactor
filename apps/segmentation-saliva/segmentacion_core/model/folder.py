#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os

from segmentacion_core.model.image import Image


__email__ = "oscarmtzp93@gmail.com"
__license__ = "GPL"
__maintainer__ = "Oscar Martinez"
__status__ = "Developing"

__version__ = "1.0"

__date__ = "oct/04/2021"

__author__ = "Oscar Martinez"

__credits__ = "UDG"


class Folder:
    """This class manages a folder with all the images inside."""

    # ______________________________MAGIC METHODS______________________________

    # _____________________________Generic methods_____________________________

    def __init__(self, path: str):
        """Initializes the properties
        path: str > Absolute path of the operating system, where the images folder is located.
        images: list(Image) > Collection of images inside the folder."""
        self.__path = None
        self.__images = []
        
        self.path = path

    def __len__(self):
        """Returns the total number of images in the collection.
        return len(self.images)"""
        return len(self.images)

    def __str__(self):
        """Returns the path of the folder.
        return self.path"""
        return self.path

    # _____________________________Generic methods_____________________________

    # ____________________________Arithmetic methods___________________________

    def __add__(self, other):
        """Adds the 2 image collections in one collection and returns it."""
        return self.images + other.images

    '''def __sub__(self, other):
        """Method description (DocString)"""
        return self.path - other.path

    def __mul__(self, other):
        """Method description (DocString)"""
        return self.path * other.path

    def __truediv__(self, other):
        """Method description (DocString)"""
        return self.path / other.path'''

    # ____________________________Arithmetic methods___________________________

    # _____________________________Logical methods_____________________________

    '''def __lt__(self, other):
        """Method description (DocString)
        return self.path < other.path"""
        return self.path < other.path

    def __le__(self, other):
        """Method description (DocString)
        return self.path <= other.path"""
        return self.path <= other.path

    def __eq__(self, other):
        """Method description (DocString)
        return self.path == other.path"""
        return self.path == other.path'''

    # _____________________________Logical methods_____________________________

    # ______________________________MAGIC METHODS______________________________

    # _________________________________Getters_________________________________

    @property
    def path(self) -> str:
        """Returns the path of the folder."""
        return self.__path

    @property
    def images(self) -> list:
        """Returns the collection of images"""
        return self.__images

    # _________________________________Getters_________________________________

    # _________________________________Setters_________________________________

    @path.setter
    def path(self, path: str):
        """Sets the path attribute."""
        if path[-1] != '/':
            self.__path = path + '/'
        else:
            self.__path = path

    @images.setter
    def images(self, images: list):
        """Sets the image collection attribute."""
        self.__images = images

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

    def get_images_data(self) -> list:
        """Returns a list of np.ndarrays with the RGB images found in the
        image collection attribute."""
        return [image.data for image in self.images]

    def upload_images(self, formats: tuple = ('.jpg', )) -> None:
        """Receives as a parameter a tuple of strings,
        which specifies what type of files it will load.
        loads all the images with the extension specified
        in the parameter found in the path attribute.
        >>> 2 + 3
        5
        """
        imgs_name = os.listdir(self.path)
        path_imgs = [self.path + p for p in imgs_name if p[-4:] in formats]
        #self.images = [Image(p[p.rfind('/')+1:p.rfind('.')], skimage.io.imread(p))
        #               for p in path_imgs]

        for i in range(path_imgs.__len__()):
            image = Image(imgs_name[i][:imgs_name[i].rfind('.')])
            image.upload_image(path_imgs[i])
            self.images.append(image)

    def save_images(self, absolute_path: str, flag_mask: bin = 0b0000, extension: str = '.jpg') -> None:
        """Saves all images in the image list attribute."""
        for i in self.images:
            i.save(absolute_path, flag_mask, extension)

    def scale_images(self, fx: float, fy: float) -> None:
        """Scales all images in the image list attribute."""
        for i in self.images:
            i.scale(fx, fy)

    def remove_folder(self, relative_path: str) -> None:
        """Deletes a folder in the relative path."""
        folder = os.listdir(self.path)
        folder.remove(relative_path)

    def calculate_indices(self) -> tuple:
        """Calculates the cytotoxicity and genotoxicity index.
        Returns: tuple(cytotoxicity_index: float
                       genotoxicity_index: float)"""

        cytoplasm = 0
        nucleus = 0
        binucleate = 0
        trinucleate = 0
        micronucleus = 0

        for img in self.images:
            cytoplasm += img.mask_cytoplasm.elements.__len__()
            nucleus += img.mask_nucleus.total_elements
            binucleate += img.mask_nucleus.total_binucleate
            trinucleate += img.mask_nucleus.total_trinucleate
            micronucleus += img.mask_micronucleus.total_micronucleus

        cytotoxicity_index = (binucleate + trinucleate) / cytoplasm
        genotoxicity_index = micronucleus / cytoplasm

        return (cytotoxicity_index, genotoxicity_index)

    # _____________________________Public methods______________________________

    # ______________________________Inner classes______________________________

    class FolderError(Exception):
        def __init__(self, msg: str):
            super().__init__(msg)

    # ______________________________Inner classes______________________________


if __name__ == "__main__":
    import doctest
    doctest.testmod()
