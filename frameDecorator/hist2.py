from math import inf, floor
import cv2
import numpy as np


class Hist2:
    def __init__(self, width=320, height=240, padding=(0, 0, 0, 0)):
        self.__width = width
        self.__padding = padding  # (left, top, right, bottom)
        horizontal = width - padding[0] - padding[2]
        self.__maxSize = min(256, horizontal)
        self.__step = max(1, floor(horizontal / self.__maxSize))
        self.__height = height
        self.__max = -inf
        self.__min = inf
        self.__dataList = [np.array([]), np.array(
            []), np.array([])]

    def __frameCalc(self, frame):
        histChannels = [
            cv2.calcHist([frame], [i], None, [256], [0, 255]).flatten()
            for i in range(3)
        ]

        if len(histChannels[0]) > self.__maxSize:
            step = len(histChannels[0]) // self.__maxSize
            new_len = self.__maxSize * step
            self.__dataList = [
                ch[:new_len].reshape(self.__maxSize, step).mean(axis=1)
                for ch in histChannels
            ]
        else:
            self.__dataList = [ch[:self.__maxSize] for ch in histChannels]

        all_data = np.concatenate(self.__dataList)
        self.__min = np.min(all_data)
        self.__max = np.max(all_data)

    def decorate(self, frame, rotate=0):
        self.__frameCalc(frame)
        sketch = np.zeros((self.__height, self.__width, 3), dtype=np.uint8)

        padLeft, padTop, padRight, padBottom = self.__padding
        plot_height = self.__height - padTop - padBottom
        baseY = self.__height - padBottom

        if self.__max <= self.__min:
            pass
        else:

            normRange = 100.0 if plot_height > 0 else 0
            normData = [
                (ch - self.__min) / (self.__max - self.__min) * normRange
                for ch in self.__dataList
            ]

            barHeights = [
                (ch * plot_height /
                 100).astype(int) if normRange > 0 else np.zeros_like(ch)
                for ch in normData
            ]

            for i in range(len(self.__dataList[0])):
                xStart = padLeft + i * self.__step
                xEnd = xStart + self.__step

                for chIdx, height in enumerate([h[i] for h in barHeights]):
                    if height <= 0:
                        continue

                    yStart = baseY - height
                    color = [0, 0, 0]
                    color[chIdx] = 255
                   
                    cv2.rectangle(
                        sketch,
                        (xStart, yStart),
                        (xEnd, baseY),
                        color,
                        -1
                    )

        
        if rotate != 0:
            rotateTimes = rotate // 90 % 4  # 标准化旋转角度
            if rotateTimes != 0:
                sketch = np.rot90(sketch, rotateTimes)

        cv2.add(sketch, frame, frame)
