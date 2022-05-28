import functools
import imghdr
import os

import cv2


class GalleryBrowser:
    def __init__(self, pictPath='./pict', width=128, height=128):
        self.__pictPath = pictPath
        if not os.path.exists(self.__pictPath):
            os.makedirs(self.__pictPath)
        self.__width, self.__height = width, height
        self.__index = 0
        self.__filePathList = list()
        self.refreshPictList()
        self.__direction = 0

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

    def next(self):
        if self.__index == len(self.__filePathList) - 1:
            return self
        self.__index += 1
        self.__direction = 0
        return self

    def previous(self):
        if self.__index == 0:
            return self
        self.__index -= 1
        self.__direction = 1
        return self

    def getPict(self):
        return self.__getPict(self.__filePathList[self.__index])

    @functools.lru_cache(maxsize=10)
    def __getPict(self, filename):
        return cv2.resize(cv2.imread(filename), (self.__width, self.__height))

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
