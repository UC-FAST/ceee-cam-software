from smbus2 import SMBus

class INA230:
    # Register address dictionary (UPPERCASE)
    __reg = {
        'CONFIG': 0x00,
        'SHUNTVOLT': 0x01,
        'BUSVOLT': 0x02,
        'POWER': 0x03,
        'CURRENT': 0x04,
        'CALIB': 0x05
    }
    
    # Configuration parameters dictionary (UPPERCASE)
    __config = {
        'AVG_MODE': 0,      # 0=1 sample, 1=4, 2=16, 3=64, 4=128, 5=256, 6=512, 7=1024
        'VBUS_CT': 4,        # Bus voltage conversion time (0=140μs,1=204μs,2=332μs,3=588μs,4=1.1ms,5=2.116ms,6=4.156ms,7=8.244ms)
        'VSH_CT': 4,         # Shunt voltage conversion time (same as above)
        'MODE': 7            # Operating mode (7=continuous shunt and bus measurement)
    }

    def __init__(self, busNum, address, shuntResistance, maxExpectedCurrent):
        """
        Initialize INA230 device
        :param busNum: I2C bus number (Raspberry Pi typically 1)
        :param address: I2C device address (0x40-0x4F)
        :param shuntResistance: Shunt resistance value (Ohms)
        :param maxExpectedCurrent: Maximum expected current (Amperes)
        """
        self.bus = SMBus(busNum)
        self.address = address
        self.shuntResistance = shuntResistance
        
        # Calculate calibration values (camelCase naming)
        self.currentLsb = maxExpectedCurrent / 32768.0
        self.powerLsb = 25.0 * self.currentLsb
        self.calibration = int(0.00512 / (self.currentLsb * shuntResistance))
        
        # Configure device
        self._configure()
        self._writeCalibration()

    def _configure(self):
        """Write configuration to CONFIG register"""
        config = (self.__config['AVG_MODE'] << 9) | \
                 (self.__config['VBUS_CT'] << 6) | \
                 (self.__config['VSH_CT'] << 3) | \
                 self.__config['MODE']
        
        self._writeWord(self.__reg['CONFIG'], config)

    def _writeCalibration(self):
        """Write calibration value to CALIB register"""
        self._writeWord(self.__reg['CALIB'], self.calibration)

    def _writeWord(self, register, data):
        """Write 16-bit data to register (big-endian format)"""
        msb = (data >> 8) & 0xFF
        lsb = data & 0xFF
        self.bus.write_i2c_block_data(self.address, register, [msb, lsb])

    def _readWord(self, register):
        """Read 16-bit data from register (big-endian format)"""
        data = self.bus.read_i2c_block_data(self.address, register, 2)
        return (data[0] << 8) | data[1]

    def readVoltage(self):
        """Read bus voltage (Volts)"""
        rawVoltage = self._readWord(self.__reg['BUSVOLT'])
        return rawVoltage * 0.00125  # LSB = 1.25mV

    def readCurrent(self):
        """Read current (Amperes)"""
        rawCurrent = self._readWord(self.__reg['CURRENT'])
        # Handle signed value (two's complement)
        if rawCurrent > 0x7FFF:
            rawCurrent -= 0x10000
        return rawCurrent * self.currentLsb

    def readPower(self):
        """Read power (Watts)"""
        rawPower = self._readWord(self.__reg['POWER'])
        return rawPower * self.powerLsb

    def readShuntVoltage(self):
        """Read shunt voltage (Volts)"""
        rawShunt = self._readWord(self.__reg['SHUNTVOLT'])
        # Handle signed value
        if rawShunt > 0x7FFF:
            rawShunt -= 0x10000
        return rawShunt * 0.0000025  # LSB = 2.5μV

    def close(self):
        """Close I2C connection"""
        self.bus.close()

# Example usage
if __name__ == "__main__":
    # Configuration parameters (camelCase naming)
    i2cBus = 1               # Raspberry Pi I2C bus number
    i2cAddress = 0x40        # INA230 address
    shuntResistance = 0.002     # Shunt resistance (Ohms)
    maxCurrent = 3.2          # Maximum expected current (Amperes)
    
    try:
        # Create INA230 instance
        ina230 = INA230(i2cBus, i2cAddress, shuntResistance, maxCurrent)
        
        # Print configuration information
        print("INA230 Configuration:")
        print(f"  I2C Address: 0x{ina230.address:02X}")
        print(f"  Shunt Resistance: {ina230.shuntResistance} Ω")
        print(f"  Calibration Value: {ina230.calibration}")
        print(f"  Current LSB: {ina230.currentLsb:.8f} A/bit")
        print(f"  Power LSB: {ina230.powerLsb:.8f} W/bit")
        
        # Read and display sensor data
        print("\nSensor Readings:")
        print(f"  Bus Voltage: {ina230.readVoltage():.3f} V")
        print(f"  Shunt Voltage: {ina230.readShuntVoltage():.6f} V")
        print(f"  Current: {ina230.readCurrent():.3f} A")
        print(f"  Power: {ina230.readPower():.3f} W")
        
        # Close connection
        ina230.close()
    
    except Exception as e:
        print(f"Error: {str(e)}")