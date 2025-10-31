import inspect
import json
import logging
import os
import queue
import time
import typing

import cv2
import numpy

import frameDecorator
from components import MAX17048, picam2, led
from utils import SlidingWindowFilter, Hdr, configLoader
from . import controlledEnd
from utils import Logger, LogMsg


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

    def __init__(self, _id='CameraControlledEnd', verbose_console: int = logging.INFO, tuning_file_path=None):
        controlledEnd.ControlledEnd.__init__(self, _id)
        if tuning_file_path:
            with open(tuning_file_path, 'r') as f:
                tuning = json.load(f)
        else:
            tuning = None
        picam2.Cam.__init__(
            self,
            verbose_console=verbose_console,
            tuning=tuning
        )
        self.__zoom: float = 1
        self.__brightness = 0
        self.__config = configLoader.ConfigLoader('./config.json')
        self.__bar_chart = frameDecorator.BarChart(
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
            font_height=10,
            color=frameDecorator.Colors.gold.value
        )
        self.__busy = frameDecorator.Busy(
            self.__config['screen']['width'],
            self.__config['screen']['height']
        )
        self.__hist = frameDecorator.Hist2()

        self.__show_hist = False
        self.__is_busy = False
        self.__mfassist = False
        self.__is_hdr_processing = False
        self.__decorate_enable = False
        self.__zoom_hold = False
        self.__bright_hold = False
        self.__rotate = 0
        self.__record_timestamp = None
        self.__option: None | typing.Dict = None
        self.__m = MAX17048.MAX17048()
        self.__filter = SlidingWindowFilter(10)
        self.__frame_list = queue.Queue(maxsize=5)

        self.__logger = Logger()

    def __worker2(self):
        if self.metadata:
            return {
                "EPTime {}": self.metadata['ExposureTime'],
                'FocusFoM {}': self.frame_quality,
                'FrameDur {}': self.metadata['FrameDuration'],
                'AnGain {}': round(self.metadata['AnalogueGain'], 2),
                'DigGain {}': round(self.metadata['DigitalGain'], 2),
                'Lux {}': round(self.metadata['Lux'], 2),
                'ClrTemp {}': self.metadata['ColourTemperature'],
                "FPS {}": round(self.frame_per_second, 1),
                "FocusFoM {}": int(self.__filter.calc())
            }

    def __find_option_by_ID(self, target):
        if self.__option is None:
            self.__logger.fatal(
                LogMsg(
                    content='Param self.__option is None',
                    module=self.__module__,
                    filename=os.path.basename(os.path.abspath(__file__)),
                    currentframe=inspect.currentframe()
                )
            )
            raise RuntimeError()
        for key, value in self.__option.items():
            if 'options' in value.keys():
                for j in value['options']:
                    if 'id' in j.keys() and 'value' in j.keys():
                        if j['id'] == target:
                            return j['value']
        raise LookupError(target)

    def up_press_action(self):
        if self.__decorate_enable:
            self.__decorator.previous_page()
            time.sleep(0.3)
        else:
            if self.__is_hdr_processing:
                return
            self.__bright_hold = True
            if self.__brightness + 0.01 > 1:
                self.__brightness = 1
            else:
                self.__brightness += 0.01
            self.__toast.set_text("BRT {}".format(int(self.__brightness * 100)))
            self.brightness(self.__brightness)
            time.sleep(0.05)

    def up_release_action(self):
        self.__bright_hold = False

    def down_press_action(self):
        if self.__decorate_enable:
            self.__decorator.next_page()
            time.sleep(0.3)
        else:
            if self.__is_hdr_processing:
                return
            self.__bright_hold = True
            if self.__brightness - 0.01 < -1:
                self.__brightness = -1
            else:
                self.__brightness -= 0.01
            self.__toast.set_text("BRT {}".format(int(self.__brightness * 100)))
            self.brightness(self.__brightness)
            time.sleep(0.05)

    def down_release_action(self):
        self.__bright_hold = False

    def left_press_action(self):
        if self.__is_hdr_processing:
            return
        self.__zoom_hold = True
        if self.__zoom - 0.05 < 1:
            self.__zoom = 1
        else:
            self.__zoom -= 0.2
        self.__toast.set_text("X {}".format(round(self.__zoom, 1)))
        self.zoom(self.__zoom)
        time.sleep(0.05)

    def left_release_action(self):
        self.__zoom_hold = False

    def right_press_action(self):
        if self.__is_hdr_processing:
            return
        self.__zoom_hold = True
        self.__zoom += 0.2
        self.__toast.set_text("X {}".format(round(self.__zoom, 1)))
        self.zoom(self.__zoom)
        time.sleep(0.05)

    def right_release_action(self):
        self.__zoom_hold = False

    def shutter_press_action(self):
        if self.__record_timestamp is not None:
            self.stop_recording()
            led.off(led.blue)
            self.__record_timestamp = None
        else:
            try:
                width, height = tuple(
                    self.__find_option_by_ID('resolution')['value'])
            except ValueError:
                width, height = 0, 0

            delay = self.__find_option_by_ID('delay')
            for i in range(delay):
                if delay - i <= 3:
                    led.toggle_state(led.green)
                    time.sleep(0.5)
                    led.toggle_state(led.green)
                    time.sleep(0.5)
                else:
                    led.toggle_state(led.green)
                    time.sleep(1)
            self.__is_busy = True
            led.on(led.green)
            self.__toast.set_text("Processing")
            path = os.path.join(
                self.__config['camera']['path'], "{}".format(int(time.time())))
            fmat = self.__find_option_by_ID('pict format')
            self.save_frame(
                filePath=path,
                fmat=fmat,
                width=int(width),
                height=int(height),
                rotate=self.__rotate,
                saveMetadata=self.__find_option_by_ID("save metadata"),
                saveRaw=self.__find_option_by_ID("dng enable")
            )
            if self.__find_option_by_ID('watermark'):
                frame = cv2.imread('{}.{}'.format(path, fmat))
                frameDecorator.WaterMark(
                    int(width), int(height)).decorate(frame)
                cv2.imwrite('{}.{}'.format(path, fmat), frame)

            led.off(led.green)
            self.__is_busy = False

    def shutterLongPressAction(self):
        if self.__is_busy or self.__is_hdr_processing:
            return
        if self.__record_timestamp is None:
            try:
                width, height = tuple(
                    self.__find_option_by_ID('resolution').split('x'))
            except ValueError:
                width, height = 0, 0
            self.start_recording(
                int(width), int(height),
                '{}'.format(
                    os.path.join(
                        self.__config['camera']['video_path'],
                        str(int(time.time())) + '.mp4'
                    )
                )
            )
            led.on(led.blue)
            self.__record_timestamp = time.time()
        else:
            self.stop_recording()
            led.off(led.blue)
            self.__record_timestamp = None

    def square_press_action(self):
        if self.__record_timestamp is None and not self.__is_busy:
            self._irq('MenuControlledEnd')

    def circle_press_action(self):
        self.__decorate_enable = not self.__decorate_enable

    def cross_press_action(self):
        pass

    def __exposeSetting(self):
        if self.__find_option_by_ID('auto expose'):
            self.set_AE_enable(
                True
            )
            self.set_AE_constraint_mode(
                self.__find_option_by_ID('constraint mode')['value']
            )
            self.set_AE_exposureMode(
                self.__find_option_by_ID('exposure mode')['value']
            )
            self.set_AE_metering_mode(
                self.__find_option_by_ID('metering mode')['value']
            )
            self.set_AE_flicker_mode(
                self.__find_option_by_ID('flicker mode')['value']
            )
            self.set_AE_flicker_period(
                self.__find_option_by_ID('flicker period')['value']
            )
        else:
            self.set_AE_enable(
                False
            )

            self.set_manual_exposure(
                self.__find_option_by_ID('exposure time'),
                self.__find_option_by_ID('analogue gain')
            )

    def __AwbSetting(self):
        if self.__find_option_by_ID('awb'):
            self.set_AWB_enable(
                True
            )
            self.set_AWB_mode(
                self.__find_option_by_ID('awb mode')['value']
            )
        else:
            self.set_AWB_enable(
                False
            )
            red, blue = self.__find_option_by_ID(
                'red gain'), self.__find_option_by_ID('blue gain')
            self.set_colour_gains(red, blue)

    def msg_receiver(self, sender, msg):
        self.__option = msg[1]
        self.loadSettings()

    def loadSettings(self):
        self.__exposeSetting()
        self.__AwbSetting()
        self.__mfassist = self.__find_option_by_ID('mf assist')
        self.__show_hist = self.__find_option_by_ID('show hist')

    def center_press_action(self):
        pass

    def rotary_encoder_clockwise(self):
        pass

    def rotary_encoder_counter_clockwise(self):
        pass

    def rotary_encoder_select(self):
        pass
        # self.__main.nextCursor()

    def on_enter(self, lastID):
        if not os.path.exists(self.__config['camera']['path']) or not os.path.isdir(self.__config['camera']['path']):
            os.mkdir(self.__config['camera']['path'])
        self._msg_sender(self._id, 'MenuControlledEnd', self._id)
        self.loadSettings()

    def active(self):
        self.start()

    def inactive(self):
        self.stop()

    def main_loop(self):
        for index, frame in enumerate(self.preview()):
            self.__filter.addData(self.frame_quality)
            self.__bar_chart.add_data(int(self.__filter.calc()))

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

            if self.__decorate_enable and not self.__zoom_hold and self.__record_timestamp is None:
                self.__bar_chart.decorate(frame, rotate=self.__rotate)
                self.__decorator.decorate(frame, rotate=self.__rotate)
            if self.__is_busy:
                self.__busy.decorate(frame, self.__rotate)

            if self.__record_timestamp is not None and not self.__zoom_hold:
                millis = (time.time() - self.__record_timestamp) * 1000
                seconds, milliseconds = divmod(int(millis), 1000)
                minutes, seconds = divmod(int(seconds), 60)
                hours, minutes = divmod(int(minutes), 60)
                self.__toast.set_text(
                    '{}:{}:{}:{}'.format(
                        hours, minutes, seconds, milliseconds
                    )
                )
            if self.__zoom_hold:
                self.__toast.decorate(frame, self.__rotate)
            if self.__bright_hold:
                self.__toast.decorate(frame, self.__rotate)
            if self.__toast.isUpdate:
                self.__toast.decorate(frame, self.__rotate)
            if self.__is_hdr_processing:
                self.__toast.decorate(frame, self.__rotate)
            if self.__show_hist:
                self.__hist.decorate(frame)

            if self.__mfassist and edges.any():
                frame = cv2.addWeighted(frame, 1, colorfulEdges, 1.0, 0)
            yield frame
