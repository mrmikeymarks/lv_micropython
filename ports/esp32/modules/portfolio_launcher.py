# Button-gated launcher: boot to a standby screen, start the portfolio when
# the button is pressed. Boot via a one-line filesystem main.py:
#   import portfolio_launcher
#
# BUTTON_PIN: GPIO0 is the BOOT button fitted on virtually every ESP32 dev
# board - press-to-start with no extra wiring. If you wire your own button
# (to GND, using the internal pull-up), free pins with this display wiring
# are 21, 26, 27, 32, 33 (34/35/36/39 are input-only and need an external
# pull-up). Do NOT use 13 (display CS), 25 (touch CS), or any other pin in
# hw_esp32's wiring table; 0/2/12/15 are strapping pins - 0 is fine as an
# active-low button after boot.

import lvgl as lv

if hasattr(lv, "init"): lv.init()

import hw_esp32
from machine import Pin
import portfolio_theme as theme

BUTTON_PIN = 0  # BOOT button; active low

theme.init()
_btn = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)

_scr = lv.obj()
_scr.set_style_bg_color(theme.BG, 0)
_scr.set_style_bg_opa(lv.OPA.COVER, 0)
_title = theme.label(_scr, "Portfolio", theme.FONT_L, theme.TEXT)
_title.align(lv.ALIGN.CENTER, 0, -30)
_hint = theme.label(_scr, lv.SYMBOL.PLAY + "  press BOOT to start",
                    theme.FONT_M, theme.ACCENT)
_hint.align(lv.ALIGN.CENTER, 0, 10)
lv.screen_load(_scr)

_pressed = [0]


def _poll(t):
    # 3 consecutive low reads @50ms = debounced press; then launch once.
    if _btn.value() == 0:
        _pressed[0] += 1
    else:
        _pressed[0] = 0
    if _pressed[0] >= 3:
        t.delete()
        _hint.set_text("loading...")
        lv.refr_now(None)
        import portfolio_main  # noqa: F401  (import = start the app)


_timer = lv.timer_create(_poll, 50, None)
print("launcher ready: press the button on GPIO%d to start" % BUTTON_PIN)
