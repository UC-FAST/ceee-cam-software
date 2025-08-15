import json
import os
import queue
import re
import subprocess
import time
import typing

import cv2
import numpy
import psutil

import frameDecorator
from components import max17048, picam2, led, configLoader
from utils import SlidingWindowFilter, Hdr
from . import controlledEnd


class CameraControlledEnd(controlledEnd.ControlledEnd, picam2.Cam):
    """
    CameraControlledEnd is a camera control class that extends ControlledEnd and picam2.Cam to provide advanced camera operations, UI interactions, and hardware integration for a controlled camera system.
    Attributes:
        __zoom (float): Current zoom level.
        __brightness (float): Current brightness adjustment.
        __config (ConfigLoader): Configuration loader for system settings.
        __barChart (BarChart): Frame decorator for displaying bar charts.
        __toast (Toast): Frame decorator for displaying toast messages.
        __decorator (SimpleText): Frame decorator for displaying text overlays.
        __busy (Busy): Frame decorator for busy/processing indication.
        __hist (Hist2): Frame decorator for histogram display.
        __showHist (bool): Flag to show/hide histogram.
        __isBusy (bool): Indicates if the camera is busy processing.
        __mfassist (bool): Manual focus assist flag.
        __isHdrProcessing (bool): HDR processing flag.
        __decorateEnable (bool): Enables/disables UI decorations.
        __zoomHold (bool): Indicates if zoom is being adjusted.
        __brightHold (bool): Indicates if brightness is being adjusted.
        __rotate (int): Frame rotation angle.
        __recordTimestamp (float or None): Timestamp for video recording.
        __option (dict): Camera options/settings.
        __m (Max17048): Battery monitor instance.
        __filter (SlidingWindowFilter): Filter for smoothing frame quality.
        __frameList (queue.Queue): Queue for frame buffering.
    Methods:
        __init__(_id, verbose_console, tuningFilePath): Initializes the camera control end.
        __worker2(): Returns a dictionary of current camera status metrics.
        __findOptionByID(target): Finds and returns the value of a camera option by its ID.
        upPressAction(): Handles the action when the up button is pressed.
        upReleaseAction(): Handles the action when the up button is released.
        downPressAction(): Handles the action when the down button is pressed.
        downReleaseAction(): Handles the action when the down button is released.
        leftPressAction(): Handles the action when the left button is pressed (zoom out).
        leftReleaseAction(): Handles the action when the left button is released.
        rightPressAction(): Handles the action when the right button is pressed (zoom in).
        rightReleaseAction(): Handles the action when the right button is released.
        shutterPressAction(): Handles the action when the shutter button is pressed (capture photo).
        shutterLongPressAction(): Handles the action when the shutter button is long-pressed (start/stop video recording).
        squarePressAction(): Handles the action when the square button is pressed (menu).
        circlePressAction(): Toggles UI decorations.
        crossPressAction(): Placeholder for cross button action.
        __exposeSetting(): Applies exposure settings based on current options.
        __AwbSetting(): Applies auto white balance settings based on current options.
        msgReceiver(sender, msg): Receives and processes messages for updating options.
        loadSettings(): Loads and applies camera settings from options.
        centerPressAction(): Placeholder for center button action.
        rotaryEncoderClockwise(): Placeholder for rotary encoder clockwise action.
        rotaryEncoderCounterClockwise(): Placeholder for rotary encoder counter-clockwise action.
        rotaryEncoderSelect(): Placeholder for rotary encoder select action.
        onEnter(lastID): Handles actions when entering this control end.
        active(): Activates the camera preview.
        inactive(): Deactivates the camera preview.
        mainLoop(): Main loop for processing and yielding camera frames with decorations and overlays.
    Usage:
        This class is intended to be used as part of a camera control system, providing both hardware and UI interaction logic for camera operation, including photo capture, video recording, and real-time frame processing.
    """
    def __init__(self, _id='CameraControlledEnd', verbose_console=None, tuningFilePath=None):
        controlledEnd.ControlledEnd.__init__(self, _id)
        if tuningFilePath:
            with open(tuningFilePath, 'r') as f:
                tuning = json.load(f)
        else:
            tuning = None
        picam2.Cam.__init__(
            self, verbose_console=verbose_console, tuning=tuning)
        self.__zoom = 1
        self.__brightness = 0
        self.__config = configLoader.ConfigLoader('./config.json')
        self.__barChart = frameDecorator.BarChart(
            self.__config['screen']['width'],
            self.__config['screen']['height'],
            fill=True,
            alpha=0.7
        )
        self.__toast = frameDecorator.Toast()
        self.__decorator = frameDecorator.SimpleText(
            [self.__worker2, ],
            height=self.__config['screen']['height'],
            padding=(10, 20, 0, 0),
            fontHeight=10,
            color=frameDecorator.Colors.gold.value
        )
        self.__busy = frameDecorator.Busy(
            self.__config['screen']['width'],
            self.__config['screen']['height']
        )
        self.__hist = frameDecorator.Hist2()

        self.__showHist = False
        self.__isBusy = False
        self.__mfassist = False
        self.__isHdrProcessing = False
        self.__decorateEnable = False
        self.__zoomHold = False
        self.__brightHold = False
        self.__rotate = 0
        self.__recordTimestamp = None
        self.__option: typing.Dict[typing.Dict] = None
        self.__m = max17048.Max17048()
        self.__filter = SlidingWindowFilter(10)
        self.__frameList = queue.Queue(maxsize=5)

        

    def __worker2(self):
        return {
            "EPTime {}": self.metadata['ExposureTime'],
            'FocusFoM {}': self.frameQuality,
            'FrameDur {}': self.metadata['FrameDuration'],
            'AnGain {}': round(self.metadata['AnalogueGain'], 2),
            'DigGain {}': round(self.metadata['DigitalGain'], 2),
            'Lux {}': round(self.metadata['Lux'], 2),
            'ClrTemp {}': self.metadata['ColourTemperature'],
            "FPS {}": round(self.framePerSecond, 1),
            "FocusFoM {}": int(self.__filter.calc())
        }

    def __findOptionByID(self, target):
        for key, value in self.__option.items():
            if 'options' in value.keys():
                for j in value['options']:
                    if 'id' in j.keys() and 'value' in j.keys():
                        if j['id'] == target:
                            return j['value']
        raise LookupError(target)

    def upPressAction(self):
        if self.__decorateEnable:
            self.__decorator.previousPage()
            time.sleep(0.3)
        else:
            if self.__isHdrProcessing:
                return
            self.__brightHold = True
            if self.__brightness + 0.01 > 1:
                self.__brightness = 1
            else:
                self.__brightness += 0.01
            self.__toast.setText("BRT {}".format(int(self.__brightness * 100)))
            self.brightness(self.__brightness)
            time.sleep(0.05)

    def upReleaseAction(self):
        self.__brightHold = False

    def downPressAction(self):
        if self.__decorateEnable:
            self.__decorator.nextPage()
            time.sleep(0.3)
        else:
            if self.__isHdrProcessing:
                return
            self.__brightHold = True
            if self.__brightness - 0.01 < -1:
                self.__brightness = -1
            else:
                self.__brightness -= 0.01
            self.__toast.setText("BRT {}".format(int(self.__brightness * 100)))
            self.brightness(self.__brightness)
            time.sleep(0.05)

    def downReleaseAction(self):
        self.__brightHold = False

    def leftPressAction(self):
        if self.__isHdrProcessing:
            return
        self.__zoomHold = True
        if self.__zoom - 0.05 < 1:
            self.__zoom = 1
        else:
            self.__zoom -= 0.2
        self.__toast.setText("X {}".format(round(self.__zoom, 1)))
        self.zoom(self.__zoom)
        time.sleep(0.05)

    def leftReleaseAction(self):
        self.__zoomHold = False

    def rightPressAction(self):
        if self.__isHdrProcessing:
            return
        self.__zoomHold = True
        self.__zoom += 0.2
        self.__toast.setText("X {}".format(round(self.__zoom, 1)))
        self.zoom(self.__zoom)
        time.sleep(0.05)

    def rightReleaseAction(self):
        self.__zoomHold = False

    def shutterPressAction(self):
        if self.__recordTimestamp is not None:
            self.stopRecording()
            led.off(led.blue)
            self.__recordTimestamp = None
        else:
            try:
                width, height = tuple(
                    self.__findOptionByID('resolution')['value'])
            except ValueError:
                width, height = 0, 0

            delay = self.__findOptionByID('delay')
            for i in range(delay):
                if delay - i <= 3:
                    led.toggleState(led.green)
                    time.sleep(0.5)
                    led.toggleState(led.green)
                    time.sleep(0.5)
                else:
                    led.toggleState(led.green)
                    time.sleep(1)
            self.__isBusy = True
            led.on(led.green)
            self.__toast.setText("Processing")
            path = os.path.join(
                self.__config['camera']['path'], "{}".format(int(time.time())))
            fmat = self.__findOptionByID('pict format')
            self.saveFrame(
                filePath=path,
                fmat=fmat,
                width=int(width),
                height=int(height),
                rotate=self.__rotate,
                saveMetadata=self.__findOptionByID("save metadata"),
                saveRaw=self.__findOptionByID("dng enable")
            )
            if self.__findOptionByID('watermark'):
                frame = cv2.imread('{}.{}'.format(path, fmat))
                frameDecorator.WaterMark(
                    int(width), int(height)).decorate(frame)
                cv2.imwrite('{}.{}'.format(path, fmat), frame)

            led.off(led.green)
            self.__isBusy = False

    def shutterLongPressAction(self):
        if self.__isBusy or self.__isHdrProcessing:
            return
        if self.__recordTimestamp is None:
            try:
                width, height = tuple(
                    self.__findOptionByID('resolution').split('x'))
            except ValueError:
                width, height = 0, 0
            self.startRecording(
                int(width), int(height),
                '{}'.format(
                    os.path.join(
                        self.__config['camera']['video_path'],
                        str(int(time.time())) + '.mp4'
                    )
                )
            )
            led.on(led.blue)
            self.__recordTimestamp = time.time()
        else:
            self.stopRecording()
            led.off(led.blue)
            self.__recordTimestamp = None

    def squarePressAction(self):
        if self.__recordTimestamp is None and not self.__isBusy:
            self._irq('MenuControlledEnd')

    def circlePressAction(self):
        self.__decorateEnable = not self.__decorateEnable

    def crossPressAction(self):
        pass

    def __exposeSetting(self):
        if self.__findOptionByID('auto expose'):
            self.setAeEnable(
                True
            )
            self.setAeConstraintMode(
                self.__findOptionByID('constraint mode')['value']
            )
            self.setAeExposureMode(
                self.__findOptionByID('exposure mode')['value']
            )
            self.setAeMeteringMode(
                self.__findOptionByID('metering mode')['value']
            )
            self.setAeFlickerMode(
                self.__findOptionByID('flicker mode')['value']
            )
            self.setAeFlickerPeriod(
                self.__findOptionByID('flicker period')['value']
            )
        else:
            self.setAeEnable(
                False
            )

            self.setManualExposure(
                self.__findOptionByID('exposure time'),
                self.__findOptionByID('analogue gain')
            )

    def __AwbSetting(self):
        if self.__findOptionByID('awb'):
            self.setAwbEnable(
                True
            )
            self.setAwbMode(
                self.__findOptionByID('awb mode')['value']
            )
        else:
            self.setAwbEnable(
                False
            )
            red, blue = self.__findOptionByID(
                'red gain'), self.__findOptionByID('blue gain')
            self.setColourGains(red, blue)

    def msgReceiver(self, sender, msg):
        self.__option = msg[1]
        self.loadSettings()

    def loadSettings(self):
        self.__exposeSetting()
        self.__AwbSetting()
        self.__mfassist = self.__findOptionByID('mf assist')
        self.__showHist = self.__findOptionByID('show hist')

    def centerPressAction(self):
        pass

    def rotaryEncoderClockwise(self):
        pass

    def rotaryEncoderCounterClockwise(self):
        pass

    def rotaryEncoderSelect(self):
        pass
        # self.__main.nextCursor()

    def onEnter(self, lastID):
        if not os.path.exists(self.__config['camera']['path']) or not os.path.isdir(self.__config['camera']['path']):
            os.mkdir(self.__config['camera']['path'])
        self._msgSender(self._id, 'MenuControlledEnd', self._id)
        self.loadSettings()

    def active(self):
        self.start()

    def inactive(self):
        self.stop()

    def mainLoop(self):
        for index, frame in enumerate(self.preview()):
            self.__filter.addData(self.frameQuality)
            self.__barChart.addData(int(self.__filter.calc()))

            if self.__mfassist:
                gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
                blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                edges = cv2.Canny(
                    blurred,
                    threshold1=70,
                    threshold2=400
                )
                if edges.any():
                    colorfulEdges = numpy.zeros(
                        (edges.shape[0], edges.shape[1], 3), dtype=numpy.uint8)

                    if index % 3 == 0:
                        colorfulEdges[edges != 0] = (0, 0, 255)
                    elif index % 3 == 1:
                        colorfulEdges[edges != 0] = (255, 0, 0)
                    else:
                        colorfulEdges[edges != 0] = (0, 255, 0)

            if self.__decorateEnable and not self.__zoomHold and self.__recordTimestamp is None:
                self.__barChart.decorate(frame, rotate=self.__rotate)
                self.__decorator.decorate(frame, rotate=self.__rotate)
            if self.__isBusy:
                self.__busy.decorate(frame, self.__rotate)

            if self.__recordTimestamp is not None and not self.__zoomHold:
                millis = (time.time() - self.__recordTimestamp) * 1000
                seconds, milliseconds = divmod(int(millis), 1000)
                minutes, seconds = divmod(int(seconds), 60)
                hours, minutes = divmod(int(minutes), 60)
                self.__toast.setText(
                    '{}:{}:{}:{}'.format(
                        hours, minutes, seconds, milliseconds
                    )
                )
            if self.__zoomHold:
                self.__toast.decorate(frame, self.__rotate)
            if self.__brightHold:
                self.__toast.decorate(frame, self.__rotate)
            if self.__toast.isUpdate:
                self.__toast.decorate(frame, self.__rotate)
            if self.__isHdrProcessing:
                self.__toast.decorate(frame, self.__rotate)
            if self.__showHist:
                self.__hist.decorate(frame)

            if self.__mfassist and edges.any():
                frame = cv2.addWeighted(frame, 1, colorfulEdges, 1.0, 0)

            yield frame
