import smbus2
import time
from datetime import datetime

class BQ32002Driver:
    """
    BQ32002 RTC driver for Raspberry Pi using SMBus.
    Handles communication with BQ32002 real-time clock module.
    """
    
    # Register addresses dictionary (keys in uppercase without prefix)
    REGISTERS = {
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
    FLAGS = {
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
    
    def __init__(self, busNumber=1, deviceAddress=0x68):
        """
        Initialize I2C connection to BQ32002.
        
        Args:
            busNumber: I2C bus number (default: 1 for Raspberry Pi 3/4)
            deviceAddress: BQ32002 device address (default: 0x68)
        """
        self.bus = smbus2.SMBus(busNumber)
        self.deviceAddress = deviceAddress
        self.configureDevice()

    def configureDevice(self):
        """Configure BQ32002 to 24-hour mode and enable oscillator."""
        # Ensure clock is running (clear STOP bit)
        seconds = self._readByte(self.REGISTERS['SECONDS'])
        if seconds & self.FLAGS['STOP_BIT']:
            self._writeByte(self.REGISTERS['SECONDS'], seconds & ~self.FLAGS['STOP_BIT'])
        
        # Set 24-hour mode in status register
        status = self._readByte(self.REGISTERS['STATUS'])
        if status & self.FLAGS['HOUR_12_24_FLAG']:
            self._writeByte(self.REGISTERS['STATUS'], status & ~self.FLAGS['HOUR_12_24_FLAG'])
        
        # Enable oscillator if disabled
        control = self._readByte(self.REGISTERS['CONTROL'])
        if control & self.FLAGS['OSC_DISABLE']:
            self._writeByte(self.REGISTERS['CONTROL'], control & ~self.FLAGS['OSC_DISABLE'])

    def readTime(self):
        """
        Read current date and time from RTC.
        
        Returns:
            datetime object containing current RTC time
        """
        data = self.bus.read_i2c_block_data(self.deviceAddress, self.REGISTERS['SECONDS'], 7)
        
        # Extract time components (convert BCD to decimal)
        seconds = self._bcdToDec(data[0] & 0x7F)  # Mask STOP bit
        minutes = self._bcdToDec(data[1])
        hours = self._bcdToDec(data[2] & 0x3F)    # Mask 12/24 mode bit
        day = self._bcdToDec(data[3])
        date = self._bcdToDec(data[4])
        month = self._bcdToDec(data[5] & 0x1F)     # Mask century bit
        year = self._bcdToDec(data[6]) + 2000      # Assume 21st century
        
        return datetime(year, month, date, hours, minutes, seconds)

    def setTime(self, dt):
        """
        Set RTC date and time.
        
        Args:
            dt: datetime object containing desired time
        """
        # Convert values to BCD format
        data = [
            self._decToBcd(dt.second) & 0x7F,   # Ensure STOP bit is clear
            self._decToBcd(dt.minute),
            self._decToBcd(dt.hour) & 0x3F,      # Set 24-hour mode
            self._decToBcd(dt.isoweekday()),      # ISO weekday (1=Monday)
            self._decToBcd(dt.day),
            self._decToBcd(dt.month),
            self._decToBcd(dt.year % 100)        # Last two digits of year
        ]
        
        # Write time block to registers
        self.bus.write_i2c_block_data(self.deviceAddress, self.REGISTERS['SECONDS'], data)

    def readCalibration(self):
        """
        Read calibration value from RTC.
        
        Returns:
            Tuple of (calibration_value, is_negative)
        """
        cal = self._readByte(self.REGISTERS['CALIBRATION'])
        sign = cal & self.FLAGS['CAL_SIGN']
        value = cal & 0x1F  # Mask calibration value bits
        
        # Handle two's complement for negative values
        if sign:
            return (value - 32, True)
        return (value, False)

    def setCalibration(self, value):
        """
        Set calibration value.
        
        Args:
            value: Calibration value between -16 and +15
        """
        if not -16 <= value <= 15:
            raise ValueError("Calibration value must be between -16 and +15")
        
        # Handle negative values using two's complement
        if value < 0:
            calValue = (abs(value) | self.FLAGS['CAL_SIGN']) ^ 0x20
        else:
            calValue = value
        
        self._writeByte(self.REGISTERS['CALIBRATION'], calValue)

    def _readByte(self, register):
        """Read single byte from specified register."""
        return self.bus.read_byte_data(self.deviceAddress, register)

    def _writeByte(self, register, value):
        """Write single byte to specified register."""
        self.bus.write_byte_data(self.deviceAddress, register, value)

    def _bcdToDec(self, bcd):
        """Convert BCD byte to decimal."""
        return (bcd // 16) * 10 + (bcd & 0x0F)

    def _decToBcd(self, dec):
        """Convert decimal to BCD byte."""
        return (dec // 10) << 4 | (dec % 10)

# Example usage
if __name__ == "__main__":
    rtc = BQ32002Driver()
    
    # Set RTC time to current system time
    currentTime = datetime.now()
    print(f"Setting RTC time to: {currentTime}")
    rtc.setTime(currentTime)
    
    # Read back RTC time
    time.sleep(10)  # Wait for potential second change
    rtcTime = rtc.readTime()
    print(f"RTC reports time: {rtcTime}")
    
    # Read and display calibration value
    calValue, isNegative = rtc.readCalibration()
    print(f"Calibration value: {'-' if isNegative else '+'}{abs(calValue)} ppm")
    
    # Set calibration example (uncomment to use)
    # rtc.setCalibration(-5)  # Set to -5 ppm