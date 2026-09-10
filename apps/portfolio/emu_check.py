# Emulator sweep for the portfolio engine: catches LVGL v8-to-v9 porting
# mistakes and dead controls.
#
#   1. API audit - every `lv.<...>` attribute chain in the engine sources is
#      resolved against the running LVGL 9 binding, so a v8-era name
#      (lv.btn, lv.scr_act, clear_flag) fails even on a line no test hits.
#   2. Interaction walk - clicks the real prev/next buttons through the whole
#      page ring both ways, checks the header title tracks the content file,
#      fires click events on every clickable widget of every page, and pokes
#      the gesture handler with no input device attached.
#
#   cd apps/portfolio && ../../ports/unix/build-standard/micropython emu_check.py [content.txt]
# Exit code 0 = clean.

import sys
import os
import gc

sys.path.insert(0, os.getenv("PORTFOLIO_MODULES") or "../../ports/esp32/modules")

import lvgl as lv

if hasattr(lv, "init"):
    lv.init()

MODULES = "../../ports/esp32/modules/"
SOURCES = tuple(MODULES + m for m in (
    "portfolio_ui.py", "portfolio_app.py", "portfolio_main.py", "portfolio_launcher.py"))
V8_RELICS = ("lv.btn", "lv.scr_act", "lv.disp_drv", "lv.indev_drv", "scr_load(",
             "lv.task_handler", "set_style_local_", "lv.ALIGN.IN_", "get_act(",
             "lv.btnmatrix", "lv.img(", "lv.img.", "clear_flag(")
failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL", msg)


def _ident(ch):
    return ch.isalpha() or ch.isdigit() or ch == "_"


def _chains(src):
    """Every dotted attribute chain rooted at `lv.` (MicroPython's re has no
    finditer, so scan by hand)."""
    i = 0
    while True:
        i = src.find("lv.", i)
        if i < 0:
            return
        if i > 0 and _ident(src[i - 1]):
            i += 3
            continue
        j = i + 3
        parts = []
        while True:
            k = j
            while k < len(src) and _ident(src[k]):
                k += 1
            if k == j:
                break
            parts.append(src[j:k])
            if k + 1 < len(src) and src[k] == "." and _ident(src[k + 1]):
                j = k + 1
            else:
                break
        if parts:
            yield ".".join(parts)
        i = j


def audit_api():
    checked = set()
    for path in SOURCES:
        try:
            src = open(path).read()
        except OSError:
            fail("source missing: " + path)
            continue
        src = "\n".join(l.split("#", 1)[0] for l in src.split("\n") if "hasattr(lv" not in l)
        for pat in V8_RELICS:
            if pat in src:
                fail("v8 relic %r in %s" % (pat, path))
        for chain in _chains(src):
            if chain in checked:
                continue
            checked.add(chain)
            obj = lv
            for part in chain.split("."):
                try:
                    obj = getattr(obj, part)
                except AttributeError:
                    fail("lv.%s not in this LVGL binding (used in %s)" % (chain, path))
                    break
    print("api audit: %d distinct lv.* chains resolved" % len(checked))


def pump(ms=200, step=20):
    for _ in range(ms // step):
        lv.tick_inc(step)
        lv.timer_handler()


def clickables(obj, out):
    for i in range(obj.get_child_count()):
        c = obj.get_child(i)
        if c.has_flag(lv.obj.FLAG.CLICKABLE):
            out.append(c)
        clickables(c, out)
    return out


def walk_app(path):
    disp = lv.display_create(320, 240)
    buf = bytearray(320 * 30 * 2)
    disp.set_buffers(buf, None, len(buf), lv.DISPLAY_RENDER_MODE.PARTIAL)
    disp.set_flush_cb(lambda d, area, px: d.flush_ready())
    from portfolio_app import PortfolioApp

    app = PortfolioApp(path)
    app.start()
    pump()
    n = len(app.pages)
    for expect in list(range(1, n)) + [0]:
        app.btn_next.send_event(lv.EVENT.CLICKED, None)
        pump()
        if app.index != expect:
            fail("next-click landed on page %d, expected %d" % (app.index + 1, expect + 1))
        if app.lbl_title.get_text() != app.pages[app.index][0]:
            fail("header title %r != content title %r" % (app.lbl_title.get_text(), app.pages[app.index][0]))
    print("nav ring forward: all %d pages reachable by next-button" % n)
    for expect in [n - 1] + list(range(n - 2, -1, -1)):
        app.btn_prev.send_event(lv.EVENT.CLICKED, None)
        pump()
        if app.index != expect:
            fail("prev-click landed on page %d, expected %d" % (app.index + 1, expect + 1))
    print("nav ring backward: all %d pages reachable by prev-button" % n)
    before = app.index
    app.scr.send_event(lv.EVENT.GESTURE, None)
    pump()
    if app.index != before:
        fail("gesture with no indev changed the page")
    for i in range(n):
        app.show_page(i)
        pump()
        targets = clickables(app.content, [])
        for t in targets:
            t.send_event(lv.EVENT.PRESSED, None)
            t.send_event(lv.EVENT.CLICKED, None)
            t.send_event(lv.EVENT.RELEASED, None)
        pump()
        gc.collect()
        print("page %-2d %-14s: %d clickables poked" % (i + 1, app.pages[i][0], len(targets)))


audit_api()
try:
    walk_app(sys.argv[1] if len(sys.argv) > 1 else "portfolio.txt")
except Exception as e:
    fail("interaction walk aborted: %s: %s" % (type(e).__name__, e))
    sys.print_exception(e)
print("---")
print("%d failure(s)" % failures)
sys.exit(1 if failures else 0)
