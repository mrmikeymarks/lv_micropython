# Hardware bring-up for the 2.8" ILI9341 + XPT2046 SPI module.
# Importing this module initializes the display, the touch controller, and
# the LVGL event loop. All pin wiring lives here so UI code (demos/) stays
# hardware-free. Verified wiring (README-default):
#   sck=19 mosi=18 miso=5 | display cs=13 dc=12 rst=4 bl=15 power=14 | touch cs=25

import lvgl as lv
from machine import SPI, Pin
import ili9xxx
from xpt2046 import Xpt2046, XPT2046_LANDSCAPE

Pin(14, Pin.OUT, value=1)  # panel power

spi = SPI(2, baudrate=24_000_000, sck=Pin(19), mosi=Pin(18), miso=Pin(5))
disp = ili9xxx.Ili9341(spi=spi, cs=13, dc=12, rst=4, bl=15, factor=8, doublebuffer=False)
touch = Xpt2046(spi=spi, cs=25, rot=XPT2046_LANDSCAPE, spiRate=24_000_000)
