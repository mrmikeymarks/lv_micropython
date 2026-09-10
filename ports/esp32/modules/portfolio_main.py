# Frozen entry point for the developer portfolio: `import portfolio_main`
# brings up the hardware via hw_esp32 and starts the app. Make it run on
# boot with a one-line filesystem main.py:
#   import portfolio_main
# All content lives in portfolio_data.py; pages are the portfolio_pXX_*
# frozen modules (flat build of apps/portfolio - keep the two in sync).

import lvgl as lv

if hasattr(lv, "init"): lv.init()  # esp32 build exposes init; unix auto-inits

import hw_esp32

# From here the display works, so any failure can be shown on the panel
# instead of only on a serial console nobody is watching.
try:
    from portfolio_app import PortfolioApp, DEFAULT_PATH

    app = PortfolioApp(DEFAULT_PATH, hor_res=hw_esp32.disp.width,
                       ver_res=hw_esp32.disp.height)
    app.start()
    print("portfolio loaded:", len(app.pages), "pages from", DEFAULT_PATH,
          "-", hw_esp32.disp.width, "x", hw_esp32.disp.height)
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
