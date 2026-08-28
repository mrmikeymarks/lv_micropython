# I2C bring-up companion to hw_esp32.py.
# Importing this module configures hardware I2C(0) on the standard ESP32
# pins, chosen to avoid the display/touch SPI wiring (see hw_esp32.py):
#   scl=22 sda=21 @ 400kHz
# Usage:
#   import i2c_esp32
#   i2c_esp32.scan()                  # list attached device addresses
#   dev = i2c_esp32.i2c               # pass to any driver taking machine.I2C

from machine import I2C, Pin

SCL = 22
SDA = 21
FREQ = 400_000

i2c = I2C(0, scl=Pin(SCL), sda=Pin(SDA), freq=FREQ)


def scan(verbose=True):
    found = i2c.scan()
    if verbose:
        if found:
            for addr in found:
                print("I2C device at 0x%02x" % addr)
        else:
            print("no I2C devices found (scl=%d sda=%d)" % (SCL, SDA))
    return found
