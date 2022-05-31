import imghdr
import os
import threading
import typing

import cv2


class GalleryBrowser:
    def __init__(self, pictPath='./pict', width=128, height=128):
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
        self.__filePathList.sort(key=lambda x: os.path.splitext(x)[0], reverse=True)
        self.__index = 0
        if not self.__filePathList:
            raise FileNotFoundError

        self.__cache[0] = None
        self.__cache[1] = (
            0,
            cv2.resize(
                cv2.imread(self.__filePathList[self.__index]),
                (self.__width, self.__height)
            )
        )
        self.__cache[2] = (
            1,
            cv2.resize(
                cv2.imread(self.__filePathList[self.__index + 1]),
                (self.__width, self.__height)
            )
        )

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
        self.__cache[pos] = (
            index,
            cv2.resize(
                cv2.imread(self.__filePathList[index]),
                (self.__width, self.__height)
            )
        )
        self.__load = None

    def getPict(self):
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

        if self.__index == len(self.__filePathList) - 1:
            self.__index = len(self.__filePathList) - 2

        elif self.__index != 0:
            if self.__direction == 0:
                self.next()
            else:
                self.previous()

        self.__filePathList.remove(filename)

    def getPictName(self):
        return self.__filePathList[self.__index]


if __name__ == '__main__':
    a = GalleryBrowser('./example')
    print(a.getPictName())
    print(a.next().getPictName())
    print(a.previous().getPictName())
