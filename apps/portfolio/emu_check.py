# Emulator sweep: catches LVGL v8-to-v9 porting mistakes and dead controls.
#
#   1. API audit - every `lv.<...>` attribute chain that appears anywhere in
#      the app source is resolved against the running LVGL 9 binding, so a
#      v8-era name (lv.btn, lv.scr_act, lv.ALIGN.IN_...) fails here even if
#      no test happens to execute that line. Known v8 relic patterns are
#      also grepped explicitly.
#   2. Interaction walk - drives the app the way a finger would: clicks the
#      real header prev/next buttons through the whole page ring (forward
#      and back), fires click events on every clickable widget of every
#      page, and pokes the gesture handler. Verifies the header title
#      tracks each page module's TITLE.
#
# Run from this directory with the unix lv_micropython binary:
#   ../../ports/unix/build-standard/micropython emu_check.py
# Exit code 0 = clean.

import sys
import gc

import lvgl as lv

if hasattr(lv, "init"):
    lv.init()

failures = 0


def fail(msg):
    global failures
    failures += 1
    print("FAIL", msg)


# --- 1. static API audit ---------------------------------------------------

V8_RELICS = (
    "lv.btn", "lv.scr_act", "lv.disp_drv", "lv.indev_drv", "scr_load(",
    "lv.task_handler", "set_style_local_", "lv.ALIGN.IN_", "get_act(",
    "lv.STATE.CHECKED_", "lv.btnmatrix", "lv.img(", "lv.img.",
    "clear_flag(",  # v9 renamed to remove_flag
)

SOURCES = (
    "main.py",
    "portfolio/theme.py",
    "portfolio/app.py",
    "portfolio/data.py",
    "portfolio/pages/__init__.py",
) + tuple("portfolio/pages/p%02d_%s.py" % (i + 1, n) for i, n in enumerate((
    "home", "about", "skills", "stack", "projects",
    "experience", "opensource", "media", "interests", "contact")))


def _ident(ch):
    return ch.isalpha() or ch.isdigit() or ch == "_"


def _chains(src):
    """Yield every dotted attribute chain rooted at `lv.` in the source.
    MicroPython's re has no finditer, so scan by hand."""
    i = 0
    while True:
        i = src.find("lv.", i)
        if i < 0:
            return
        if i > 0 and _ident(src[i - 1]):  # part of a longer name, e.g. mylv.
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
            if k < len(src) and src[k] == "." and k + 1 < len(src) \
                    and _ident(src[k + 1]):
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
        # Audit code, not prose: strip comments, and skip lines that probe
        # optional API themselves (hasattr-guarded, e.g. lv.init on ESP32).
        src = "\n".join(
            line.split("#", 1)[0] for line in src.split("\n")
            if "hasattr(lv" not in line)
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
                    fail("lv.%s not in this LVGL binding (used in %s)"
                         % (chain, path))
                    break
    print("api audit: %d distinct lv.* chains resolved" % len(checked))


# --- 2. interaction walk ---------------------------------------------------

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


def walk_app():
    disp = lv.display_create(320, 240)
    buf = bytearray(320 * 30 * 2)
    disp.set_buffers(buf, None, len(buf), lv.DISPLAY_RENDER_MODE.PARTIAL)
    disp.set_flush_cb(lambda d, area, px: d.flush_ready())

    from portfolio.app import PortfolioApp
    from portfolio.data import PORTFOLIO
    from portfolio.pages import PAGES

    app = PortfolioApp(PORTFOLIO)
    app.start()
    pump()

    n = len(PAGES)

    # Ring forward via the real next button, checking title wiring per page.
    for expect in list(range(1, n)) + [0]:
        app.btn_next.send_event(lv.EVENT.CLICKED, None)
        pump()
        if app.index != expect:
            fail("next-click landed on page %d, expected %d"
                 % (app.index + 1, expect + 1))
        want = getattr(app._page_mod, "TITLE", PAGES[app.index][1]) \
            if app._page_mod else PAGES[app.index][1]
        got = app.lbl_title.get_text()
        if got != want:
            fail("header title %r != page TITLE %r on page %d"
                 % (got, want, app.index + 1))
    print("nav ring forward: all %d pages reachable by next-button" % n)

    # And backwards.
    for expect in [n - 1] + list(range(n - 2, -1, -1)):
        app.btn_prev.send_event(lv.EVENT.CLICKED, None)
        pump()
        if app.index != expect:
            fail("prev-click landed on page %d, expected %d"
                 % (app.index + 1, expect + 1))
    print("nav ring backward: all %d pages reachable by prev-button" % n)

    # Gesture handler must be a no-op without a real input device.
    before = app.index
    app.scr.send_event(lv.EVENT.GESTURE, None)
    pump()
    if app.index != before:
        fail("gesture with no indev changed the page")

    # Click every clickable widget on every page; nothing may raise.
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
        print("page %-2d %-16s: %d clickables poked"
              % (i + 1, PAGES[i][0], len(targets)))


audit_api()
try:
    walk_app()
except Exception as e:
    fail("interaction walk aborted: %s: %s" % (type(e).__name__, e))
    sys.print_exception(e)

print("---")
print("%d failure(s)" % failures)
sys.exit(1 if failures else 0)
