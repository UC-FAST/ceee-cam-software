import abc
import re
import subprocess

import numpy
import psutil

from components import max17048
import frameDecorator
from utils.slidingWindowFilter import SlidingWindowFilter


class SystemMonitor(abc.ABC):
    def __init__(self, _id='SystemMonitor'):
        self._id = _id
        self._irq = None
        self._msgSender = None
        self.__decorator = frameDecorator.SimpleText(
            [
                self.__page1
                ],
            height=240,
            padding=(10, 20, 0, 0),
            fontHeight=10,
            color=frameDecorator.Colors.gold.value
        )
        self.__m = max17048.Max17048()



    """---Multi Direction Button Start---"""


    def __page1(self):
        """
        Gathers and returns system monitoring information including CPU usage, memory usage, disk usage, battery status, CPU temperature, and the IP address of the 'wlan0' network interface.

        Returns:
            dict: A dictionary containing the following keys and their corresponding values:
                - "CPU {}%": Current CPU usage percentage.
                - "MEM {}%": Current memory usage percentage.
                - "DISK {}%": Current disk usage percentage for the root filesystem.
                - "BAT {}v {}%": Tuple containing current battery voltage and battery percentage.
                - "TEMP {} C": Current CPU temperature in Celsius.
                - "IP {}": IP address of the 'wlan0' interface, or 'NULL' if not found.
        """
        result = subprocess.run(
            ["ifconfig"], capture_output=True).stdout.decode()
        pattern = 'wlan0:.*inet (.*)  netmask'
        try:
            target = re.findall(
                pattern=pattern, string=result, flags=re.DOTALL)[0]
        except IndexError:
            target = 'NULL'


        return {
            "CPU {}%": round(psutil.cpu_percent(interval=0.3), 2),
            "MEM {}%": round((psutil.virtual_memory().used / psutil.virtual_memory().total) * 100, 2),
            "DISK {}%": psutil.disk_usage('/').percent,
            "BAT {}v {}%":( round(self.__m.getBat(), 2),self.__m.getBatteryPercent(self.__m.getBat())),
            "TEMP {} C": psutil.sensors_temperatures()['cpu_thermal'][0].current,
            'IP {}': target,
        }

    def centerPressAction(self):
        pass

    def centerReleaseAction(self):
        pass

    def upPressAction(self):
        self.__decorator.previousPage()

    def upReleaseAction(self):
        pass

    def downPressAction(self):
        self.__decorator.nextPage()

    def downReleaseAction(self):
        pass

    def leftPressAction(self):
        self.__decorator.previousPage()

    def leftReleaseAction(self):
        pass

    def rightPressAction(self):
        self.__decorator.nextPage()

    def rightReleaseAction(self):
        pass

    """---Multi Direction Button End---"""

    """---Multi Function Button Start---"""

    def circlePressAction(self):
        pass

    def squarePressAction(self):
        pass

    def crossPressAction(self):
        self._irq("CameraControlledEnd")

    def shutterPressAction(self):
        pass

    """---Multi Function Button End---"""

    """---Rotary Encoder Start---"""

    def rotaryEncoderClockwise(self):
        self.__decorator.previousPage()

    def rotaryEncoderCounterClockwise(self):
        self.__decorator.nextPage()

    def rotaryEncoderSelect(self):
        pass

    """---Rotary Encoder End---"""

    """---Communication Function Start---"""

    def msgReceiver(self, sender, msg):
        pass

    def msgSender(self, func):
        self._msgSender = func

    """---Communication Function End---"""

    def irq(self, func):
        self._irq = func

    def mainLoop(self):
        frame=numpy.zeros((240, 320, 3), dtype=numpy.uint8)
        self.__decorator.decorate(frame)
        yield frame

    def onExit(self):
        pass

    def onEnter(self, lastID):
        pass

    def active(self):
        pass

    def inactive(self):
        pass

    @property
    def id(self):
        return self._id
