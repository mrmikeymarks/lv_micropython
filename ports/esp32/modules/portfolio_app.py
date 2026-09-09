# Frozen build of portfolio/app.py: pages live in the
# portfolio_pages/ subpackage, theme/data as flat siblings (see
# apps/portfolio/ for the filesystem variant; keep in sync).
# Portfolio shell: header bar with prev/next navigation, page counter, and a
# content area that hosts exactly one lazily-imported page at a time.

import sys
import gc

import lvgl as lv

import portfolio_theme as theme
from portfolio_pages import PAGES

HEADER_H = 32


class PortfolioApp:
    def __init__(self, data, hor_res=320, ver_res=240):
        theme.init()
        self.data = data
        self.index = 0
        self._page_mod = None
        self._timers = []
        self._cleanups = []

        self.scr = lv.obj()
        self.scr.set_style_bg_color(theme.BG, 0)
        self.scr.set_style_bg_opa(lv.OPA.COVER, 0)
        self.scr.set_style_pad_all(0, 0)
        self.scr.set_style_border_width(0, 0)
        self.scr.remove_flag(lv.obj.FLAG.SCROLLABLE)

        self._build_header(hor_res)

        content = lv.obj(self.scr)
        content.set_pos(0, HEADER_H)
        content.set_size(hor_res, ver_res - HEADER_H)
        content.set_style_bg_opa(lv.OPA.TRANSP, 0)
        content.set_style_border_width(0, 0)
        content.set_style_radius(0, 0)
        content.set_style_pad_all(8, 0)
        content.set_scroll_dir(lv.DIR.VER)
        content.set_scrollbar_mode(lv.SCROLLBAR_MODE.ACTIVE)
        self.content = content

        # Swipe left/right anywhere to change pages (buttons work too).
        self.scr.add_event_cb(self._on_gesture, lv.EVENT.GESTURE, None)

    def _build_header(self, hor_res):
        bar = lv.obj(self.scr)
        bar.set_pos(0, 0)
        bar.set_size(hor_res, HEADER_H)
        bar.set_style_bg_color(theme.SURFACE, 0)
        bar.set_style_bg_opa(lv.OPA.COVER, 0)
        bar.set_style_border_width(0, 0)
        bar.set_style_radius(0, 0)
        bar.set_style_pad_all(0, 0)
        bar.remove_flag(lv.obj.FLAG.SCROLLABLE)

        self.btn_prev = self._nav_button(bar, lv.SYMBOL.LEFT, lv.ALIGN.LEFT_MID, -1)
        self.btn_next = self._nav_button(bar, lv.SYMBOL.RIGHT, lv.ALIGN.RIGHT_MID, 1)

        self.lbl_title = theme.label(bar, "", theme.FONT_M, theme.TEXT)
        self.lbl_title.align(lv.ALIGN.CENTER, 0, 0)

        self.lbl_count = theme.label(bar, "", theme.FONT_S, theme.MUTED)
        self.lbl_count.align(lv.ALIGN.RIGHT_MID, -44, 0)

    def _nav_button(self, parent, symbol, align, step):
        btn = lv.button(parent)
        btn.set_size(40, HEADER_H)
        btn.align(align, 0, 0)
        btn.set_style_bg_color(theme.SURFACE, 0)
        btn.set_style_bg_color(theme.SURFACE_2, lv.STATE.PRESSED)
        btn.set_style_radius(0, 0)
        btn.set_style_shadow_width(0, 0)
        lbl = theme.label(btn, symbol, theme.FONT_M, theme.ACCENT)
        lbl.center()
        btn.add_event_cb(lambda e, s=step: self.step(s), lv.EVENT.CLICKED, None)
        return btn

    # -- page lifecycle ----------------------------------------------------

    def start(self):
        lv.screen_load(self.scr)
        self.show_page(0)

    def step(self, delta):
        self.show_page((self.index + delta) % len(PAGES))

    def _teardown(self, name):
        # Timers first (they may reference widgets), then widgets, then the
        # page module itself.
        for t in self._timers:
            t.delete()
        self._timers = []
        for fn in self._cleanups:
            fn()
        self._cleanups = []
        self.content.clean()
        sys.modules.pop("portfolio_pages." + name, None)
        # The import also bound the module as an attribute of the pages
        # package; without dropping that too, every visited page stays
        # pinned on the heap.
        pages_pkg = sys.modules.get("portfolio_pages")
        if pages_pkg is not None:
            try:
                delattr(pages_pkg, name)
            except (AttributeError, KeyError):
                # not imported yet; MicroPython raises KeyError here
                pass
        self._page_mod = None
        gc.collect()

    def show_page(self, index):
        self._teardown(PAGES[self.index][0])

        self.index = index
        name, fallback_title = PAGES[index]
        self.content.scroll_to_y(0, False)
        try:
            # Pre-build guard: with less than ~24KB free even a mid-sized
            # page would land in GC-thrash territory; refuse fast instead
            # of letting every animation tick crawl.
            if gc.mem_free() < 24576:
                raise MemoryError
            mod = __import__("portfolio_pages." + name, None, None, (name,))
            self._page_mod = mod
            ctx = {
                "app": self,
                "data": self.data,
                "index": index,
                "count": len(PAGES),
            }
            mod.build(self.content, ctx)
            # A page that fits but leaves no working headroom would make the
            # whole UI crawl (every tick becomes a full GC); degrade instead.
            gc.collect()
            if gc.mem_free() < 12288:
                raise MemoryError
            title = getattr(mod, "TITLE", fallback_title)
        except MemoryError:
            # A page too big for what's left of the heap must not take the
            # whole app down; recover to a navigable error notice. Full
            # teardown: the page may have registered timers before failing.
            self._teardown(name)
            note = theme.label(self.content,
                               "not enough memory\nfor this page",
                               theme.FONT_M, theme.WARN)
            note.center()
            title = fallback_title

        self.lbl_title.set_text(title)
        self.lbl_count.set_text("%d/%d" % (index + 1, len(PAGES)))

    # -- helpers for pages -------------------------------------------------

    def own_timer(self, timer):
        """Pages register lv timers here; deleted on page change."""
        self._timers.append(timer)
        return timer

    def on_leave(self, fn):
        """Extra cleanup hook run when the page is torn down."""
        self._cleanups.append(fn)

    # -- input -------------------------------------------------------------

    def _on_gesture(self, e):
        indev = lv.indev_active()
        if not indev:
            return
        d = indev.get_gesture_dir()
        if d == lv.DIR.LEFT:
            self.step(1)
        elif d == lv.DIR.RIGHT:
            self.step(-1)
