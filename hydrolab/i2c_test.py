#!/usr/bin/env python3
import time
from smbus2 import SMBus, i2c_msg

BUS, ADDR = 1, 0x44

def crc8(data):
    crc = 0xFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x31) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc

def read(bus):
    bus.write_i2c_block_data(ADDR, 0x2C, [0x06])  # single-shot, high repeatability, clock stretching
    time.sleep(0.02)
    msg = i2c_msg.read(ADDR, 6)
    bus.i2c_rdwr(msg)
    d = list(msg)
    if crc8(d[0:2]) != d[2] or crc8(d[3:5]) != d[5]:
        raise IOError("CRC mismatch")
    raw_t = (d[0] << 8) | d[1]
    raw_h = (d[3] << 8) | d[4]
    return -45 + 175 * raw_t / 65535, 100 * raw_h / 65535

if __name__ == "__main__":
    with SMBus(BUS) as bus:
        while True:
            t, h = read(bus)
            print(f"{time.strftime('%H:%M:%S')}  T={t:.2f} °C  RH={h:.2f} %")
            time.sleep(1)
