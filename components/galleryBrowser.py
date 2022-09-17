import imghdr
import os
import threading
import typing

import cv2


class GalleryBrowser:
    def __init__(self, pictPath='./pict/', width=None, height=None):
        self.__pictPath = pictPath
        if not os.path.exists(self.__pictPath):
            os.makedirs(self.__pictPath)
        self.__width, self.__height = width, height
        self.__index = 0
        self.__filePathList = list()
        self.__direction = 0
        self.__cache: typing.List[(typing.Tuple, None)] = [None, None, None]
        self.__load = None

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
        if not self.__filePathList:
            raise FileNotFoundError
        self.__filePathList.sort(key=lambda x: os.path.splitext(x)[0], reverse=True)
        self.__index = 0

        self.__cache[0] = None
        frame = cv2.imread(self.__filePathList[self.__index])
        if self.__width and self.__height:
            frame = cv2.resize(frame, (self.__width, self.__height))
        self.__cache[1] = (0, frame)
        try:
            frame = cv2.imread(self.__filePathList[self.__index + 1])
            if self.__width and self.__height:
                frame = cv2.resize(frame, (self.__width, self.__height))
            self.__cache[2] = (1, frame)
        except IndexError:
            self.__cache[2] = None

    def next(self):
        if self.__index == len(self.__filePathList) - 1:
            return self
        self.__index += 1
        self.__direction = 0
        if self.__load is not None:
            self.__load.join()

        self.__cache[0] = self.__cache[1]
        self.__cache[1] = self.__cache[2]
        self.__cache[2] = None

        return self

    def previous(self):
        if self.__index == 0:
            return self
        self.__index -= 1
        self.__direction = 1
        if self.__load is not None:
            self.__load.join()

        self.__cache[2] = self.__cache[1]
        self.__cache[1] = self.__cache[0]
        self.__cache[0] = None
        return self

    def __loadImgInAnotherThread(self, pos, index):
        frame = cv2.imread(self.__filePathList[index])
        if self.__width and self.__height:
            frame = cv2.resize(frame, (self.__width, self.__height))
        self.__cache[pos] = (index, frame)
        self.__load = None

    def getPict(self):
        if len(self.__filePathList) == 0:
            raise FileNotFoundError

        if self.__load is not None:
            self.__load.join()

        if self.__cache[0] is None and self.__index != 0:
            self.__load = threading.Thread(
                target=self.__loadImgInAnotherThread,
                args=(0, self.__index - 1)
            )
            self.__load.start()

        elif self.__cache[2] is None and self.__index != len(self.__filePathList) - 1:
            self.__load = threading.Thread(
                target=self.__loadImgInAnotherThread,
                args=(2, self.__index + 1)
            )
            self.__load.start()

        return self.__cache[1][1].copy()

    def delete(self):
        filename = self.__filePathList[self.__index]
        os.remove(filename)
        self.__filePathList.pop(self.__index)

        if self.__index == len(self.__filePathList):
            self.__index = len(self.__filePathList) - 1
            self.__cache[1] = self.__cache[0]
            self.__cache[2] = None
            self.__cache[0] = None
        elif self.__index == 0:
            self.__cache[1] = self.__cache[2]
            self.__cache[0] = None
            self.__cache[2] = None

        elif self.__index != 0:
            if self.__direction == 0:
                self.__cache[1] = self.__cache[2]
                self.__cache[2] = None
            else:
                self.__cache[1] = self.__cache[0]
                self.__cache[0] = None

    def getPictName(self, fullPath=False):
        if fullPath:
            return self.__filePathList[self.__index]
        return self.__filePathList[self.__index].replace(self.__pictPath, '')


if __name__ == '__main__':
    a = GalleryBrowser('./example')
    print(a.getPictName())
    print(a.next().getPictName())
    print(a.previous().getPictName())
