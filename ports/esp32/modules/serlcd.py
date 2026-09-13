# SparkFun Qwiic SerLCD (16x2, AVR-based) on the shared I2C pins.
#
# The SerLCD stretches the clock while its firmware digests each byte, and
# the ESP32's hardware I2C master NACKs it at any speed. A bit-banged
# SoftI2C at 100 kHz talks to it fine, so this driver borrows the bus pins
# for the few milliseconds of a write and hands them back to the hardware
# bus (i2c_esp32.restore()) - the sensors keep their 400 kHz hardware bus.
#
#   import serlcd
#   lcd = serlcd.SerLCD()               # address 0x2D on this board (factory default is 0x72)
#   lcd.show("20.9C 47%  1012h", "CO2 400 TVOC 0")
#
# Commands follow the SerLCD firmware: '|' prefix for settings ('-' clear,
# 0x18 contrast, '+' r g b backlight), 0xFE prefix for HD44780 cursor moves.

import time
from machine import SoftI2C, Pin

import i2c_esp32

COLS = 16


class SerLCD:
    def __init__(self, addr=0x2D, scl=i2c_esp32.SCL, sda=i2c_esp32.SDA, freq=100_000):
        self.addr = addr
        self.scl = Pin(scl)
        self.sda = Pin(sda)
        self.freq = freq
        self.soft = SoftI2C(scl=self.scl, sda=self.sda, freq=freq, timeout=50_000)
        i2c_esp32.restore()
        self.errors = 0
        self._line = bytearray(COLS)   # padded line buffer, reused for every write

    def _send(self, *chunks):
        """Borrow the pins, write the chunks, give the pins back. Never raises:
        a display that is unplugged just counts an error."""
        self.soft.init(scl=self.scl, sda=self.sda, freq=self.freq)
        try:
            for c in chunks:
                self.soft.writeto(self.addr, c)
                time.sleep_ms(2)
        except OSError:
            self.errors += 1
        finally:
            i2c_esp32.restore()

    def clear(self):
        self._send(b"|-")
        time.sleep_ms(10)

    def backlight(self, r, g, b):
        self._send(bytes((0x7C, 0x2B, r, g, b)))

    def contrast(self, v):
        self._send(bytes((0x7C, 0x18, v)))

    def _pad(self, text):
        # text -> exactly COLS bytes in the reused buffer (no new objects
        # beyond what the caller's string already cost)
        n = min(len(text), COLS)
        for i in range(n):
            self._line[i] = ord(text[i])
        for i in range(n, COLS):
            self._line[i] = 32
        return self._line

    def show(self, line1, line2=""):
        """Overwrite both lines (no clear, so no flicker)."""
        self._send(b"\xfe\x80", self._pad(line1), b"\xfe\xc0", self._pad(line2))

    def set_address(self, new_addr):
        """Persistently change the SerLCD's I2C address (takes effect immediately)."""
        self._send(bytes((0x7C, 0x19, new_addr)))
        self.addr = new_addr
