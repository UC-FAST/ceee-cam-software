import multiprocessing
import os
import subprocess
import threading
import time
from typing import List

import cv2
import wiringpi

import controlledEnd
import frameDecorator
from components import screen, configLoader
from utils import exceptionRecorder, initialize_logger


class UniversalControl:
    def __init__(self, lcd: screen.Lcd, controlledEndList: List[controlledEnd.ControlledEnd]):
        self.__controlledEndList = controlledEndList
        self.__config = configLoader.ConfigLoader('./config.json')
        self.__logger = initialize_logger(console_level=self.__config['debug_level'])
        self.__enable = True
        self.__rights = 0
        self.__lastWidget = None
        self.__lcd = lcd
        self.__direction = 0
        self.__menuEnable = False
        self.__decorateEnable = False
        self.__zoom = 1
        self.__frame = None
        self.__signal = False

        self.__directionPressActionSheet = (
            self.__upPressAction,
            self.__rightPressAction,
            self.__downPressAction,
            self.__leftPressAction,
        )

        self.__directionReleaseActionSheet = (
            self.__upReleaseAction,
            self.__rightReleaseAction,
            self.__downReleaseAction,
            self.__leftReleaseAction,
        )

        self.__keyState = {
            self.__config['pin']['d1']: 0,
            self.__config['pin']['d2']: 0,
            self.__config['pin']['d3']: 0,
            self.__config['pin']['d4']: 0,
            self.__config['pin']['center']: 0,
            self.__config['pin']['circle']: 0,
            self.__config['pin']['triangle']: 0,
        }

        for i in self.__controlledEndList:
            i.irq(self.__irq)
            i.msgSender(self.__msgSender)

        wiringpi.wiringPiSetup()
        wiringpi.wiringPiISR(self.__config['pin']['d1'], wiringpi.GPIO.INT_EDGE_BOTH, self.__d1Action)
        wiringpi.wiringPiISR(self.__config['pin']['d2'], wiringpi.GPIO.INT_EDGE_BOTH, self.__d2Action)
        wiringpi.wiringPiISR(self.__config['pin']['d3'], wiringpi.GPIO.INT_EDGE_BOTH, self.__d3Action)
        wiringpi.wiringPiISR(self.__config['pin']['d4'], wiringpi.GPIO.INT_EDGE_BOTH, self.__d4Action)
        wiringpi.wiringPiISR(self.__config['pin']['center'], wiringpi.GPIO.INT_EDGE_BOTH, self.__centerAction)
        wiringpi.wiringPiISR(self.__config['pin']['circle'], wiringpi.GPIO.INT_EDGE_BOTH, self.__circleAction)
        wiringpi.wiringPiISR(self.__config['pin']['triangle'], wiringpi.GPIO.INT_EDGE_BOTH,
                             self.__triangleAction)
        wiringpi.wiringPiISR(self.__config['pin']['square'], wiringpi.GPIO.INT_EDGE_RISING, self.__squareAction)
        wiringpi.wiringPiISR(self.__config['pin']['cross'], wiringpi.GPIO.INT_EDGE_RISING, self.__crossAction)

        self.__w = frameDecorator.Warining()
        self.__h = frameDecorator.Hist(
            self.__config['screen']['width'],
            self.__config['screen']['height'],
            fill=0
        )

        self.__frameList = multiprocessing.Queue()
        self.__t = multiprocessing.Process(target=self.showImageInAnotherProcess, args=(self.__frameList,))
        self.__logger.info("UniversalControl initialized")
        # self.__poweroffTime = 5 * 60
        # self.__poweroffTimer = threading.Timer(self.__poweroffTime, self.__powerOff)
        # self.__poweroffTimer.start()

    def __msgReceiver(self, msg):
        if msg == 'restart':
            subprocess.run(['sudo', 'reboot'])

    @staticmethod
    def __powerOff():
        subprocess.run(['sudo', 'poweroff'])

    def __refreshTimer(self):
        return
        if self.__poweroffTimer.is_alive():
            self.__poweroffTimer.cancel()
        self.__poweroffTimer = threading.Timer(self.__poweroffTime, self.__powerOff)
        self.__poweroffTimer.start()

    @exceptionRecorder()
    def __irq(self, _id: str):
        self.__logger.info("Irq to {}".format(_id))
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
            if imgList:
                self.__lcd.showImage(imgList.pop(0))
            else:
                time.sleep(0.01)

    @exceptionRecorder()
    def showImageInAnotherProcess(self, imgList: multiprocessing.Queue):
        while True:
            self.__lcd.showImage(imgList.get(True))

    @exceptionRecorder()
    def __centerAction(self):
        if self.__keyState[self.__config['pin']['center']]:
            self.__keyState[self.__config['pin']['center']] = 0
            self.__centerReleaseAction()
        else:
            self.__keyState[self.__config['pin']['center']] = 1
            self.__centerPressAction()

    def __centerPressAction(self):
        self.__logger.debug("Center press action")
        if not self.__enable:
            return
        self.__refreshTimer()
        self.__controlledEndList[self.__rights].centerPressAction()

    def __centerReleaseAction(self):
        self.__logger.debug("Center release action")
        if not self.__enable:
            return
        self.__refreshTimer()
        self.__controlledEndList[self.__rights].centerReleaseAction()

    @exceptionRecorder()
    def __circleAction(self):
        if self.__keyState[self.__config['pin']['circle']]:
            self.__keyState[self.__config['pin']['circle']] = 0
            self.__circleReleaseAction()
        else:
            self.__keyState[self.__config['pin']['circle']] = 1
            self.__circlePressAction()

    def __circlePressAction(self):
        self.__logger.debug("Circle press action")
        if not self.__enable:
            return
        self.__refreshTimer()
        self.__controlledEndList[self.__rights].circlePressAction()

    def __circleReleaseAction(self):
        self.__logger.debug("Circle release action")
        if not self.__enable:
            return
        self.__refreshTimer()
        self.__controlledEndList[self.__rights].circleReleaseAction()

    @exceptionRecorder()
    def __triangleAction(self):
        if self.__keyState[self.__config['pin']['triangle']]:
            self.__keyState[self.__config['pin']['triangle']] = 0
            self.__triangleReleaseAction()
        else:
            self.__keyState[self.__config['pin']['triangle']] = 1
            self.__trianglePressAction()

    def __trianglePressAction(self):
        self.__logger.debug("Triangle press action")
        if not self.__enable:
            return
        self.__refreshTimer()
        self.__controlledEndList[self.__rights].trianglePressAction()

    def __triangleReleaseAction(self):
        self.__logger.debug("Triangle release action")
        if not self.__enable:
            return
        self.__refreshTimer()
        self.__controlledEndList[self.__rights].triangleReleaseAction()

    @exceptionRecorder()
    def __squareAction(self):
        self.__logger.debug("Square action")
        if not self.__enable:
            return
        self.__refreshTimer()
        t = 0
        while wiringpi.digitalRead(self.__config['pin']['square']) and t < 1:
            t += 0.01
            time.sleep(0.01)
        if t < 0.09:
            return
        self.__refreshTimer()
        if t >= 1:
            filename = os.path.join(self.__config['screenshot_path'], 'Screenshot{}.png'.format(int(time.time())))
            path = os.path.split(filename)[0]
            if not os.path.exists(path) or not os.path.isdir(path):
                os.makedirs(path)
            self.__logger.info("Screenshot {}".format(filename))
            cv2.imwrite(
                filename,
                self.__frame,
            )
        else:
            self.__logger.info('Rotate')
            self.__rotate()
            for i in self.__controlledEndList:
                i.direction(self.__direction)

        while wiringpi.digitalRead(self.__config['pin']['square']):
            time.sleep(0.02)

    @exceptionRecorder()
    def __crossAction(self):
        self.__logger.debug('Cross action')
        t = 0
        while wiringpi.digitalRead(self.__config['pin']['cross']) and t <= 2:
            t += 0.01
            time.sleep(0.01)
        if t < 0.09:
            return
        self.__refreshTimer()
        if t >= 2:
            # self.__frameList.put()
            self.__logger.info('Poweroff')
            subprocess.run(['sudo', 'poweroff'])
        else:
            self.__logger.info('Toggle enable')
            self.__enable = not self.__enable
            self.__lcd.backlight(self.__enable)

    @exceptionRecorder()
    def __d1Action(self):
        if self.__keyState[self.__config['pin']['d1']]:
            self.__keyState[self.__config['pin']['d1']] = 0
            self.__d1ReleaseAction()
        else:
            self.__keyState[self.__config['pin']['d1']] = 1
            self.__d1PressAction()

    def __d1PressAction(self):
        if not self.__enable:
            return
        self.__refreshTimer()
        while wiringpi.digitalRead(self.__config['pin']['d1']):
            self.__directionPressActionSheet[(self.__direction // 90) * 3 % 4]()

    def __d1ReleaseAction(self):
        if not self.__enable:
            return
        self.__refreshTimer()
        self.__directionReleaseActionSheet[(self.__direction // 90) * 3 % 4]()

    @exceptionRecorder()
    def __d2Action(self):
        if self.__keyState[self.__config['pin']['d2']]:
            self.__keyState[self.__config['pin']['d2']] = 0
            self.__d2ReleaseAction()
        else:
            self.__keyState[self.__config['pin']['d2']] = 1
            self.__d2PressAction()

    def __d2PressAction(self):
        if not self.__enable:
            return
        self.__refreshTimer()
        while wiringpi.digitalRead(self.__config['pin']['d2']):
            self.__directionPressActionSheet[((self.__direction // 90) * 3 + 1) % 4]()

    def __d2ReleaseAction(self):
        if not self.__enable:
            return
        self.__refreshTimer()
        self.__directionReleaseActionSheet[((self.__direction // 90) * 3 + 1) % 4]()

    @exceptionRecorder()
    def __d3Action(self):
        if self.__keyState[self.__config['pin']['d3']]:
            self.__keyState[self.__config['pin']['d3']] = 0
            self.__d3ReleaseAction()
        else:
            self.__keyState[self.__config['pin']['d3']] = 1
            self.__d3PressAction()

    def __d3PressAction(self):
        if not self.__enable:
            return
        self.__refreshTimer()
        while wiringpi.digitalRead(self.__config['pin']['d3']):
            self.__directionPressActionSheet[((self.__direction // 90) * 3 + 2) % 4]()

    def __d3ReleaseAction(self):
        if not self.__enable:
            return
        self.__refreshTimer()
        self.__directionReleaseActionSheet[((self.__direction // 90) * 3 + 2) % 4]()

    @exceptionRecorder()
    def __d4Action(self):
        if self.__keyState[self.__config['pin']['d4']]:
            self.__keyState[self.__config['pin']['d4']] = 0
            self.__d4ReleaseAction()
        else:
            self.__keyState[self.__config['pin']['d4']] = 1
            self.__d4PressAction()

    def __d4PressAction(self):
        if not self.__enable:
            return
        self.__refreshTimer()
        while wiringpi.digitalRead(self.__config['pin']['d4']):
            self.__directionPressActionSheet[((self.__direction // 90) * 3 + 3) % 4]()

    def __d4ReleaseAction(self):
        if not self.__enable:
            return
        self.__refreshTimer()
        self.__directionReleaseActionSheet[((self.__direction // 90) * 3 + 3) % 4]()

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

    def __rotate(self):
        if self.__direction == 270:
            self.__direction = 0
        else:
            self.__direction += 90
        self.__logger.debug('Direction: {}'.format(self.__direction))

    def mainLoop(self):
        self.__t.start()
        self.__logger.info("Enter mainloop")
        try:
            while True:
                self.__controlledEndList[self.__rights].onEnter(self.__lastWidget)
                for self.__frame in self.__controlledEndList[self.__rights].mainLoop():
                    if self.__signal:
                        self.__signal = False
                        break
                    while not self.__enable:
                        time.sleep(0.1)
                    self.__frameList.put(self.__frame, True)
        except KeyboardInterrupt:
            self.__logger.info('Stop')
            self.__lcd.backlight(False)
            self.__logger.info('Stop')
            exit(0)
        '''except Exception as e:
            self.__frameList.put(
                self.__w.decorate(
                    "{} {}".format(repr(e).split('(')[0], str(e)),
                    self.__direction
                ),
                True
            )
            time.sleep(3)'''
