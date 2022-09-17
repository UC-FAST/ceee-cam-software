from collections import Iterable
from math import ceil

import cv2
import numpy as np


class SimpleText:
    def __init__(self,
                 func: list,
                 height: int,
                 padding: tuple = (0, 0, 0, 0),
                 fontHeight: int = 12,
                 color: tuple = (255, 255, 255),
                 thickness: float = 1
                 ):
        self.__fontHeight = fontHeight
        self.__fontSize = cv2.getFontScaleFromHeight(cv2.FONT_ITALIC, self.__fontHeight)
        self.__height = height
        self.__padding = padding
        self.__color = color
        self.__thickness = thickness
        self.funcList = tuple(func)
        self.__index = 0

    def nextPage(self):
        if self.__index == len(self.funcList) - 1:
            return
        else:
            self.__index += 1

    def previousPage(self):
        if self.__index == 0:
            return
        else:
            self.__index -= 1

    def setPage(self, page: int):
        if page < len(self.funcList):
            self.__index = page
        else:
            raise IndexError

    def decorate(self, frame, rotate=0):
        sketch = np.zeros(frame.shape, np.uint8)
        widget = self.funcList[self.__index]()
        totalHeight = self.__height - self.__padding[1] - self.__padding[3]
        textCount = len(widget)
        spaceCount = 1 if textCount == 1 else textCount - 1
        step = ceil((totalHeight - textCount * self.__fontHeight) / spaceCount)
        for index, (key, value) in enumerate(widget.items()):
            if isinstance(value, str):
                cv2.putText(
                    sketch,
                    key.format(value),
                    (self.__padding[0], self.__padding[1] + index * (step + self.__fontHeight)),
                    cv2.FONT_ITALIC,
                    self.__fontSize,
                    self.__color,
                    self.__thickness
                )
            elif isinstance(value, Iterable):
                cv2.putText(
                    sketch,
                    key.format(*tuple(value)),
                    (self.__padding[0], self.__padding[1] + index * (step + self.__fontHeight)),
                    cv2.FONT_ITALIC,
                    self.__fontSize,
                    self.__color,
                    self.__thickness
                )
            else:
                cv2.putText(
                    sketch,
                    key.format(value),
                    (self.__padding[0], self.__padding[1] + index * (step + self.__fontHeight)),
                    cv2.FONT_ITALIC,
                    self.__fontSize,
                    self.__color,
                    self.__thickness
                )
        sketch = np.rot90(sketch, -rotate // 90)
        cv2.addWeighted(sketch, 1, frame, 1, 0, frame)
