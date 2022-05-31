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
        except FileNotFoundError:
            pass
        self.__width, self.__height = width, height
        self.__direction = 0
        with open(self.__config['gallery']['configFilePath']) as f:
            self.__option: typing.Dict[typing.Dict] = json.load(f)
        self.__frameList = queue.SimpleQueue()
        self.__busy = frameDecorator.Busy()
        self.__rotate = 0
        self.__currentFrame = np.zeros((self.__width, self.__height, 3), np.uint8)
        self.__hist = frameDecorator.Hist(fill=True)
        self.__rawFrame = None
        self.__from = None

    def __findOptionByID(self, target):
        for key, value in self.__option.items():
            if 'options' in value.keys():
                for j in value['options']:
                    if 'id' in j.keys() and 'value' in j.keys():
                        if j['id'] == target:
                            return j['value']
        raise IndexError

    def centerPressAction(self):
        pass

    def upPressAction(self):
        self.previous()
        self.__refreshFrame()
        sleep(0.2)

    def downPressAction(self):
        self.next()
        self.__refreshFrame()
        sleep(0.2)

    def leftPressAction(self):
        self.previous()
        self.__refreshFrame()
        sleep(0.2)

    def rightPressAction(self):
        self.next()
        self.__refreshFrame()
        sleep(0.2)

    def __addHist(self):
        if self.__findOptionByID("show hist"):
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
            elif msg == 'update':
                self.update()
            else:
                with open(self.__config['gallery']['configFilePath'], 'w') as f:
                    json.dump(self.__option, f, indent=4)

    def update(self):
        pass

    def __refreshFrame(self):
        if self.__currentFrame is not None:
            self.__busy.decorate(self.__currentFrame)
            self.__frameList.put(self.__currentFrame)

        self.__rawFrame = self.getPict()
        self.__currentFrame = self.__rawFrame.copy()
        self.__addHist()
        self.__frameList.put(self.__currentFrame)

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
        except FileNotFoundError:
            self._irq(lastID)
        self.__from = lastID
        self.__refreshFrame()
        self._msgSender(self._id, "MenuControlledEnd", self.__option)
