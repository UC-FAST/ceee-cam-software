import csv
import subprocess
import time
from typing import OrderedDict

import smbus2

from . import configLoader


class MAX17048:
    def __init__(
        self,
        i2cBus=configLoader.ConfigLoader()['sensor']['MAX17048']['bus'],
        addr=0x36
    ):
        self.__i2c = smbus2.SMBus(i2cBus)
        self.__addr = addr
        self.__reg = {
            'VCELL': 0X02,
            'SOC': 0x04,
            'MODE': 0X06,
            'VERSION': 0X08,
            'HIBRT': 0x0A,
            'CONFIG': 0X0C,
            'VALRT': 0X14,
            'CRATE': 0X16,
            'VRESET': 0X18,
            'STATUS': 0X1A,
            'CMD': 0xFE
        }

        # self.__powersave()
        self.__recordEnable = False
        if self.__recordEnable:
            with open('record.csv', 'a', newline='') as f:
                c = csv.DictWriter(f, ['time', 'v'])
                c.writeheader()
        self.__lastBat = 0
        self.__alertThreshold = None

    def getBat(self):
        msb, lsb = tuple(self.__i2c.read_i2c_block_data(
            self.__addr, self.__reg['VCELL'], 2, force=None))
        data = (msb << 8 | lsb) * 0.000078125
        if self.__recordEnable:
            if data != self.__lastBat:
                self.__record(data)
                self.__lastBat = data
        if self.__alertThreshold is not None and data < self.__alertThreshold:
            self.__alertAction()
        return data

    def version(self):
        msb, lsb = tuple(self.__i2c.read_i2c_block_data(
            self.__addr, self.__reg['VERSION'], 2, force=None))
        return msb << 8 | lsb

    def __powersave(self):
        msb, lsb = tuple(self.__i2c.read_i2c_block_data(
            self.__addr, self.__reg['CONFIG'], 2, force=None))
        self.__i2c.write_i2c_block_data(self.__addr, self.__reg['CONFIG'], [
                                        msb, lsb | 128], force=None)

    def setAlart(self, voltage):
        voltage /= 0.02
        lsb = self.__i2c.read_i2c_block_data(
            self.__addr, self.__reg['VALRT'], 2, force=None)[1]
        self.__i2c.write_i2c_block_data(self.__addr, self.__reg['VALRT'], [
                                        int(voltage), lsb], force=None)

    def soc(self):
        msb, lsb = tuple(self.__i2c.read_i2c_block_data(
            self.__addr, self.__reg['SOC'], 2, force=None))
        return (msb << 8 | lsb) * 3.90625e-05

    def __record(self, data):
        with open('record.csv', 'a', newline='') as f:
            c = csv.DictWriter(f, ['time', 'v'])
            c.writerow({'time': time.time(), 'v': data})

    @staticmethod
    def __alertAction():
        subprocess.run(['sudo', 'poweroff'])

    @staticmethod
    def getBatteryPercent(voltage):
        batteryVoltage2Percentage = OrderedDict(
            {
                4.20: 100.0,
                4.19: 99.5,
                4.18: 99.0,
                4.17: 98.0,
                4.16: 97.0,
                4.15: 96.0,
                4.14: 95.0,
                4.13: 94.0,
                4.12: 92.5,
                4.11: 91.0,
                4.10: 89.5,
                4.09: 88.0,
                4.08: 86.5,
                4.07: 85.0,
                4.06: 83.5,
                4.05: 82.0,
                4.04: 80.5,
                4.03: 79.0,
                4.02: 77.5,
                4.01: 76.0,
                4.00: 74.5,
                3.99: 73.0,
                3.98: 71.5,
                3.97: 70.0,
                3.96: 68.5,
                3.95: 67.0,
                3.94: 65.5,
                3.93: 64.0,
                3.92: 62.5,
                3.91: 61.0,
                3.90: 59.5,
                3.89: 58.0,
                3.88: 56.5,
                3.87: 55.0,
                3.86: 53.5,
                3.85: 52.0,
                3.84: 50.5,
                3.83: 49.0,
                3.82: 47.5,
                3.81: 46.0,
                3.80: 44.5,
                3.79: 43.0,
                3.78: 41.5,
                3.77: 40.0,
                3.76: 38.5,
                3.75: 37.0,
                3.74: 35.5,
                3.73: 34.0,
                3.72: 32.5,
                3.71: 31.0,
                3.70: 29.0,
                3.69: 27.0,
                3.68: 25.0,
                3.67: 23.0,
                3.66: 21.0,
                3.65: 19.0,
                3.64: 17.0,
                3.63: 15.0,
                3.62: 13.0,
                3.61: 11.0,
                3.60: 9.0,
                3.59: 7.5,
                3.58: 6.0,
                3.57: 5.0,
                3.56: 4.0,
                3.55: 3.5,
                3.54: 3.0,
                3.53: 2.5,
                3.52: 2.0,
                3.51: 1.5,
                3.50: 1.0,
                3.49: 0.8,
                3.48: 0.6,
                3.47: 0.4,
                3.46: 0.2,
                3.45: 0.1,
                3.44: 0.05,
                3.43: 0.01,
                3.27: 0.00
            }
        )
        for v, p in zip(batteryVoltage2Percentage.keys(), batteryVoltage2Percentage.values()):
            if voltage > v:
                return p


if __name__ == '__main__':
    m = MAX17048()
    print(MAX17048().getBat())
    while True:
        print(m.getBatteryPercent(m.getBat()))
        time.sleep(1)
