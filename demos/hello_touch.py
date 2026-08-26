# Universal LVGL demo: runs unchanged on the ESP32 device, the desktop
# simulator (unix port + SDL), and the online simulator (sim.lvgl.io v9.0
# via ?script=<raw URL>). Keep the UI code to LVGL 9.0-safe APIs so the
# online simulator (frozen at LVGL 9.0) stays compatible; the device and
# desktop run LVGL 9.3. See demos/README.md.

import sys
import lvgl as lv

WIDTH, HEIGHT = 320, 240


def build_ui():
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
    print("ui loaded on", sys.platform)


# --- environment bootstrap ------------------------------------------------
if sys.platform == "esp32":
    # Real hardware: frozen shim owns the wiring and starts the event loop.
    import hw_esp32
    build_ui()
elif sys.platform in ("darwin", "linux"):
    # Desktop simulator: SDL window + mouse. macOS has no machine.Timer and
    # the lv_timer fallback is Linux-only, so drive LVGL with asyncio.
    import lv_utils
    import asyncio
    lv.sdl_window_create(WIDTH, HEIGHT)
    lv.sdl_window_set_title(lv.display_get_default(), "lv_micropython demo")
    lv.sdl_mouse_create()
    ev = lv_utils.event_loop(asynchronous=True)
    build_ui()
    asyncio.Loop.run_forever()
else:
    # Online simulator: the page injects display_driver with its own loop.
    import display_driver
    build_ui()
