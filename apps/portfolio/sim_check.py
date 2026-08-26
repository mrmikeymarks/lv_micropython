# Headless smoke test: build every portfolio page against a dummy 320x240
# display and report per-page object counts, build time, and heap cost.
#
# Run from this directory with the unix lv_micropython binary:
#   cd apps/portfolio
#   ../../ports/unix/build-standard/micropython sim_check.py [page_number]
#
# Exit code 0 = all pages built and rendered without an exception.

import sys
import gc
import time

import lvgl as lv

if hasattr(lv, "init"):
    lv.init()

HOR, VER = 320, 240

disp = lv.display_create(HOR, VER)
# Same size as the ili9xxx driver's buffer on the device (factor=8), so a
# heap-constrained run (-X heapsize=110k) mirrors a no-PSRAM ESP32.
buf = bytearray(HOR * 30 * 2)
disp.set_buffers(buf, None, len(buf), lv.DISPLAY_RENDER_MODE.PARTIAL)
disp.set_flush_cb(lambda d, area, px: d.flush_ready())

from portfolio.app import PortfolioApp
from portfolio.data import PORTFOLIO
from portfolio.pages import PAGES


def count_objs(obj):
    n = obj.get_child_count()
    total = n
    for i in range(n):
        total += count_objs(obj.get_child(i))
    return total


def pump(ms=400, step=20):
    for _ in range(ms // step):
        lv.tick_inc(step)
        lv.timer_handler()


app = PortfolioApp(PORTFOLIO)
app.start()
pump()

only = None
if len(sys.argv) > 1:
    only = int(sys.argv[1])

failures = 0
for i in range(len(PAGES)):
    if only is not None and i + 1 != only:
        continue
    name = PAGES[i][0]
    gc.collect()
    mem_before = gc.mem_alloc()
    t0 = time.ticks_ms()
    try:
        app.show_page(i)
        pump()  # let animations/timers tick and layouts settle
        elapsed = time.ticks_diff(time.ticks_ms(), t0)
        objs = count_objs(app.content)
        gc.collect()
        mem_kb = (gc.mem_alloc() - mem_before) / 1024
        note = ""
        if app._page_mod is None:
            note += " DEGRADED:low-memory notice shown"
        if objs > 90:
            note += " WARN:objs>90"
        if mem_kb > 40:
            note += " WARN:mem>40KB"
        print("PASS %-16s objs=%-3d build=%dms mem=%.1fKB%s"
              % (name, objs, elapsed, mem_kb, note))
    except Exception as e:
        failures += 1
        print("FAIL %-16s %s: %s" % (name, type(e).__name__, e))
        sys.print_exception(e)

# Exercise navigation the way a user would: wrap forward past the end.
if only is None and failures == 0:
    try:
        for _ in range(len(PAGES) + 1):
            app.step(1)
            pump(100)
        print("PASS navigation wrap-around")
    except Exception as e:
        failures += 1
        print("FAIL navigation: %s: %s" % (type(e).__name__, e))
        sys.print_exception(e)

print("---")
print("%d failure(s)" % failures)
sys.exit(1 if failures else 0)
