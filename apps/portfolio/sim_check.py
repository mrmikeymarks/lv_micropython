# Headless check for the text-driven portfolio: validates the content file
# and builds every page against a dummy 320x240 display.
#
#   cd apps/portfolio
#   ../../ports/unix/build-standard/micropython sim_check.py [content.txt] [page]
#
# Content lint (any file, any author): unknown element kinds, more than
# MAX_ELEMENTS per page, non-ASCII text, unknown lv.SYMBOL names.
# Render check: per-page object count, build time, heap cost, widgets
# poking past the usable width, and navigation wrap-around with the same
# low-memory guards the device uses. Run with -X heapsize=120k (and
# PORTFOLIO_MODULES, below) to mirror a 110 KB no-PSRAM ESP32: this process
# is ~10 KB heavier than the board and holds the engine bytecode in RAM,
# which the frozen firmware doesn't. Exit code 0 = clean.

import sys
import os
import gc
import time

# On the device the engine is frozen (no compile step). For heap-tier runs
# point PORTFOLIO_MODULES at a directory of mpy-cross output so the test
# doesn't pay a source-compile spike the board never sees:
#   mpy-cross -o stage/portfolio_ui.mpy ports/esp32/modules/portfolio_ui.py (and _app)
sys.path.insert(0, os.getenv("PORTFOLIO_MODULES") or "../../ports/esp32/modules")

import lvgl as lv

if hasattr(lv, "init"):
    lv.init()

HOR, VER = 320, 240
disp = lv.display_create(HOR, VER)
buf = bytearray(HOR * 30 * 2)  # same size as the ili9xxx driver's buffer
disp.set_buffers(buf, None, len(buf), lv.DISPLAY_RENDER_MODE.PARTIAL)
disp.set_flush_cb(lambda d, area, px: d.flush_ready())

import portfolio_ui as ui
from portfolio_app import PortfolioApp

path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].isdigit() else "portfolio.txt"
only = int(sys.argv[-1]) if len(sys.argv) > 1 and sys.argv[-1].isdigit() else None
failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL", msg)


# ---- 1. content lint --------------------------------------------------------

# Uses the engine's own reader/parser so the lint sees exactly what the
# device will render (same line-ending, BOM, truncation and cap rules).
page_no, count, title, cost = 0, 0, "", 0
for n, (nxt, raw) in enumerate(ui.read_lines(path), 1):
    if len(raw) >= ui.MAX_LINE:
        fail("line %d: longer than %d bytes (truncated on the device)" % (n, ui.MAX_LINE))
    if ui.is_header(raw):
        if page_no and cost > ui.MAX_OBJECTS:
            fail("page %r: about %d widgets, max %d (refused on the device)" % (title, cost, ui.MAX_OBJECTS))
        page_no += 1
        count, title, cost = 0, ui.header_title(raw), 0
        continue
    p = ui.parse(raw)
    if not p:
        continue
    kind, fields = p
    count += 1
    if page_no == 0:
        fail("line %d: content before the first '= Title' header is ignored" % n)
    if kind not in ui.RENDERERS:
        fail("line %d (%s): unknown element kind %r" % (n, title, kind))
        continue
    cost += ui.estimate(kind, fields)
    if count == ui.MAX_ELEMENTS + 1:
        fail("page %r: more than %d elements" % (title, ui.MAX_ELEMENTS))
    if kind in ui.NEEDS_FIELDS and not any(fields):
        fail("line %d (%s): empty %s element" % (n, title, kind))
    cap = ui.MAX_ITEMS.get(kind)
    n_items = len(fields) - (1 if kind == "chips" else 0)
    if cap and n_items > cap:
        fail("line %d (%s): %s has %d items, only %d are shown" % (n, title, kind, n_items, cap))
    syms = ([f.split(":", 1)[0].strip() for f in fields if ":" in f] if kind in ("list", "grid")
            else fields[:1] if kind == "media" else [])
    for sym in syms:
        if not ui.symbol_known(sym):
            fail("line %d (%s): unknown symbol %r (shows a generic icon)" % (n, title, sym))
if page_no and cost > ui.MAX_OBJECTS:
    fail("page %r: about %d widgets, max %d (refused on the device)" % (title, cost, ui.MAX_OBJECTS))
if page_no == 0:
    fail("no '= Title' page headers found")
raw_bytes = open(path, "rb").read()
if any(b > 127 for b in raw_bytes):
    fail("file contains non-ASCII bytes (rendered as '?': the fonts have no such glyphs)")
print("lint: %d pages in %s, %d problem(s)" % (page_no, path, failures))


# ---- 2. render every page ---------------------------------------------------

def count_objs(obj):
    n = obj.get_child_count()
    return n + sum(count_objs(obj.get_child(i)) for i in range(n))


def overflow(obj, out, limit=HOR - 8):
    for i in range(obj.get_child_count()):
        c = obj.get_child(i)
        if c.get_x() + c.get_width() > limit + 1 and c.get_width() > 0:
            out.append("%dpx wide at x=%d" % (c.get_width(), c.get_x()))
        overflow(c, out, limit)
    return out


def pump(ms=400, step=20):
    for _ in range(ms // step):
        lv.tick_inc(step)
        lv.timer_handler()


app = PortfolioApp(path)
app.start()
pump()

for i in range(len(app.pages)):
    if only is not None and i + 1 != only:
        continue
    name = app.pages[i][0]
    gc.collect()
    before = gc.mem_alloc()
    t0 = time.ticks_ms()
    try:
        app.show_page(i)
        pump()
        ms = time.ticks_diff(time.ticks_ms(), t0)
        objs = count_objs(app.content)
        gc.collect()
        kb = (gc.mem_alloc() - before) / 1024
        note = ""
        if objs <= 1 and app.content.get_child_count() == 1:
            note += " DEGRADED:low-memory notice"
        spill = overflow(app.content, [])
        if spill:
            note += " OVERFLOW:" + spill[0]
            failures += 1
        print("PASS %-14s objs=%-3d build=%dms mem=%.1fKB%s" % (name, objs, ms, kb, note))
    except Exception as e:
        fail("%s: %s: %s" % (name, type(e).__name__, e))
        sys.print_exception(e)

if only is None and failures == 0:
    try:
        for _ in range(len(app.pages) + 1):
            app.step(1)
            pump(100)
        print("PASS navigation wrap-around")
    except Exception as e:
        fail("navigation: %s: %s" % (type(e).__name__, e))
        sys.print_exception(e)

print("---")
print("%d failure(s)" % failures)
sys.exit(1 if failures else 0)
