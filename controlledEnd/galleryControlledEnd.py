import json
import queue
import typing
from time import sleep

import numpy as np
import wiringpi

import controlledEnd
import frameDecorator
from components import galleryBrowser, configLoader


class GalleryControlledEnd(controlledEnd.ControlledEnd, galleryBrowser.GalleryBrowser):
    def __init__(self, _id='GalleryControlledEnd', width=128, height=128):
        controlledEnd.ControlledEnd.__init__(self, _id)
        self.__config = configLoader.ConfigLoader('./config.json')
        try:
            galleryBrowser.GalleryBrowser.__init__(self, self.__config['camera']['path'], width, height)
        except IndexError:
            pass
        self.__width, self.__height = width, height
        self.__direction = 0
        with open(self.__config['gallery']['configFilePath']) as f:
            self.__option: typing.Dict[typing.Dict] = json.load(f)
        self.__frameList = queue.Queue()
        self.__busy = frameDecorator.Busy()
        self.__rotate = 0
        self.__currentFrame = np.zeros((self.__width, self.__height, 3), np.uint8)
        self.__hist = frameDecorator.Hist(fill=True)
        self.__rawFrame = None
        self.__from = None

    def __findOptionByContent(self, key):
        for _ in self.__option.keys():
            if 'options' in self.__option[_].keys():
                for j in self.__option[_]['options']:
                    if 'content' in j.keys() and 'value' in j.keys():
                        if j['content'] == key:
                            return j['value']
        raise IndexError

    def centerPressAction(self):
        pass

    def upPressAction(self):
        try:
            self.previous()
        except IndexError:
            return
        self.__refreshFrame()
        sleep(0.2)

    def downPressAction(self):
        try:
            self.next()
        except IndexError:
            return
        self.__refreshFrame()
        sleep(0.2)

    def leftPressAction(self):
        try:
            self.previous()
        except IndexError:
            return
        self.__refreshFrame()
        sleep(0.2)

    def rightPressAction(self):
        try:
            self.next()
        except IndexError:
            return
        self.__refreshFrame()
        sleep(0.2)

    def __addHist(self):
        if self.__findOptionByContent("Show Hist"):
            self.__hist.decorate(self.__currentFrame)
        else:
            self.__currentFrame = self.__rawFrame.copy()

    def circlePressAction(self):
        pass

    def trianglePressAction(self):
        t = 0
        while wiringpi.digitalRead(self.__config['pin']['triangle']) and t < 1:
            t += 0.01
            sleep(0.01)
        if t < 0.09:
            return
        if t >= 1:
            self._irq('CameraControlledEnd')
        else:
            self._irq('MenuControlledEnd')

    def msgReceiver(self, sender, msg):
        if sender == 'MenuControlledEnd':
            if msg == 'delete':
                self.delete()
                self.__refreshFrame()

    def __refreshFrame(self):
        if self.__currentFrame is not None:
            self.__busy.decorate(self.__currentFrame)#, rotate=self.__rotate)
            self.__frameList.put(self.__currentFrame)
        try:
            self.__rawFrame = self.getPict()
            self.__currentFrame = self.__rawFrame.copy()
            self.__addHist()
            self.__frameList.put(self.__currentFrame)
        except AttributeError:
            self.__currentFrame = frameDecorator.Warining(self.__width, self.__height).decorate("Empty")
            self.__frameList.put(self.__currentFrame, True)

    def mainLoop(self):
        while True:
            pict = self.__frameList.get(block=True)
            yield np.rot90(pict, -self.__rotate // 90)

    def direction(self, direction):
        self.__rotate = direction
        self.__frameList.put(self.__currentFrame)

    def onExit(self):
        self.__frameList.put(self.__currentFrame)

    def onEnter(self, lastID):
        try:
            self.refreshPictList()
        except IndexError:
            self._irq(lastID)
        self.__from = lastID
        self.__refreshFrame()
        self._msgSender(self._id, "MenuControlledEnd", self.__option)
