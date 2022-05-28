import cv2
import numpy as np


class Toast:
    def __init__(
            self,
            width=128,
            height=128,
            fontHeight=12,
    ):
        self.__width = width
        self.__height = height
        self.__fontHeight = fontHeight
        self.__fontScale = cv2.getFontScaleFromHeight(cv2.FONT_ITALIC, self.__fontHeight)
        self.__text = None
        self.__offsetRight = 0
        self.__offsetLeft = self.__width
        self.__isUpdate = False

    @property
    def isUpdate(self):
        return self.__isUpdate

    def setText(self, text: str):
        if not self.__text or len(text) != len(self.__text):
            self.__offsetRight = (self.__width - len(text) * self.__fontHeight) // 2 - self.__fontHeight
            self.__offsetLeft = (self.__width + len(text) * self.__fontHeight) // 2 + self.__fontHeight
        self.__text = text
        self.__isUpdate = True

    def decorate(self, frame, rotate=0):
        if self.__text:
            sketch = np.zeros(frame.shape, np.uint8)
            cv2.rectangle(
                sketch,
                (self.__offsetRight, int(self.__height * 0.96 - self.__fontHeight)),
                (self.__offsetLeft, int(self.__height * 0.96)),
                (255, 0, 0),
                -1
            )
            cv2.putText(
                sketch,
                self.__text,
                (self.__offsetRight + self.__fontHeight, int(self.__height * 0.96)),
                cv2.FONT_ITALIC,
                self.__fontScale,
                (255, 255, 255)
            )
            if rotate:
                sketch = np.rot90(sketch, -rotate // 90)
            cv2.addWeighted(sketch, 1, frame, 1, 0, frame)
            self.__isUpdate = False
