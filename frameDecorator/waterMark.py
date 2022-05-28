import cv2
import numpy as np


class WaterMark:
    def __init__(self, width=128, height=128, fontHeight=0):
        self.__width = width
        self.__height = height
        if fontHeight:
            self.__fontHeight = fontHeight
            self.__fontSize = cv2.getFontScaleFromHeight(cv2.FONT_HERSHEY_DUPLEX, self.__fontHeight)
        else:
            self.__fontHeight = self.__height // 35
            self.__fontSize = cv2.getFontScaleFromHeight(cv2.FONT_HERSHEY_DUPLEX, self.__fontHeight)

    def decorate(self, frame, rotate=0):
        circleCoordinate = (
            int(self.__width / 20.6) + self.__fontHeight // 2,
            self.__height - (int(self.__height / 39.3) + self.__fontHeight // 2)
        )
        sketch = np.zeros(frame.shape, np.uint8)
        cv2.circle(sketch, circleCoordinate, int(self.__fontHeight / 2.8), (255, 255, 255), 1, cv2.LINE_AA)
        cv2.circle(sketch, circleCoordinate, int(self.__fontHeight / 1.8), (255, 255, 255), 2, cv2.LINE_AA)
        cv2.addWeighted(sketch, 0.4, frame, 1, 0, frame)
        sketch = np.zeros(frame.shape, np.uint8)

        cv2.putText(sketch,
                    "CEEE",
                    (
                        circleCoordinate[0] + self.__fontHeight // 2 + self.__width // 70,
                        circleCoordinate[1] + self.__fontHeight // 2
                    ),
                    cv2.FONT_HERSHEY_DUPLEX,
                    self.__fontSize,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA
                    )
        sketch = np.rot90(sketch, -rotate // 90)
        cv2.addWeighted(sketch, 0.6, frame, 1, 0, frame)
