import os

import cv2


class Hdr:
    def __init__(self, imageList: list):
        self.__imageList = imageList
        alignMTB = cv2.createAlignMTB()
        alignMTB.process(self.__imageList, self.__imageList)

    def exposureFusion(self):
        mergeMertens = cv2.createMergeMertens()
        exposureFusion = mergeMertens.process(self.__imageList)
        return exposureFusion * 255


if __name__ == '__main__':

    frameList = list()
    for i in os.listdir('../temp'):
        frameList.append(cv2.imread(os.path.join('../temp', i)))
    h = Hdr(frameList)
    h.exposureFusion('1.png')
