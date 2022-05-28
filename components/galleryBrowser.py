import imghdr
import os
import threading
from typing import List

import cv2
import numpy as np


class GalleryBrowser:
    def __init__(self, pictPath='./pict', width=128, height=128):
        self.__pictPath = pictPath
        if not os.path.exists(self.__pictPath):
            os.makedirs(self.__pictPath)
        self.__width, self.__height = width, height
        self.__index = 0
        self.__filePathList = list()
        self.__cache: List[np.array] = [None, None, None]
        self.__loadNext = None
        self.__loadPrevious = None
        self.__browseDirection = 1
        self.refreshPictList()

    def __loadNextPictInAnotherThread(self):
        self.__cache[0] = self.__cache[1]
        self.__cache[1] = self.__cache[2]
        if self.__index == len(self.__filePathList) - 1:
            self.__cache[2] = None
        else:
            self.__cache[2] = cv2.resize(
                cv2.imread(self.__filePathList[self.__index + 1]),
                (self.__width, self.__height)
            )

    def __loadPreviousPictInAnotherThread(self):
        self.__cache[2] = self.__cache[1]
        self.__cache[1] = self.__cache[0]
        if self.__index == 0:
            self.__cache[0] = None
        else:
            self.__cache[0] = cv2.resize(
                cv2.imread(self.__filePathList[self.__index - 1]),
                (self.__width, self.__height)
            )

    def refreshPictList(self):
        self.__filePathList = list()
        for file in os.listdir(self.__pictPath):
            if os.path.isdir(os.path.join(self.__pictPath, file)):
                continue
            filePath = os.path.join(self.__pictPath, file)
            fmat = imghdr.what(filePath)
            if (file.endswith('.dng') and fmat == 'tiff') or not fmat:
                continue
            self.__filePathList.append(filePath)
        self.__filePathList.sort(key=lambda x: os.path.splitext(x)[0])
        self.__index = 0
        if not self.__filePathList:
            raise IndexError
        self.__filePathList = self.__filePathList[::-1]
        self.__cache[0] = None
        self.__cache[1] = cv2.resize(
            cv2.imread(self.__filePathList[self.__index]),
            (self.__width, self.__height)
        )
        if len(self.__filePathList) == 1:
            self.__cache[2] = None
        else:
            self.__cache[2] = cv2.resize(
                cv2.imread(self.__filePathList[self.__index + 1]),
                (self.__width, self.__height)
            )

    def next(self):
        if self.__index == len(self.__filePathList) - 1:
            raise IndexError

        if self.__loadNext is not None and self.__loadNext.is_alive():
            self.__loadNext.join()

        self.__index += 1
        self.__browseDirection = 1
        self.__loadNext = threading.Thread(target=self.__loadNextPictInAnotherThread)
        self.__loadNext.start()
        return self

    def previous(self):
        if self.__index == 0:
            raise IndexError
        if self.__loadPrevious is not None and self.__loadPrevious.is_alive():
            self.__loadPrevious.join()
        self.__index -= 1
        self.__browseDirection = 0
        self.__loadPrevious = threading.Thread(target=self.__loadPreviousPictInAnotherThread)
        self.__loadPrevious.start()
        return self

    def getPict(self):
        if self.__browseDirection == 1 and self.__loadNext:
            self.__loadNext.join()
        elif self.__browseDirection == 0 and self.__loadPrevious:
            self.__loadPrevious.join()
        frame = self.__cache[1]

        if frame is not None:
            return frame.copy()

    def delete(self):
        filename = self.__filePathList[self.__index]
        os.remove(filename)
        self.__cache.pop(filename)
        self.__filePathList.remove(filename)
        if self.__index == len(self.__filePathList):
            self.__index = len(self.__filePathList) - 1
        else:
            self.next()

    def getPictName(self):
        return self.__filePathList[self.__index]


if __name__ == '__main__':
    a = GalleryBrowser('./example')
    print(a.getPictName())
    print(a.next().getPictName())
    print(a.previous().getPictName())
