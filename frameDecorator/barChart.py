from math import ceil, inf

import cv2
import numpy as np


class BarChart:
    def __init__(self, width=128, height=128, maxSize=128, scale=0, color=(0, 0, 255), thickness=1, fill=False,
                 alpha: float = 1):
        self.__step = ceil(width / maxSize)
        self.__maxSize = maxSize
        self.__height = height
        self.__scale = scale
        self.__color = color
        self.__thickness = thickness
        self.__fill = fill
        if 0 <= alpha <= 1:
            self.__alpha = alpha
        elif alpha <= 0:
            self.__alpha = 0
        elif alpha >= 1:
            self.__alpha = 1
        self.__max = -inf
        self.__min = inf
        self.__dataList = list()

    @property
    def dataList(self):
        return self.__dataList

    @dataList.setter
    def dataList(self, datas):
        if len(datas) > self.__maxSize:
            temp = list()
            step = len(datas) // self.__maxSize
            for i in range(0, len(datas), step):
                s = 0
                for j in range(step):
                    s += datas[i + j]
                average = s / step
                temp.append(average)

            self.__dataList = temp
        else:
            self.__dataList = datas
        for i in self.__dataList:
            if i < self.__min:
                self.__min = i
            if i > self.__max:
                self.__max = i

    def addData(self, data):
        if not self.__scale:
            if len(self.__dataList) == self.__maxSize:
                temp = self.__dataList.pop(0)
                if temp == self.__max:
                    self.__max = max(self.__dataList)
                elif temp == self.__min:
                    self.__min = min(self.__dataList)

            if data > self.__max:
                self.__max = data
            if data < self.__min:
                self.__min = data
            self.__dataList.append(data)

        else:
            if len(self.__dataList) == self.__maxSize:
                self.__dataList.pop(0)

            self.__dataList.append(data)
        return self

    def decorate(self, frame, rotate=0):
        sketch = np.zeros(frame.shape, np.uint8)
        if self.__alpha == 1:
            for index, i in enumerate(self.__dataList):
                if self.__scale:
                    i /= self.__scale
                else:
                    try:
                        i = 10 + (90 - 10) / (self.__max - self.__min) * (i - self.__min)
                    except ZeroDivisionError:
                        i = 10

                if self.__fill:
                    cv2.rectangle(sketch,
                                  (index * self.__step, int(self.__height - (i / 100 * self.__height))),
                                  (int((index + 1) * self.__step), self.__height),
                                  color=self.__color,
                                  thickness=-1)
                else:
                    cv2.rectangle(sketch,
                                  (index * self.__step,
                                   int(self.__height - (i / 100 * self.__height) - self.__thickness)),
                                  (int((index + 1) * self.__step), int(self.__height - (i / 100 * self.__height))),
                                  color=self.__color,
                                  thickness=1)
        else:
            sketchChart = np.zeros(frame.shape, np.uint8)
            for index, i in enumerate(self.__dataList):
                if self.__scale:
                    i /= self.__scale
                else:
                    try:
                        i = 10 + (90 - 10) / (self.__max - self.__min) * (i - self.__min)
                    except ZeroDivisionError:
                        i = 10

                if self.__fill:
                    cv2.rectangle(sketchChart,
                                  (index * self.__step, int(self.__height - (i / 100 * self.__height))),
                                  (int((index + 1) * self.__step), self.__height),
                                  color=self.__color,
                                  thickness=-1)
                else:
                    cv2.rectangle(sketchChart,
                                  (index * self.__step,
                                   int(self.__height - (i / 100 * self.__height) - self.__thickness)),
                                  (int((index + 1) * self.__step), int(self.__height - (i / 100 * self.__height)) - 1),
                                  color=self.__color,
                                  thickness=1)

            cv2.addWeighted(sketchChart, self.__alpha, sketch, 1, 0, sketch)
        sketch = np.rot90(sketch, -rotate // 90)
        cv2.addWeighted(sketch, 1, frame, 1, 0, frame)
