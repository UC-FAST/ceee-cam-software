import json
import os
import queue
import re
import subprocess
import time
import typing

import cv2
import psutil
import wiringpi

import frameDecorator
from components import max17048, picam2, led, configLoader
from utils import SlidingWindowFilter, Hdr
from . import controlledEnd


class CameraControlledEnd(controlledEnd.ControlledEnd, picam2.Cam):
    def __init__(self, _id='CameraControlledEnd', verbose_console=None, tuningFilePath=None):
        controlledEnd.ControlledEnd.__init__(self, _id)
        if tuningFilePath:
            with open(tuningFilePath, 'r') as f:
                tuning = json.load(f)
        else:
            tuning = None
        picam2.Cam.__init__(self, verbose_console=verbose_console, tuning=tuning)
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
            [self.__worker2, self.__worker1, self.__worker3],
            height=self.__config['screen']['height'],
            padding=(10, 20, 0, 0),
            fontHeight=10,
            color=frameDecorator.Colors.gold.value
        )
        self.__busy = frameDecorator.Busy(
            self.__config['screen']['width'],
            self.__config['screen']['height']
        )
        self.__isBusy = False
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

    def __worker3(self):
        result = subprocess.run(["ifconfig"], capture_output=True).stdout.decode()
        pattern = 'wlan0:.*inet (.*)  netmask'
        try:
            target = re.findall(pattern=pattern, string=result, flags=re.DOTALL)[0]
        except IndexError:
            target = 'NULL'
        return {
            'IP {}': target,
        }

    def __worker2(self):
        return {
            "EPTime {}": self.metadata['ExposureTime'],
            'FocusFoM {}': self.frameQuality,
            'FrameDur {}': self.metadata['FrameDuration'],
            'AnGain {}': round(self.metadata['AnalogueGain'], 2),
            'DigGain {}': round(self.metadata['DigitalGain'], 2),
            'Lux {}': round(self.metadata['Lux'], 2),
            'ClrTemp {}': self.metadata['ColourTemperature'],
        }

    def __worker1(self):
        return {
            # "BAT {}v": round(self.__m.getBat(), 2),
            "BAT {}v": round(self.__m.getBat(), 2),
            "FPS {}": round(self.framePerSecond, 1),
            "MEM {}%": round((psutil.virtual_memory().used / psutil.virtual_memory().total) * 100, 2),
            "TEMP {}": psutil.sensors_temperatures()['cpu_thermal'][0].current,
            "DISK {}%": psutil.disk_usage('/').percent,
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
            self.__zoom -= 0.05
        self.__toast.setText("X {}".format(round(self.__zoom, 1)))
        self.zoom(self.__zoom)
        time.sleep(0.05)

    def leftReleaseAction(self):
        self.__zoomHold = False

    def rightPressAction(self):
        if self.__isHdrProcessing:
            return
        self.__zoomHold = True
        self.__zoom += 0.05
        self.__toast.setText("X {}".format(round(self.__zoom, 1)))
        self.zoom(self.__zoom)
        time.sleep(0.05)

    def rightReleaseAction(self):
        self.__zoomHold = False

    def circlePressAction(self):
        if self.__recordTimestamp is not None:
            self.stopRecording()
            led.off(led.blue)
            self.__recordTimestamp = None
        else:
            if self.__findOptionByID('hdr enable'):
                try:
                    width, height = tuple(self.__findOptionByID('resolution').split('x'))
                except ValueError:
                    width, height = 0, 0
                self.__isBusy = True
                self.__isHdrProcessing = True
                led.on(led.green)
                lower, upper, stackNum = self.__findOptionByID('lower'), self.__findOptionByID(
                    'upper'), self.__findOptionByID('stack num')
                step = (upper - lower) // (stackNum - 1)
                exposureTimeList, frameList = list(), list()
                for index, i in enumerate(range(lower, upper + step, step), start=1):
                    self.__toast.setText("{}/{}".format(index, stackNum))
                    exposeTime, frame = self.exposureCapture(i, int(width), int(height))
                    exposureTimeList.append(exposeTime / 1e6)
                    frameList.append(frame)

                self.__toast.setText("Processing")
                algorithm = self.__findOptionByID('algorithm')
                hdr = Hdr(exposureTimeList, frameList, self.__findOptionByID('correction'))
                if algorithm == 'Drago':
                    hdrFrame = hdr.tonemapDrago()
                elif algorithm == 'Reinhard':
                    hdrFrame = hdr.tonemapReinhard()
                elif algorithm == 'Mantiuk':
                    hdrFrame = hdr.tonemapMantiuk()
                elif algorithm == 'EP Fusion':
                    hdrFrame = hdr.exposureFusion()
                else:
                    raise LookupError(algorithm)
                if self.__findOptionByID('watermark'):
                    frameDecorator.WaterMark(int(width), int(height)).decorate(hdrFrame)
                cv2.imwrite(
                    os.path.join(
                        self.__config['camera']['path'],
                        "{}{}".format(
                            int(time.time()),
                            '{}'.format(self.__findOptionByID('pict format'))
                            if self.__findOptionByID('pict format').startswith('.')
                            else '.{}'.format(self.__findOptionByID('pict format'))
                        )
                    ),
                    hdrFrame
                )
                led.off(led.green)
                self.__isHdrProcessing = False
                self.__isBusy = False
                self.__exposeSetting()
            else:
                try:
                    width, height = tuple(self.__findOptionByID('resolution').split('x'))
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
                path = os.path.join(self.__config['camera']['path'], "{}".format(int(time.time())))
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
                    frameDecorator.WaterMark(int(width), int(height)).decorate(frame)
                    cv2.imwrite('{}.{}'.format(path, fmat), frame)

                led.off(led.green)
                self.__isBusy = False

    def circleLongPressAction(self):
        if self.__isBusy or self.__isHdrProcessing:
            return
        if self.__recordTimestamp is None:
            try:
                width, height = tuple(self.__findOptionByID('resolution').split('x'))
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

    def trianglePressAction(self):
        if self.__decorateEnable:
            self.__decorateEnable = False
        elif not self.__decorateEnable and self.__recordTimestamp is None and not self.__isBusy:
            self._irq('MenuControlledEnd')

    def triangleLongPressAction(self):
        self.__decorateEnable = not self.__decorateEnable

    def __exposeSetting(self):
        if self.__findOptionByID('auto expose'):
            self.setAeExposureMode(self.__findOptionByID('exposure mode')[1])
            self.setAeMeteringMode(self.__findOptionByID('metering mode')[1])
        else:
            if self.__findOptionByID('manual expose'):
                exposure = self.__findOptionByID('exposure time')
            else:
                exposure = 0
            if self.__findOptionByID('manual analog'):
                analog = self.__findOptionByID('analogue gain')
            else:
                analog = 0
            self.setExposure(exposure, analog)

    def __colourGainsSetting(self):
        if not self.__findOptionByID('awb'):
            red, blue = self.__findOptionByID('red gain'), self.__findOptionByID('blue gain')
            self.setColourGains(red, blue)

    def msgReceiver(self, sender, msg):
        if sender == 'MenuControlledEnd':
            self.__option = msg[1]
            self.__exposeSetting()
            self.__colourGainsSetting()
            if self.__findOptionByID('awb'):
                self.setAwbMode(self.__findOptionByID('awb mode')[1])

    def centerPressAction(self):
        t = 0
        while wiringpi.digitalRead(self.__config['pin']['center']) and t < 1:
            t += 0.01
            time.sleep(0.01)
        if t < 0.09:
            return
        self.__zoom = 1
        self.__brightness = 0
        self.zoom(self.__zoom)
        self.brightness(self.__brightness)

    def direction(self, direction):
        self.__rotate = direction

    def onEnter(self, lastID):
        if not os.path.exists(self.__config['camera']['path']) or not os.path.isdir(self.__config['camera']['path']):
            os.mkdir(self.__config['camera']['path'])
        self._msgSender(self._id, 'MenuControlledEnd', self._id)

    def active(self):
        self.start()

    def inactive(self):
        self.stop()

    def mainLoop(self):
        for index, frame in enumerate(self.preview()):
            self.__filter.addData(self.frameQuality)
            self.__barChart.addData(int(self.__filter.calc()))
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
                self.__toast.setText('{}:{}:{}:{}'.format(hours, minutes, seconds, milliseconds))
            if self.__zoomHold:
                self.__toast.decorate(frame, self.__rotate)
            if self.__brightHold:
                self.__toast.decorate(frame, self.__rotate)
            if self.__toast.isUpdate:
                self.__toast.decorate(frame, self.__rotate)
            if self.__isHdrProcessing:
                self.__toast.decorate(frame, self.__rotate)

            yield frame
