import lvgl as lv
lv.init()

from machine import SPI, Pin

# Import ILI9341 driver and initialized it
import ili9xxx
from ili9341 import ili9341
disp = ili9341()

# # Import XPT2046 driver and initialize it

from xpt2046 import xpt2046
touch = xpt2046()


# Display power pin (README default wiring uses pin 14 for panel power)
Pin(14, Pin.OUT, value=1)

# 2.8" ILI9341 + XPT2046 module, README-default wiring:
# sck=19, mosi=18, miso=5, display cs=13, dc=12, rst=4, backlight=15, touch cs=25
spi = SPI(2, baudrate=24_000_000, sck=Pin(19), mosi=Pin(18), miso=Pin(5))
disp = ili9xxx.Ili9341(spi=spi, cs=13, dc=12, rst=4, bl=15, factor=8, doublebuffer=False)
touch = Xpt2046(spi=spi, cs=25, rot=XPT2046_LANDSCAPE, spiRate=24_000_000)

scr = lv.obj()
label = lv.label(scr)
label.set_text("Hello World!")
label.align(lv.ALIGN.CENTER, 0, -40)

btn = lv.button(scr)
btn.align(lv.ALIGN.CENTER, 0, 30)
btn_label = lv.label(btn)
btn_label.set_text("Tap me: 0")

count = [0]

def on_click(e):
    count[0] += 1
    btn_label.set_text("Tap me: %d" % count[0])
    print("tapped:", count[0])

btn.add_event_cb(on_click, lv.EVENT.CLICKED, None)

lv.screen_load(scr)
print("hello-world + touch loaded; display", disp.width, "x", disp.height)
