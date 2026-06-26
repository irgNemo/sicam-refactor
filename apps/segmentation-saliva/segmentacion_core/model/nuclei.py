#!/usr/bin/python3
# -*- coding: utf-8 -*-

import numpy as np
import cv2

from segmentacion_core.model.element import Element
from segmentacion_core.model.cytoplasm import Cytoplasm

__email__ = "oscarmtzp93@gmail.com"
__license__ = "GPL"
__maintainer__ = "Oscar Martinez"
__status__ = "Developing"

__version__ = "1.0"

__date__ = "oct/24/2021"

__author__ = "Oscar Martinez"

__credits__ = "UDG"


class Nuclei(Element):
    """Class description (DocString)"""

    # ______________________________Class methods______________________________

    @classmethod
    def trim_image_mask(cls, img: np.ndarray, mask: np.ndarray, pos_x: int, pos_y: int, margin: int = 3) -> np.ndarray:
        """Trims the image passed by parameter with the mask attribute,
        and leaves a margin to the image."""
        if img.shape.__len__() == 3:
            aux_img = img[pos_y - margin: pos_y + mask.shape[0] + margin,
                      pos_x - margin: pos_x + mask.shape[1] + margin, :]

        elif img.shape.__len__() == 2:
            aux_img = img[pos_y - margin: pos_y + mask.shape[0] + margin,
                      pos_x - margin: pos_x + mask.shape[1] + margin]

        return aux_img

    @classmethod
    def combine_mask_3d(cls, img: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Description."""
        margin = int((img.shape[0] - mask.shape[0]) / 2)
        img_mask = np.zeros((img.shape[0], img.shape[1], 3), np.uint8)
        index = np.where(mask != 0)

        for i in range(index[0].__len__()):
            try:
                img_mask[index[0][i] + margin, index[1][i] + margin] = img[index[0][i], index[1][i]]
            except:
                print(f'img_mask.shape {img_mask.shape}')
                print(f'index[0][i] + margin {index[0][i] + margin}')
                print(f'index[1][i] + margin {index[1][i] + margin}')
                print(f'img.shape {img.shape}')
                print(f'index[0][i] {index[0][i]}')
                print(f'index[1][i] {index[1][i]}')
                print()

        return img_mask.astype(np.uint8)

    # ______________________________Class methods______________________________

    # ______________________________MAGIC METHODS______________________________

    # _____________________________Generic methods_____________________________

    def __init__(self, mask: np.ndarray = None, pos_x: int = None, pos_y: int = None):
        """Method description  (DocString)"""
        super(Nuclei, self).__init__(mask, pos_x, pos_y)

        self.__nucleis = list()

    # _____________________________Generic methods_____________________________

    # ______________________________MAGIC METHODS______________________________

    # _________________________________Getters_________________________________

    @property
    def nucleis(self) -> list:
        """Method description (DocString)"""
        return self.__nucleis

    # _________________________________Getters_________________________________

    # _________________________________Setters_________________________________

    @nucleis.setter
    def nucleis(self, nucleis: list):
        """Method description (DocString)"""
        self.__nucleis = nucleis

    # _________________________________Setters_________________________________

    # _____________________________Private methods_____________________________

    def __trim_image_mask(self, img: np.ndarray, margin: int = 3) -> np.ndarray:
        """Trims the image passed by parameter with the mask attribute,
        and leaves a margin to the image."""
        return Nuclei.trim_image_mask(img, self.mask, self.pos_x, self.pos_y, margin)

    def __combine_mask_3d(self, img: np.ndarray) -> np.ndarray:
        """Description."""
        return Nuclei.combine_mask_3d(img, self.mask)

    def __combine_mask_2d(self, img: np.ndarray) -> np.ndarray:
        """Description."""
        margin = int((img.shape[0] - self.mask.shape[0]) / 2)
        img_mask = np.zeros((img.shape[0], img.shape[1]), dtype='uint8')

        index = np.where(self.mask != 0)

        for i in range(index[0].__len__()):
            img_mask[index[0][i] + margin, index[1][i] + margin] = img[index[0][i], index[1][i]]

        return img_mask.astype('uint8')

    def __hierarchy_is_valid(self, index: int, hierarchy: np.ndarray) -> bool:
        """Description."""
        count_parent = 1

        index_parent = hierarchy[0][index][3]
        while index_parent != -1:
            count_parent = count_parent + 1
            index_parent = hierarchy[0][index_parent][3]

        # return True if not count_parent % 2 and hierarchy[0][index][2] == -1 else False
        return True if count_parent % 2 else False

    def __area_is_valid(self, area_cyto: float, area_nuclei: float) -> bool:
        """Description."""
        proportion = area_nuclei / area_cyto
        #print(f'Area: 0.01 < {proportion} < .1')
        return True if 0.01 < proportion < .1 else False  # Hardcode

    def __is_ellipse(self, contour: np.ndarray, shape: tuple) -> bool:
        """Description."""
        color = 1
        tolerance_percentage = 15  # Hardcode

        img_original = np.zeros(shape, np.uint8)
        img_original = cv2.drawContours(img_original, [contour], 0, color, cv2.FILLED)

        img_ideal = np.zeros(shape, np.uint8)
        ellipse = cv2.fitEllipse(contour)
        img_ideal = cv2.ellipse(img_ideal, ellipse, color, cv2.FILLED)

        x_min, y_min = contour.min(axis=0)[0]
        x_max, y_max = contour.max(axis=0)[0]
        img_original = img_original[y_min:y_max, x_min:x_max]
        img_ideal = img_ideal[y_min:y_max, x_min:x_max]

        pixels = img_ideal.shape[0] * img_ideal.shape[1]
        img_result = img_ideal ^ img_original
        #print(f'Ellipse: {img_result.sum() / pixels * 100} < {tolerance_percentage}')

        return True if img_result.sum() / pixels * 100 < tolerance_percentage else False

    def __has_garbage(self, img_cyto:  np.ndarray, contour: np.ndarray, cytoplasm: Cytoplasm) -> bool:
        """Description."""
        mask_cyto = np.zeros((img_cyto.shape[0], img_cyto.shape[1]), np.uint8)
        mask_cyto = cv2.drawContours(mask_cyto, [contour], 0, 255, cv2.FILLED)
        min_x, min_y = contour.min(axis=0)[0]
        max_x, max_y = contour.max(axis=0)[0]
        mask_nuclei = mask_cyto[min_y:max_y, min_x:max_x]
        img_nuclei = Nuclei.trim_image_mask(img_cyto, mask_nuclei, min_x, min_y, 4)  # Hardcode
        img_nuclei_mask = Nuclei.combine_mask_3d(img_nuclei, mask_nuclei)

        img_nuclei_mask_gray = cv2.cvtColor(img_nuclei_mask, cv2.COLOR_BGR2GRAY)
        img_nuclei_mask_gray_blur = cv2.medianBlur(img_nuclei_mask_gray, 9)  # Hardcode
        img_nuclei_mask_gray_canny = cv2.Canny(img_nuclei_mask_gray_blur, 45, 50)  # Hardcode
        #cv2.imshow('nuclei', img_nuclei_mask_gray_canny)
        #cv2.imwrite('nuclei.jpg', img_nuclei_mask_gray_canny)

        _, hierarchy = cv2.findContours(img_nuclei_mask_gray_canny, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
        # print(hierarchy)

        if hierarchy.shape[1] == 2:
            img_hsv = cv2.cvtColor(img_nuclei_mask, cv2.COLOR_BGR2HSV)
            max_hue = img_hsv[:, :, 0].max()
            img_hsv[:, :, 0] = np.where(img_hsv[:, :, 0] == 0, max_hue, img_hsv[:, :, 0])

            cytoplasm.color_nuclei = [int(img_hsv[:, :, 0].min()), int(max_hue)]
            return False
        else:
            return True

        # return False if hierarchy.shape[1] == 2 else True

    # _____________________________Private methods_____________________________

    # _____________________________Public methods______________________________

    def is_a_element(self, **kwargs) -> int:
        """Searches for nucleus and adds them to the elements list.
        >>> 2 + 3
        5
        """
        elements = 0
        self.nucleis = np.zeros(self.mask.shape, np.uint8)

        img_gray = cv2.cvtColor(kwargs['img'], cv2.COLOR_BGR2GRAY)
        trim_img = self.__trim_image_mask(img_gray, 4)  # Hardcode. Cut the image to the size of the mask
        mask_and_img = self.__combine_mask_3d(trim_img)
        img_blur = cv2.medianBlur(mask_and_img, 9)  # Hardcode
        img_canny = cv2.Canny(img_blur, 30, 45)  # Hardcode

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))  # Hardcode
        img_morphology = cv2.morphologyEx(img_canny, cv2.MORPH_CLOSE, kernel)

        contours, hierarchy = cv2.findContours(img_morphology, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

        area_cyto = cv2.contourArea(contours[0])
        for i, c in enumerate(contours):
            '''img_aux = np.zeros(img_morphology.shape, np.uint8)
            img_aux = cv2.drawContours(img_aux, c, -1, 255, 1)
            img_aux = cv2.drawContours(img_aux, contours, 0, 255, 1)
            trim_img_color_aux = self.__trim_image_mask(kwargs['img'], 4)

            cv2.imshow('original', trim_img_color_aux)
            cv2.imwrite('original.jpg', trim_img_color_aux)
            cv2.imshow('img_gray', trim_img)
            cv2.imwrite('img_gray.jpg', trim_img)
            cv2.imshow('mask and img', mask_and_img)
            cv2.imwrite('mask_and_img.jpg', mask_and_img)
            cv2.imshow('blur', img_blur)
            cv2.imwrite('img_blur.jpg', img_blur)
            cv2.imshow('canny', img_canny)
            cv2.imwrite('img_canny.jpg', img_canny)
            cv2.imshow('morphological', img_morphology)
            cv2.imwrite('img_morphology.jpg', img_morphology)
            cv2.imshow('contour', img_aux)
            cv2.imwrite('contour.jpg', img_aux)
            cv2.waitKey(0)'''

            if self.__hierarchy_is_valid(i, hierarchy):
                #print("Accept Hierarchy")
                area_nuclei = cv2.contourArea(contours[i])
                if self.__area_is_valid(area_cyto, area_nuclei):
                    #print("Accept Area")
                    if self.__is_ellipse(c, img_morphology.shape):
                        #print("Accept Ellipse")
                        img_original = self.__trim_image_mask(kwargs['img'], 4)  # Hardcode
                        if not self.__has_garbage(img_original, c, kwargs['cytoplasm']):
                            self.nucleis = cv2.drawContours(self.nucleis, c-8, -1, 255, -1)
                            elements += 1
                            kwargs['cytoplasm'].area = area_nuclei

                            '''#print("Accept Garbage")
                            img_aux = np.zeros(img_morphology.shape, np.uint8)
                            img_aux = cv2.drawContours(img_aux, c, -1, 255, 1)
                            img_aux = cv2.drawContours(img_aux, contours, 0, 255, 1)
                            cv2.imshow('binary', img_aux)
                            cv2.imwrite('binary.jpg', img_aux)
                            cv2.imshow('original2', img_original)

                            cv2.waitKey(0)'''
        return elements

    # _____________________________Public methods______________________________
    # ______________________________Inner classes______________________________

    class NucleiError(Exception):
        def __init__(self, msg: str):
            super().__init__(msg)

    # ______________________________Inner classes______________________________


if __name__ == "__main__":
    import doctest

    doctest.testmod()
