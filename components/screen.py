from enum import Enum
from time import sleep

import cv2
import numpy as np
import spidev
import wiringpi

from .configLoader import ConfigLoader


class ScanDir(Enum):
    L2R_U2D = 1
    L2R_D2U = 2
    R2L_U2D = 3
    R2L_D2U = 4
    U2D_L2R = 5
    U2D_R2L = 6
    D2U_L2R = 7
    D2U_R2L = 8


class Lcd:
    def __init__(self, width=128, height=128, scanDir=ScanDir.R2L_D2U):
        self.__config = ConfigLoader('./config.json')
        self.width = width
        self.height = height
        self.scanDir = scanDir
        self.LCD_X_Adjust = 132
        self.LCD_Y_Adjust = 162
        self.__spi = spidev.SpiDev(0, 0)
        self.__spi.max_speed_hz = 17500000
        self.__spi.mode = 0b00

        wiringpi.wiringPiSetup()
        wiringpi.pinMode(self.__config['pin']['rst'], 1)
        wiringpi.pinMode(self.__config['pin']['dc'], 1)
        wiringpi.pinMode(self.__config['pin']['bl'], 1)

        self.init()
        self.clear()

    def backlight(self, state: bool):
        wiringpi.digitalWrite(self.__config['pin']['bl'], not state)

    def reset(self):
        wiringpi.digitalWrite(self.__config['pin']['rst'], 1)
        sleep(0.1)
        wiringpi.digitalWrite(self.__config['pin']['rst'], 0)
        sleep(0.1)
        wiringpi.digitalWrite(self.__config['pin']['rst'], 1)
        sleep(0.1)

    def __regWrite(self, Reg):
        wiringpi.digitalWrite(self.__config['pin']['dc'], 0)
        self.__spi.writebytes([Reg])

    def __dataWrite_8bit(self, Data):
        wiringpi.digitalWrite(self.__config['pin']['dc'], 1)
        self.__spi.writebytes([Data])

    def __dataWrite_NLen16Bit(self, Data, DataLen):
        wiringpi.digitalWrite(self.__config['pin']['dc'], 1)
        for i in range(0, DataLen):
            self.__spi.writebytes([Data >> 8])
            self.__spi.writebytes([Data & 0xff])

    def __regInit(self):
        # ST7735R Frame Rate
        self.__regWrite(0xB1)
        self.__dataWrite_8bit(0x01)
        self.__dataWrite_8bit(0x2C)
        self.__dataWrite_8bit(0x2D)

        self.__regWrite(0xB2)
        self.__dataWrite_8bit(0x01)
        self.__dataWrite_8bit(0x2C)
        self.__dataWrite_8bit(0x2D)

        self.__regWrite(0xB3)
        self.__dataWrite_8bit(0x01)
        self.__dataWrite_8bit(0x2C)
        self.__dataWrite_8bit(0x2D)
        self.__dataWrite_8bit(0x01)
        self.__dataWrite_8bit(0x2C)
        self.__dataWrite_8bit(0x2D)

        # Column inversion
        self.__regWrite(0xB4)
        self.__dataWrite_8bit(0x07)

        # ST7735R Power Sequence
        self.__regWrite(0xC0)
        self.__dataWrite_8bit(0xA2)
        self.__dataWrite_8bit(0x02)
        self.__dataWrite_8bit(0x84)
        self.__regWrite(0xC1)
        self.__dataWrite_8bit(0xC5)

        self.__regWrite(0xC2)
        self.__dataWrite_8bit(0x0A)
        self.__dataWrite_8bit(0x00)

        self.__regWrite(0xC3)
        self.__dataWrite_8bit(0x8A)
        self.__dataWrite_8bit(0x2A)
        self.__regWrite(0xC4)
        self.__dataWrite_8bit(0x8A)
        self.__dataWrite_8bit(0xEE)

        self.__regWrite(0xC5)  # VCOM
        self.__dataWrite_8bit(0x0E)

        # ST7735R Gamma Sequence
        self.__regWrite(0xe0)
        self.__dataWrite_8bit(0x0f)
        self.__dataWrite_8bit(0x1a)
        self.__dataWrite_8bit(0x0f)
        self.__dataWrite_8bit(0x18)
        self.__dataWrite_8bit(0x2f)
        self.__dataWrite_8bit(0x28)
        self.__dataWrite_8bit(0x20)
        self.__dataWrite_8bit(0x22)
        self.__dataWrite_8bit(0x1f)
        self.__dataWrite_8bit(0x1b)
        self.__dataWrite_8bit(0x23)
        self.__dataWrite_8bit(0x37)
        self.__dataWrite_8bit(0x00)
        self.__dataWrite_8bit(0x07)
        self.__dataWrite_8bit(0x02)
        self.__dataWrite_8bit(0x10)

        self.__regWrite(0xe1)
        self.__dataWrite_8bit(0x0f)
        self.__dataWrite_8bit(0x1b)
        self.__dataWrite_8bit(0x0f)
        self.__dataWrite_8bit(0x17)
        self.__dataWrite_8bit(0x33)
        self.__dataWrite_8bit(0x2c)
        self.__dataWrite_8bit(0x29)
        self.__dataWrite_8bit(0x2e)
        self.__dataWrite_8bit(0x30)
        self.__dataWrite_8bit(0x30)
        self.__dataWrite_8bit(0x39)
        self.__dataWrite_8bit(0x3f)
        self.__dataWrite_8bit(0x00)
        self.__dataWrite_8bit(0x07)
        self.__dataWrite_8bit(0x03)
        self.__dataWrite_8bit(0x10)

        # Enable test command
        self.__regWrite(0xF0)
        self.__dataWrite_8bit(0x01)

        # Disable ram power save mode
        self.__regWrite(0xF6)
        self.__dataWrite_8bit(0x00)

        # 65k mode
        self.__regWrite(0x3A)
        self.__dataWrite_8bit(0x05)

    def __setGramScanWay(self):
        if (self.scanDir == ScanDir.L2R_U2D) or (self.scanDir == ScanDir.L2R_D2U) or (
                self.scanDir == ScanDir.R2L_U2D) or (
                self.scanDir == ScanDir.R2L_D2U):
            if self.scanDir == ScanDir.L2R_U2D:
                memoryAccessRegData = 0X00 | 0x00
            elif self.scanDir == ScanDir.L2R_D2U:
                memoryAccessRegData = 0X00 | 0x80
            elif self.scanDir == ScanDir.R2L_U2D:
                memoryAccessRegData = 0x40 | 0x00
            else:  # R2L_D2U:
                memoryAccessRegData = 0x40 | 0x80
        else:
            if self.scanDir == ScanDir.U2D_L2R:
                memoryAccessRegData = 0X00 | 0x00 | 0x20
            elif self.scanDir == ScanDir.U2D_R2L:
                memoryAccessRegData = 0X00 | 0x40 | 0x20
            elif self.scanDir == ScanDir.D2U_L2R:
                memoryAccessRegData = 0x80 | 0x00 | 0x20
            else:  # R2L_D2U
                memoryAccessRegData = 0x40 | 0x80 | 0x20

        # please set (memoryAccessRegData & 0x10) != 1
        if (memoryAccessRegData & 0x10) != 1:
            self.LCD_X_Adjust = 1
            self.LCD_Y_Adjust = 2
        else:
            self.LCD_X_Adjust = 2
            self.LCD_Y_Adjust = 1

        # Set the read / write scan direction of the frame memory
        self.__regWrite(0x36)  # MX, MY, BGR mode
        self.__dataWrite_8bit(memoryAccessRegData | 0x00)  # 0x00 set BGR

    def init(self):
        # Turn on the backlight
        wiringpi.digitalWrite(self.__config['pin']['bl'], 0)
        # Hardware reset
        self.reset()
        # Set the initialization register
        self.__regInit()
        # Set the display scan and color transfer modes
        self.__setGramScanWay()
        sleep(0.2)
        # sleep out
        self.__regWrite(0x11)
        sleep(0.12)
        # Turn on the LCD display
        self.__regWrite(0x29)

    # function:	Sets the start position and size of the display area
    def __setWindows(self, XStart, YStart, XEnd, YEnd):
        # set the X coordinates
        self.__regWrite(0x2A)
        self.__dataWrite_8bit(0x00)
        self.__dataWrite_8bit((XStart & 0xff) + self.LCD_X_Adjust)
        self.__dataWrite_8bit(0x00)
        self.__dataWrite_8bit(((XEnd - 1) & 0xff) + self.LCD_X_Adjust)

        # set the Y coordinates
        self.__regWrite(0x2B)
        self.__dataWrite_8bit(0x00)
        self.__dataWrite_8bit((YStart & 0xff) + self.LCD_Y_Adjust)
        self.__dataWrite_8bit(0x00)
        self.__dataWrite_8bit(((YEnd - 1) & 0xff) + self.LCD_Y_Adjust)

        self.__regWrite(0x2C)

    def clear(self):
        _buffer = [0xff] * (self.width * self.height * 2)
        self.__setWindows(0, 0, self.width, self.height)
        wiringpi.digitalWrite(self.__config['pin']['dc'], 1)
        for i in range(0, len(_buffer), 4096):
            self.__spi.writebytes(_buffer[i:i + 4096])

    def showImage(self, img):
        try:
            if type(img) == np.ndarray:  # opencv format
                imwidth, imheight, _ = img.shape
                if imwidth != self.width or imheight != self.height:
                    img = cv2.resize(img, (self.width, self.height))

            else:  # PIL format
                img = np.asarray(img)
                imwidth, imheight, _ = img.shape
                if imwidth != self.width or imheight != self.height:
                    img = cv2.resize(img, (self.width, self.height))
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        except ValueError:
            return

        pix = np.zeros((self.width, self.height, 2), dtype=np.uint8)
        pix[..., [0]] = np.add(np.bitwise_and(img[..., [0]], 0xF8), np.right_shift(img[..., [1]], 5))
        pix[..., [1]] = np.add(np.bitwise_and(np.left_shift(img[..., [1]], 3), 0xE0), np.right_shift(img[..., [2]], 3))
        pix = pix.flatten().tolist()

        self.__setWindows(0, 0, self.width, self.height)
        wiringpi.digitalWrite(self.__config['pin']['dc'], 1)
        for i in range(0, len(pix), 4096):
            self.__spi.writebytes(pix[i:i + 4096])


if __name__ == '__main__':
    Lcd().backlight(False)
