import multiprocessing
import subprocess
import threading
import time
from typing import List

import gpiozero

import controlledEnd
import frameDecorator
from components import lcd20, configLoader
from utils import exceptionRecorder, initialize_logger


class UniversalControl:
    def __init__(self, lcd: lcd20.Lcd, controlledEndList: List[controlledEnd.ControlledEnd]):
        self.__controlledEndList = controlledEndList
        self.__config = configLoader.ConfigLoader('./config.json')
        self.__logger = initialize_logger(
            console_level=self.__config['debug_level'])
        self.__enable = True
        self.__rights = 0  # Current controlled end in use
        self.__lastWidget = None  # Last controlled end, used for return operation
        self.__lcd = lcd
        self.__lcd.Init()
        self.__direction = 0
        self.__menuEnable = False
        self.__decorateEnable = False
        self.__zoom = 1
        self.__frame = None  # Frame gen by current controlled end
        self.__signal = False

        for i in self.__controlledEndList:
            i.irq(self.__irq)
            # Assign UniversalControl.__msgSender to controlledEnd
            i.msgSender(self.__msgSender)

        self.__gpioInit()

        self.__w = frameDecorator.Warining()
        self.__frameList = multiprocessing.Queue(maxsize=1)
        self.__t = multiprocessing.Process(
            target=self.showImageInAnotherProcess, args=(self.__frameList,))
        self.__logger.info("UniversalControl initialized")

    def __gpioInit(self):

        self.__shutter = gpiozero.DigitalInputDevice(
            pin=self.__config['pin']['shutter']
        )
        self.__shutter.when_activated = self.__shutterPressAction

        self.__square = gpiozero.DigitalInputDevice(
            pin=self.__config['pin']['square']
        )
        self.__square.when_activated = self.__squarePressAction

        self.__cross = gpiozero.DigitalInputDevice(
            pin=self.__config['pin']['cross']
        )
        self.__cross.when_activated = self.__crossPressAction

        self.__circle = gpiozero.DigitalInputDevice(
            pin=self.__config['pin']['circle']
        )
        self.__circle.when_activated = self.__circlePressAction

        self.__up = gpiozero.DigitalInputDevice(
            pin=self.__config['pin']['up']
        )
        self.__up.when_activated = self.__upPressAction
        self.__up.when_deactivated = self.__upReleaseAction

        self.__down = gpiozero.DigitalInputDevice(
            pin=self.__config['pin']['down']
        )
        self.__down.when_activated = self.__downPressAction
        self.__down.when_deactivated = self.__downReleaseAction

        self.__left = gpiozero.DigitalInputDevice(
            pin=self.__config['pin']['left']
        )
        self.__left.when_activated = self.__leftPressAction
        self.__left.when_deactivated = self.__leftReleaseAction

        self.__right = gpiozero.DigitalInputDevice(
            pin=self.__config['pin']['right']
        )
        self.__right.when_activated = self.__rightPressAction
        self.__right.when_deactivated = self.__rightReleaseAction

        self.__center = gpiozero.DigitalInputDevice(
            pin=self.__config['pin']['center']
        )
        self.__center.when_activated = self.__centerPressAction
        self.__center.when_deactivated = self.__centerReleaseAction

        self.__rotaryEncoderSelect = gpiozero.DigitalInputDevice(
            pin=self.__config['pin']['rotaryEncoder1S']
        )
        self.__rotaryEncoderSelect.when_activated = self.__rotaryEncoderSelectAction

        self.__rotaryEncoder = gpiozero.RotaryEncoder(
            self.__config['pin']['rotaryEncoder1A'],
            self.__config['pin']['rotaryEncoder1B']
        )
        self.__rotaryEncoder.when_rotated_clockwise = self.__rotaryEncoderClockwise
        self.__rotaryEncoder.when_rotated_counter_clockwise = self.__rotaryEncoderCounterClockwise

    def __msgReceiver(self, msg):
        if msg == 'restart':
            subprocess.run(['sudo', 'reboot'])

    @exceptionRecorder()
    def __irq(self, _id: str):
        """
        Switch the control right of controlledEnd.
        """
        self.__logger.info("Irq to {}".format(_id))
        # Look up controlled end in list
        for index, widget in enumerate(self.__controlledEndList):
            if widget.id == _id:
                self.__signal = True
                self.__lastWidget = self.__controlledEndList[self.__rights].id
                oldRights = self.__rights
                self.__rights = index
                self.__controlledEndList[oldRights].onExit()
                break
        else:
            raise LookupError(_id)

    @exceptionRecorder()
    def __msgSender(self, sender: str, receiver: str, msg):
        """

        """
        self.__logger.info("Message from {} to {}".format(sender, receiver))
        self.__logger.debug("Message: {}".format(msg))
        if receiver == 'UniversalControl':
            self.__msgReceiver(msg)
            return
        for widget in self.__controlledEndList:
            if widget.id == receiver:
                widget.msgReceiver(sender, msg)
                break
        else:
            raise LookupError(receiver)

    @exceptionRecorder()
    def showImageInAnotherThread(self, imgList: list):
        while True:
            self.__lcd.showImage(imgList.get(True))

    @exceptionRecorder()
    def showImageInAnotherProcess(self, imgList: multiprocessing.Queue):
        while True:
            self.__lcd.showImage(imgList.get(True))

    @exceptionRecorder()
    def __centerPressAction(self):
        self.__logger.debug("Center press action")
        if not self.__enable:
            return
        self.__controlledEndList[self.__rights].centerPressAction()

    @exceptionRecorder()
    def __centerReleaseAction(self):
        self.__logger.debug("Center release action")
        if not self.__enable:
            return
        self.__controlledEndList[self.__rights].centerReleaseAction()

    def __circlePressAction(self):
        self.__logger.debug("Circle action")
        if not self.__enable:
            return
        self.__controlledEndList[self.__rights].circlePressAction()

    @exceptionRecorder()
    def __squarePressAction(self):
        self.__logger.debug("Square action")
        if not self.__enable:
            return
        self.__controlledEndList[self.__rights].squarePressAction()

    @exceptionRecorder()
    def __crossPressAction(self):
        self.__logger.debug("Cross action")
        if not self.__enable:
            return
        self.__controlledEndList[self.__rights].crossPressAction()

    def __shutterPressAction(self):
        self.__logger.debug("Shutter press action")
        if not self.__enable:
            return
        self.__controlledEndList[self.__rights].shutterPressAction()

    def __upPressAction(self):
        self.__logger.debug('Up press action')
        self.__controlledEndList[self.__rights].upPressAction()

    def __downPressAction(self):
        self.__logger.debug('Down press action')
        self.__controlledEndList[self.__rights].downPressAction()

    def __rightPressAction(self):
        self.__logger.debug('Right press action')
        self.__controlledEndList[self.__rights].rightPressAction()

    def __leftPressAction(self):
        self.__logger.debug('Left press action')
        self.__controlledEndList[self.__rights].leftPressAction()

    def __upReleaseAction(self):
        self.__logger.debug('Up release action')
        self.__controlledEndList[self.__rights].upReleaseAction()

    def __downReleaseAction(self):
        self.__logger.debug('Down release action')
        self.__controlledEndList[self.__rights].downReleaseAction()

    def __rightReleaseAction(self):
        self.__logger.debug('Right release action')
        self.__controlledEndList[self.__rights].rightReleaseAction()

    def __leftReleaseAction(self):
        self.__logger.debug('Left release action')
        self.__controlledEndList[self.__rights].leftReleaseAction()

    def __rotaryEncoderSelectAction(self):
        self.__logger.debug('Rotary encoder select action')
        if not self.__enable:
            return
        self.__controlledEndList[self.__rights].rotaryEncoderSelect()

    def __rotaryEncoderClockwise(self):
        self.__logger.debug('Rotary encoder clockwise action')
        if not self.__enable:
            return
        self.__controlledEndList[self.__rights].rotaryEncoderClockwise()

    def __rotaryEncoderCounterClockwise(self):
        self.__logger.debug('Rotary encoder counter clockwise action')
        if not self.__enable:
            return
        self.__controlledEndList[self.__rights].rotaryEncoderCounterClockwise()

    def mainLoop(self):
        self.__t.start()
        self.__logger.info("Enter mainloop")
        try:
            while True:
                self.__controlledEndList[self.__rights].onEnter(
                    self.__lastWidget)
                for self.__frame in self.__controlledEndList[self.__rights].mainLoop():
                    if self.__signal:
                        self.__signal = False
                        break
                    while not self.__enable:
                        time.sleep(0.1)
                    self.__frameList.put(self.__frame, True)
        except KeyboardInterrupt:
            self.__logger.info('Stop')
            self.__t.terminate()
            self.__lcd.backlight(False)
            exit(0)
