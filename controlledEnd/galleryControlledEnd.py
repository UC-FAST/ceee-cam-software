import queue
import typing
from time import sleep

import numpy as np

import controlledEnd
import frameDecorator
from components import galleryBrowser


class GalleryControlledEnd(controlledEnd.ControlledEnd, galleryBrowser.GalleryBrowser):
    def __init__(self, _id='GalleryControlledEnd', width=320, height=240, pictPath='./pict/'):
        controlledEnd.ControlledEnd.__init__(self, _id)
        pictPath = pictPath if pictPath.endswith('/') else pictPath + '/'
        galleryBrowser.GalleryBrowser.__init__(self, pictPath, width, height)
        self.__width, self.__height = width, height
        self.__direction = 0
        self.__option: typing.Dict[typing.Dict] = None
        self.__frameList = queue.SimpleQueue()
        self.__busy = frameDecorator.Busy()
        self.__rotate = 0
        self.__currentFrame = np.zeros((self.__width, self.__height, 3), np.uint8)
        self.__hist = frameDecorator.Hist(fill=True)
        self.__rawFrame = None
        self.__from = None
        self.__delete = False
        self.__empty = False

        self.__decorator = frameDecorator.SimpleText(
            [self.__worker1],
            height=self.__height,
            padding=(10, 20, 0, 0),
            fontHeight=10,
            color=frameDecorator.Colors.gold.value
        )
        self.__simpleTextEnable = False

    def __worker1(self):
        return {
            "{}": self.getPictName(),
        }

    def __findOptionByID(self, target):
        for key, value in self.__option.items():
            if 'options' in value.keys():
                for j in value['options']:
                    if 'id' in j.keys() and 'value' in j.keys():
                        if j['id'] == target:
                            return j['value']
        raise LookupError('target')

    def centerPressAction(self):
        if self.__empty:
            self.__empty = False
            self._irq(self.__from)
            return

    def upPressAction(self):
        if self.__empty:
            self.__empty = False
            self._irq(self.__from)
            return
        self.previous()
        self.__refreshFrame()
        sleep(0.2)

    def downPressAction(self):
        if self.__empty:
            self.__empty = False
            self._irq(self.__from)
            return
        self.next()
        self.__refreshFrame()
        sleep(0.2)

    def leftPressAction(self):
        if self.__empty:
            self.__empty = False
            self._irq(self.__from)
            return
        self.previous()
        self.__refreshFrame()
        sleep(0.2)

    def rightPressAction(self):
        if self.__empty:
            self.__empty = False
            self._irq(self.__from)
            return
        self.next()
        self.__refreshFrame()
        sleep(0.2)

    def __addHist(self):
        if self.__findOptionByID("show hist"):
            self.__hist.decorate(self.__currentFrame)
        else:
            self.__currentFrame = self.__rawFrame.copy()

    def circlePressAction(self):
        if self.__empty:
            self.__empty = False
            self._irq(self.__from)
            return
        self.__simpleTextEnable = not self.__simpleTextEnable
        self.__refreshFrame()

    def crossPressAction(self):
        pass

    def crossLongPressAction(self):
        if self.__empty:
            self.__empty = False
            self._irq(self.__from)
            return
        self._irq('CameraControlledEnd')

    def squarePressAction(self):
        if self.__empty:
            self.__empty = False
            self._irq(self.__from)
            return
        self._irq('MenuControlledEnd')

    def shutterPressAction(self):
        pass
    
    def rotaryEncoderClockwise(self):
        pass

    def rotaryEncoderCounterClockwise(self):
        pass

    def rotaryEncoderSelect(self):
        pass
    
    def msgReceiver(self, sender, msg):
        if sender == 'MenuControlledEnd':
            self.__option = msg[1]
            if msg[0] == 'delete':
                self.__delete = True
                self.delete()
                self.__refreshFrame()
            elif msg[0] == 'update':
                self.update()

    def update(self):
        pass

    def __refreshFrame(self):
        if self.__currentFrame is not None:
            self.__busy.decorate(self.__currentFrame)
            self.__frameList.put(self.__currentFrame)
        try:
            self.__rawFrame = self.getPict()
        except FileNotFoundError:
            self.__empty = True
            self._irq("CameraControlledEnd")
            return
        self.__currentFrame = self.__rawFrame.copy()
        self.__addHist()
        self.__frameList.put(self.__currentFrame)

    def mainLoop(self):
        while True:
            pict = self.__frameList.get(block=True)
            if self.__simpleTextEnable:
                self.__decorator.decorate(pict)
            yield np.rot90(pict, -self.__rotate // 90)


    def onExit(self):
        self.__frameList.put(frameDecorator.Warining().decorate("Empty"))

    def onEnter(self, lastID):
        try:
            if not self.__delete:
                self.__from = lastID
                self.refreshPictList()
            self.__delete = False
            self._msgSender(self._id, "MenuControlledEnd", self._id)
            self.__refreshFrame()
        except FileNotFoundError:
            self.__empty = True
            self.__frameList.put(frameDecorator.Warining().decorate("Empty"))
