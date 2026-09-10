# Portfolio shell: header with prev/next, page counter, and a content area
# showing one page streamed from a plain-text content file. Nothing but the
# current page's few lines is ever in RAM; the engine (portfolio_ui) does
# the drawing. See apps/portfolio/portfolio.txt for the content format.

import gc

import lvgl as lv

import portfolio_ui as ui

HEADER_H = 32
DEFAULT_PATH = "/portfolio.txt"


class PortfolioApp:
    def __init__(self, path=DEFAULT_PATH, hor_res=320, ver_res=240):
        ui.init()
        self.path = path
        self.index = 0
        self.pages = self._scan()  # [(title, offset of first body line)]

        self.scr = lv.obj()
        self.scr.set_style_bg_color(ui.BG, 0)
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

        self.scr.add_event_cb(self._on_gesture, lv.EVENT.GESTURE, None)

    # -- content file ------------------------------------------------------

    def _scan(self):
        """One bounded pass over the file: page titles and body offsets.
        Any failure becomes a single explanatory page instead of a crash."""
        pages = []
        try:
            for nxt, text in ui.read_lines(self.path):
                if ui.is_header(text):
                    pages.append((ui.header_title(text), nxt))
            if not pages:
                return [("No pages", "muted | %s has no '= Title' page headers." % self.path)]
        except OSError:
            return [("No content", "muted | %s not found on the board. Copy it with: lvmp install"
                     % self.path)]
        except MemoryError:
            return [("No content", "muted | not enough memory to read %s" % self.path)]
        return pages

    def _page_lines(self, index):
        title, offset = self.pages[index]
        if isinstance(offset, str):
            return [offset]  # a synthetic explanatory page
        lines = []
        for nxt, text in ui.read_lines(self.path, offset):
            if ui.is_header(text):
                break
            lines.append(text)
            if len(lines) > ui.MAX_ELEMENTS + 8:
                break  # over-cap pages are reported by the engine; stop reading
        return lines

    # -- chrome ------------------------------------------------------------

    def _build_header(self, hor_res):
        bar = lv.obj(self.scr)
        bar.set_pos(0, 0)
        bar.set_size(hor_res, HEADER_H)
        bar.set_style_bg_color(ui.SURFACE, 0)
        bar.set_style_bg_opa(lv.OPA.COVER, 0)
        bar.set_style_border_width(0, 0)
        bar.set_style_radius(0, 0)
        bar.set_style_pad_all(0, 0)
        bar.remove_flag(lv.obj.FLAG.SCROLLABLE)
        self.btn_prev = self._nav_button(bar, lv.SYMBOL.LEFT, lv.ALIGN.LEFT_MID, -1)
        self.btn_next = self._nav_button(bar, lv.SYMBOL.RIGHT, lv.ALIGN.RIGHT_MID, 1)
        self.lbl_title = ui.label(bar, "", ui.FONT_M, ui.TEXT)
        self.lbl_title.set_long_mode(lv.label.LONG_MODE.DOTS)
        self.lbl_title.set_width(160)
        self.lbl_title.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
        self.lbl_title.align(lv.ALIGN.CENTER, 0, 0)
        self.lbl_count = ui.label(bar, "", ui.FONT_S, ui.MUTED)
        self.lbl_count.align(lv.ALIGN.RIGHT_MID, -44, 0)

    def _nav_button(self, parent, sym, align, step):
        btn = lv.button(parent)
        btn.set_size(40, HEADER_H)
        btn.align(align, 0, 0)
        btn.set_style_bg_color(ui.SURFACE, 0)
        btn.set_style_bg_color(ui.SURFACE_2, lv.STATE.PRESSED)
        btn.set_style_radius(0, 0)
        btn.set_style_shadow_width(0, 0)
        ui.label(btn, sym, ui.FONT_M, ui.ACCENT).center()
        btn.add_event_cb(lambda e, s=step: self.step(s), lv.EVENT.CLICKED, None)
        return btn

    # -- navigation --------------------------------------------------------

    def start(self):
        lv.screen_load(self.scr)
        self.show_page(0)

    def step(self, delta):
        self.show_page((self.index + delta) % len(self.pages))

    def show_page(self, index):
        self.content.clean()
        gc.collect()
        self.index = index
        self.content.scroll_to_y(0, False)
        try:
            # Refuse fast when even a small page would land in GC-thrash
            # territory, and again if the built page leaves no headroom.
            if gc.mem_free() < 24576:
                raise MemoryError
            ui.render_page(self.content, self._page_lines(index))
            gc.collect()
            if gc.mem_free() < 12288:
                raise MemoryError
        except MemoryError:
            self.content.clean()
            gc.collect()
            ui.label(self.content, "not enough memory\nfor this page",
                     ui.FONT_M, ui.WARN).center()
        self.lbl_title.set_text(self.pages[index][0])
        self.lbl_count.set_text("%d/%d" % (index + 1, len(self.pages)))

    def _on_gesture(self, e):
        indev = lv.indev_active()
        if not indev:
            return
        d = indev.get_gesture_dir()
        if d == lv.DIR.LEFT:
            self.step(1)
        elif d == lv.DIR.RIGHT:
            self.step(-1)
