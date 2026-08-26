# Minimal frozen example: initialize the hardware and show a label.
# (The earlier version mixed rdagger and generic driver imports that don't
# exist in this firmware — `from ili9341 import ili9341` and lowercase
# `xpt2046` — and constructed the display twice.)
# For the full portable demo workflow (device / desktop SDL / online
# simulator from one file) see demos/hello_touch.py.

import lvgl as lv
import hw_esp32

scr = lv.obj()
label = lv.label(scr)
label.set_text("Hello from frozen hello_lvgl_main")
label.center()
lv.screen_load(scr)
