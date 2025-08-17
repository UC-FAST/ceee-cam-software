import smbus2
import time
from datetime import datetime

from . import configLoader


class BQ32002:
    """
    BQ32002 RTC driver for Raspberry Pi using SMBus.
    Handles communication with BQ32002 real-time clock module.
    """

    # Register addresses dictionary (keys in uppercase without prefix)
    __reg = {
        'SECONDS': 0x00,
        'MINUTES': 0x01,
        'HOURS': 0x02,
        'DAY': 0x03,
        'DATE': 0x04,
        'MONTH': 0x05,
        'YEAR': 0x06,
        'CALIBRATION': 0x07,
        'CONTROL': 0x0E,
        'STATUS': 0x0F
    }

    # Configuration flags dictionary
    __flags = {
        'STOP_BIT': 0x80,         # Clock stop bit in seconds register
        'HOUR_12_24_MODE': 0x40,   # 12/24 hour mode bit in hours register
        'CAL_SIGN': 0x80,         # Calibration sign bit in calibration register
        'OUTPUT_CONTROL': 0x80,    # Output control bit in control register
        'TEMP_COMP_INT': 0x20,     # Temperature compensation interval bit
        'TEMP_COMP_EN': 0x10,      # Temperature compensation enable bit
        'OSC_DISABLE': 0x08,      # Oscillator disable bit
        'CF_BIT': 0x04,           # Calibration flag bit in status register
        'HOUR_12_24_FLAG': 0x02,  # 12/24 hour flag in status register
        'STOP_FLAG': 0x01         # Stop flag in status register
    }

    def __init__(
        self,
            busNumber=configLoader.ConfigLoader()['sensor']['BQ32002']['bus'],
            addr=0x68
    ):
        """
        Initialize I2C connection to BQ32002.

        Args:
            busNumber: I2C bus number (default: 1 for Raspberry Pi 3/4)
            deviceAddress: BQ32002 device address (default: 0x68)
        """
        self.__bus = smbus2.SMBus(busNumber)
        self.__addr = addr
        self.configureDevice()

    def configureDevice(self):
        """Configure BQ32002 to 24-hour mode and enable oscillator."""
        # Ensure clock is running (clear STOP bit)
        seconds = self.__bus.read_byte_data(self.__addr, self.__reg['SECONDS'])
        if seconds & self.__flags['STOP_BIT']:
            self.__writeByte(self.__reg['SECONDS'],
                             seconds & ~self.__flags['STOP_BIT'])

        # Set 24-hour mode in status register
        status = self.__bus.read_byte_data(self.__addr, self.__reg['STATUS'])
        if status & self.__flags['HOUR_12_24_FLAG']:
            self.__writeByte(
                self.__reg['STATUS'], status & ~self.__flags['HOUR_12_24_FLAG'])

        # Enable oscillator if disabled
        control = self.__bus.read_byte_data(self.__addr, self.__reg['CONTROL'])
        if control & self.__flags['OSC_DISABLE']:
            self.__writeByte(self.__reg['CONTROL'],
                             control & ~self.__flags['OSC_DISABLE'])

    def getTime(self):
        """
        Read current date and time from RTC.

        Returns:
            datetime object containing current RTC time
        """
        data = self.__bus.read_i2c_block_data(
            self.__addr, self.__reg['SECONDS'], 7)

        # Extract time components (convert BCD to decimal)
        seconds = self.__bcdToDec(data[0] & 0x7F)  # Mask STOP bit
        minutes = self.__bcdToDec(data[1])
        hours = self.__bcdToDec(data[2] & 0x3F)    # Mask 12/24 mode bit
        day = self.__bcdToDec(data[3])
        date = self.__bcdToDec(data[4])
        month = self.__bcdToDec(data[5] & 0x1F)     # Mask century bit
        year = self.__bcdToDec(data[6]) + 2000      # Assume 21st century

        return datetime(year, month, date, hours, minutes, seconds)

    def setTime(self, dt: datetime):
        """
        Set RTC date and time.

        Args:
            dt: datetime object containing desired time
        """
        # Convert values to BCD format
        data = [
            self.__decToBcd(dt.second) & 0x7F,   # Ensure STOP bit is clear
            self.__decToBcd(dt.minute),
            self.__decToBcd(dt.hour) & 0x3F,      # Set 24-hour mode
            self.__decToBcd(dt.isoweekday()),      # ISO weekday (1=Monday)
            self.__decToBcd(dt.day),
            self.__decToBcd(dt.month),
            self.__decToBcd(dt.year % 100)        # Last two digits of year
        ]

        # Write time block to registers
        self.__bus.write_i2c_block_data(
            self.__addr, self.__reg['SECONDS'], data)

    @property
    def calibration(self):
        """
        Read calibration value from RTC.

        Returns:
            Tuple of (calibration_value, is_negative)
        """
        cal = self.__bus.read_byte_data(self.__addr, self.__reg['CALIBRATION'])
        sign = cal & self.__flags['CAL_SIGN']
        value = cal & 0x1F  # Mask calibration value bits

        # Handle two's complement for negative values
        if sign:
            return (value - 32, True)
        return (value, False)

    @calibration.setter
    def calibration(self, value):
        """
        Set calibration value.

        Args:
            value: Calibration value between -16 and +15
        """
        if not -16 <= value <= 15:
            raise ValueError("Calibration value must be between -16 and +15")

        # Handle negative values using two's complement
        if value < 0:
            calValue = (abs(value) | self.__flags['CAL_SIGN']) ^ 0x20
        else:
            calValue = value

        self.__bus.write_byte_data(
            self.__addr, self.__reg['CALIBRATION'], calValue)

    def __bcdToDec(self, bcd):
        """Convert BCD byte to decimal."""
        return (bcd // 16) * 10 + (bcd & 0x0F)

    def __decToBcd(self, dec):
        """Convert decimal to BCD byte."""
        return (dec // 10) << 4 | (dec % 10)


# Example usage
if __name__ == "__main__":
    rtc = BQ32002()

    # Set RTC time to current system time
    currentTime = datetime.now()
    print(f"Setting RTC time to: {currentTime}")
    rtc.setTime(currentTime)

    # Read back RTC time
    time.sleep(3)  # Wait for potential second change
    rtcTime = rtc.getTime()
    print(f"RTC reports time: {rtcTime}")

    # Read and display calibration value
    calValue, isNegative = rtc.calibration
    print(
        f"Calibration value: {'-' if isNegative else '+'}{abs(calValue)} ppm")
