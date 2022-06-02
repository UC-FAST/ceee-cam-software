import csv
import subprocess
import time

import smbus2


class Max17048:
    def __init__(self):
        self.__i2c = smbus2.SMBus(1)
        self.__MAX17048_ADDR = 0x36
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

        self.__powersave()
        self.__recordEnable = False
        if self.__recordEnable:
            with open('record.csv', 'a', newline='') as f:
                c = csv.DictWriter(f, ['time', 'v'])
                c.writeheader()
        self.__lastBat = 0
        self.__alertThreshold = None

    def getBat(self):
        msb, lsb = tuple(self.__i2c.read_i2c_block_data(self.__MAX17048_ADDR, self.__reg['VCELL'], 2, force=None))
        data = (msb << 8 | lsb) * 0.000078125
        if self.__recordEnable:
            if data != self.__lastBat:
                self.__record(data)
                self.__lastBat = data
        if self.__alertThreshold is not None and data < self.__alertThreshold:
            self.__alertAction()
        return data

    def version(self):
        msb, lsb = tuple(self.__i2c.read_i2c_block_data(self.__MAX17048_ADDR, self.__reg['VERSION'], 2, force=None))
        return msb << 8 | lsb

    def __powersave(self):
        msb, lsb = tuple(self.__i2c.read_i2c_block_data(self.__MAX17048_ADDR, self.__reg['CONFIG'], 2, force=None))
        self.__i2c.write_i2c_block_data(self.__MAX17048_ADDR, self.__reg['CONFIG'], [msb, lsb | 128], force=None)

    def setAlart(self, voltage):
        voltage /= 0.02
        lsb = self.__i2c.read_i2c_block_data(self.__MAX17048_ADDR, self.__reg['VALRT'], 2, force=None)[1]
        self.__i2c.write_i2c_block_data(self.__MAX17048_ADDR, self.__reg['VALRT'], [int(voltage), lsb], force=None)

    def soc(self):
        msb, lsb = tuple(self.__i2c.read_i2c_block_data(self.__MAX17048_ADDR, self.__reg['SOC'], 2, force=None))
        return (msb << 8 | lsb) * 3.90625e-05

    def __record(self, data):
        with open('record.csv', 'a', newline='') as f:
            c = csv.DictWriter(f, ['time', 'v'])
            c.writerow({'time': time.time(), 'v': data})

    @staticmethod
    def __alertAction():
        subprocess.run(['sudo', 'poweroff'])


if __name__ == '__main__':
    m = Max17048()
    print(Max17048().getBat())
    while True:
        print(m.soc())
        time.sleep(1)
