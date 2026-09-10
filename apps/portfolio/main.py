# Device entry point: bring up the 2.8" ILI9341 + XPT2046 module and run the
# portfolio. Wiring matches the repo's README-default hw_esp32.py:
#   sck=19 mosi=18 miso=5 | display cs=13 dc=12 rst=4 bl=15 | touch cs=25
#   panel power on pin 14
# Drivers (ili9xxx, xpt2046, lv_utils) are frozen into the firmware.

import lvgl as lv

if hasattr(lv, "init"): lv.init()  # esp32 build exposes init; unix auto-inits

from machine import SPI, Pin

import ili9xxx
from xpt2046 import Xpt2046, XPT2046_LANDSCAPE

Pin(14, Pin.OUT, value=1)  # panel power

spi = SPI(2, baudrate=24_000_000, sck=Pin(19), mosi=Pin(18), miso=Pin(5))
disp = ili9xxx.Ili9341(spi=spi, cs=13, dc=12, rst=4, bl=15, factor=8,
                       doublebuffer=False)
touch = Xpt2046(spi=spi, cs=25, rot=XPT2046_LANDSCAPE, spiRate=24_000_000)

# From here the display works, so any failure can be shown on the panel
# instead of only on a serial console nobody is watching.
try:
    from portfolio.app import PortfolioApp
    from portfolio.data import PORTFOLIO

    app = PortfolioApp(PORTFOLIO, hor_res=disp.width, ver_res=disp.height)
    app.start()
    print("portfolio loaded:", PORTFOLIO["name"], "-",
          disp.width, "x", disp.height)
except Exception as e:
    import sys
    sys.print_exception(e)
    scr = lv.obj()
    scr.set_style_bg_color(lv.color_hex(0x2B0000), 0)
    msg = lv.label(scr)
    msg.set_long_mode(lv.label.LONG_MODE.WRAP)
    msg.set_width(300)
    msg.set_style_text_color(lv.color_hex(0xFFB0B0), 0)
    msg.set_text("portfolio failed to start\n\n%s: %s\n\n"
                 "see serial console for the full traceback"
                 % (type(e).__name__, e))
    msg.center()
    lv.screen_load(scr)
