from collections.abc import Iterable
from math import ceil
import cv2
import numpy as np


class SimpleText:

    def __init__(
        self,
        funcList: list,
        height: int,
        padding: tuple = (5, 5, 5, 5),
        fontHeight: int = 24,
        color: tuple = (255, 255, 255),
        thickness: float = 1
    ):

        if height <= 0:
            raise ValueError("Height must be positive")
        if any(p < 0 for p in padding):
            raise ValueError("Padding values must be non-negative")
        if not funcList:
            raise ValueError("Function list cannot be empty")

        self.__fontHeight = fontHeight
        self.__fontSize = cv2.getFontScaleFromHeight(
            cv2.FONT_ITALIC, self.__fontHeight)
        self.__height = height
        self.__padding = padding
        self.__color = color
        self.__thickness = thickness
        self.__funcList = tuple(funcList)
        self.__index = 0

    @property
    def currentPage(self):
        return self.__index

    @property
    def totalPages(self):
        return len(self.__funcList)

    def nextPage(self):
        self.__index = min(self.__index + 1, self.totalPages - 1)

    def previousPage(self):
        self.__index = max(self.__index - 1, 0)

    def setPage(self, page: int):
        if 0 <= page < self.totalPages:
            self.__index = page
        else:
            raise IndexError(
                f"Page index out of range [0, {self.totalPages - 1}]")

    def decorate(self, frame, rotate=0):
        widget = self.__funcList[self.__index]()
        if not widget:
            return frame

        sketch = np.zeros_like(frame, dtype=np.uint8)
        _, topPadding,  _, bottomPadding = self.__padding
        availableHeight = self.__height - topPadding - bottomPadding
        textCount = len(widget)

        if textCount == 1:
            step = 0
        else:
            totalTextHeight = textCount * self.__fontHeight
            step = ceil((availableHeight - totalTextHeight) / (textCount - 1))

        leftPadding = self.__padding[0]
        yPos = topPadding

        for key, value in widget.items():

            if isinstance(value, str):
                text = key.format(value)
            elif isinstance(value, Iterable) and not isinstance(value, str):
                text = key.format(*value)
            else:
                text = key.format(value)

            cv2.putText(
                sketch,
                text,
                (leftPadding, yPos),
                cv2.FONT_ITALIC,
                self.__fontSize,
                self.__color,
                self.__thickness,
            )
            yPos += self.__fontHeight + step

        if rotate != 0:
            rotateTimes = (-rotate // 90) % 4
            if rotateTimes:
                sketch = np.rot90(sketch, rotateTimes)

        cv2.addWeighted(sketch, 1, frame, 1, 0, frame)
        return frame
