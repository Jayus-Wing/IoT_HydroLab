import time
from smbus2 import SMBus, i2c_msg

SHT30_ADDR = 0x44

# Module 1 on I2C bus 1 (default), Module 2 on I2C bus 3
MODULE_I2C_BUS = {
    "module_1": 1,
    "module_2": 3,
}

def _crc8(data):
    crc = 0xFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x31) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc

def read_sht30(module="module_1", retries=3):
    """Read temperature (C) and humidity (%RH) from SHT30. Returns (temp, humidity)."""
    bus_num = MODULE_I2C_BUS[module]
    for attempt in range(retries):
        try:
            with SMBus(bus_num) as bus:
                bus.write_i2c_block_data(SHT30_ADDR, 0x2C, [0x06])
                time.sleep(0.05)
                msg = i2c_msg.read(SHT30_ADDR, 6)
                bus.i2c_rdwr(msg)
                d = list(msg)
                if _crc8(d[0:2]) != d[2] or _crc8(d[3:5]) != d[5]:
                    raise IOError("SHT30 CRC mismatch")
                raw_t = (d[0] << 8) | d[1]
                raw_h = (d[3] << 8) | d[4]
                temp = -45 + 175 * raw_t / 65535
                humidity = 100 * raw_h / 65535
                return temp, humidity
        except IOError:
            if attempt == retries - 1:
                raise
            time.sleep(0.1)

def get_water_level():
    """Return faked water level (hardcoded)."""
    return 75.0
