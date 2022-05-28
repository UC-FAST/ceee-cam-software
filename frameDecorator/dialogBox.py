from math import ceil

import cv2
import numpy as np


class DialogBox:
    def __init__(
            self,
            width: int,
            height: int,
            options: list = None,
            title: str = None,
            padding: tuple = (0, 0, 0, 0),
            columnCount: int = 1,
            showIndex: bool = False,
            fontHeight: int = 12,
            color: tuple = (255, 255, 255),
            thickness: int = 1
    ):

        self.__options = options
        self.__columnCount = columnCount
        self.__title = title
        self.__height = height
        self.__width = width
        self.__fontHeight = fontHeight
        self.__padding = padding
        if self.__options:
            if showIndex:
                self.__optionList = tuple(["{}: {}".format(i + 1, x) for i, x in enumerate(options)])
            else:
                self.__optionList = tuple(options)
            self.__verticalStep = self.__verticalStepCalc()
            self.__horizontalStep = self.__horizontalStepCalc()
        else:
            self.__optionList = None

        self.__showIndex = showIndex
        self.__fontSize = cv2.getFontScaleFromHeight(cv2.FONT_ITALIC, fontHeight)
        self.__color = color
        self.__thickness = thickness
        self.__index = 0

    @property
    def options(self):
        return self.__options

    @options.setter
    def options(self, options):
        self.__options = options
        if self.__options:
            if self.__showIndex:
                self.__optionList = tuple(["{}: {}".format(i + 1, x) for i, x in enumerate(options)])
            else:
                self.__optionList = tuple(options)
            self.__verticalStep = self.__verticalStepCalc()
            self.__horizontalStep = self.__horizontalStepCalc()
            self.__index = 0
        else:
            self.__optionList = None

    @property
    def title(self):
        return self.__title

    @title.setter
    def title(self, t):
        if t:
            self.__title = t
            if not self.__title:
                self.__verticalStep = self.__verticalStepCalc()
                self.__horizontalStep = self.__horizontalStepCalc()

        elif not t:
            self.__title = None
            if self.__title:
                self.__verticalStep = self.__verticalStepCalc()
                self.__horizontalStep = self.__horizontalStepCalc()

    def __verticalStepCalc(self):
        lineCount = ceil(len(self.__optionList) / self.__columnCount)
        if self.__title:
            lineCount += 1
        spaceCount = lineCount
        heightTotal = self.__height - self.__padding[1] - self.__padding[3]
        spaceTotal = heightTotal - lineCount * self.__fontHeight
        return int(spaceTotal / spaceCount)

    def __horizontalStepCalc(self):
        return int((self.__width - self.__padding[0] - self.__padding[2]) / self.__columnCount)

    def setIndex(self, index: int):
        if not self.__optionList or index < len(self.__optionList):
            raise IndexError
        self.__index = index

    def getCurrentIndex(self):
        if self.__options:
            return self.__index
        raise IndexError

    def optionUp(self):
        if self.__index - self.__columnCount < 0:
            return
        else:
            self.__index -= self.__columnCount

    def optionDown(self):
        if (len(self.__optionList) - self.__columnCount) <= self.__index < len(self.__optionList):
            return
        else:
            self.__index += self.__columnCount

    def optionRight(self):
        self.__index = self.__index if self.__index == len(self.__optionList) - 1 else self.__index + 1

    def optionLeft(self):
        self.__index = 0 if self.__index == 0 else self.__index - 1

    def decorate(self, frame, rotate=0):
        sketch = np.zeros(frame.shape, np.uint8)
        verticalOffset = self.__padding[1] + self.__fontHeight
        if self.__title:
            verticalOffset += self.__verticalStep + self.__fontHeight
            totalWidth = self.__width - self.__padding[0] - self.__padding[2]
            x = (totalWidth - len(self.__title) * self.__fontHeight) // 2

            cv2.putText(
                sketch,
                self.__title,
                (
                    self.__padding[0] + x,
                    self.__fontHeight + self.__padding[1]
                ),
                cv2.FONT_ITALIC, self.__fontSize,
                self.__color,
                self.__thickness
            )
        currentIndex = 0
        for i in range(ceil(len(self.__optionList) / self.__columnCount)):
            for j in range(self.__columnCount):
                try:
                    coordinate = (
                        j * self.__horizontalStep + self.__padding[0],
                        i * (self.__fontHeight + self.__verticalStep) + verticalOffset
                    )
                    if currentIndex == self.__index:
                        cv2.rectangle(sketch,
                                      (coordinate[0], coordinate[1] - self.__fontHeight),
                                      (coordinate[0] + self.__horizontalStep, coordinate[1]),
                                      color=(255, 0, 0),
                                      thickness=-self.__thickness
                                      )

                    cv2.putText(
                        sketch,
                        self.__optionList[i * self.__columnCount + j],
                        coordinate,
                        cv2.FONT_ITALIC, self.__fontSize,
                        self.__color,
                        self.__thickness
                    )
                    currentIndex += 1
                except IndexError:
                    break
        if rotate:
            sketch = np.rot90(sketch, -rotate // 90)

        cv2.addWeighted(sketch, 1, frame, 0.3, 0, frame)
