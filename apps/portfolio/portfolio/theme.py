# Shared look-and-feel for all portfolio pages.
#
# Page contract (every module in portfolio/pages/):
#   TITLE = "Header title"            # shown in the top bar
#   def build(parent, ctx): ...       # create widgets under `parent`
#
# `parent` is a plain container sized to the content area (320x208 on the
# reference board), already scrollable vertically. `ctx` is a dict:
#   ctx["app"]    PortfolioApp - use app.own_timer(t) for any lv timer you
#                 create so it is deleted when the user leaves the page
#   ctx["data"]   the PORTFOLIO dict from portfolio/data.py
#   ctx["index"], ctx["count"]  current page number / page total
#
# Rules that keep pages working on a no-PSRAM ESP32:
#   - only fonts FONT_S / FONT_M / FONT_L below (montserrat 14/16/24)
#   - no image files; use lv.SYMBOL glyphs and drawn widgets
#   - keep it under ~70 lv objects per page
#   - never create lv.style_t inside build(); use the shared ones here or
#     per-object set_style_* locals

import lvgl as lv

# Palette - dark slate + teal/amber accents (RGB565-friendly hues)
BG = lv.color_hex(0x10141B)
SURFACE = lv.color_hex(0x1B222D)
SURFACE_2 = lv.color_hex(0x27303E)
BORDER = lv.color_hex(0x39465A)
ACCENT = lv.color_hex(0x2EC4B6)  # teal
ACCENT_2 = lv.color_hex(0xFFA630)  # amber
ACCENT_3 = lv.color_hex(0x8F6BFF)  # violet
GOOD = lv.color_hex(0x5DD39E)
WARN = lv.color_hex(0xFFC145)
TEXT = lv.color_hex(0xEAF0F6)
MUTED = lv.color_hex(0x93A1B5)

FONT_S = lv.font_montserrat_14
FONT_M = lv.font_montserrat_16
FONT_L = lv.font_montserrat_24

# Shared styles (created once; referenced from module scope so the GC keeps
# them alive for the lifetime of the app).
_inited = False
STYLE_CARD = None
STYLE_CHIP = None


def init():
    global _inited, STYLE_CARD, STYLE_CHIP
    if _inited:
        return
    _inited = True

    STYLE_CARD = lv.style_t()
    STYLE_CARD.init()
    STYLE_CARD.set_bg_color(SURFACE)
    STYLE_CARD.set_bg_opa(lv.OPA.COVER)
    STYLE_CARD.set_radius(8)
    STYLE_CARD.set_border_width(1)
    STYLE_CARD.set_border_color(BORDER)
    STYLE_CARD.set_pad_all(8)
    STYLE_CARD.set_width(lv.pct(100))
    STYLE_CARD.set_height(lv.SIZE_CONTENT)

    STYLE_CHIP = lv.style_t()
    STYLE_CHIP.init()
    STYLE_CHIP.set_bg_color(SURFACE_2)
    STYLE_CHIP.set_bg_opa(lv.OPA.COVER)
    STYLE_CHIP.set_radius(10)
    STYLE_CHIP.set_border_width(0)
    STYLE_CHIP.set_pad_hor(8)
    STYLE_CHIP.set_pad_ver(3)


def bare(obj):
    """Strip default lv.obj chrome: transparent, borderless, no padding."""
    obj.set_style_bg_opa(lv.OPA.TRANSP, 0)
    obj.set_style_border_width(0, 0)
    obj.set_style_pad_all(0, 0)
    obj.set_style_radius(0, 0)
    return obj


def label(parent, text, font=FONT_S, color=TEXT):
    l = lv.label(parent)
    l.set_text(text)
    l.set_style_text_font(font, 0)
    l.set_style_text_color(color, 0)
    return l


def wrapped(parent, text, font=FONT_S, color=TEXT, width=lv.pct(100)):
    """Long-text label that wraps instead of scrolling."""
    l = label(parent, text, font, color)
    l.set_long_mode(lv.label.LONG_MODE.WRAP)
    l.set_width(width)
    return l


def title(parent, text, color=ACCENT):
    """Section heading: accent tick + medium label, in a row."""
    r = row(parent)
    r.set_style_pad_column(6, 0)
    tick = lv.obj(r)
    tick.set_size(4, 16)
    tick.set_style_bg_color(color, 0)
    tick.set_style_bg_opa(lv.OPA.COVER, 0)
    tick.set_style_radius(2, 0)
    tick.set_style_border_width(0, 0)
    label(r, text, FONT_M, TEXT)
    return r


def card(parent):
    c = lv.obj(parent)
    c.add_style(STYLE_CARD, 0)
    c.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return c


def tile(parent, w, h):
    """Fixed-size card (the STYLE_CARD look without full-width sizing)."""
    t = lv.obj(parent)
    t.add_style(STYLE_CARD, 0)
    t.set_size(w, h)
    t.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return t


def symbol(name, fallback=None):
    """Resolve an lv.SYMBOL glyph from its name in data.py, safely."""
    return getattr(lv.SYMBOL, name, fallback or lv.SYMBOL.OK)


def row(parent, gap=6):
    """Transparent flex row that hugs its content height."""
    r = bare(lv.obj(parent))
    r.set_width(lv.pct(100))
    r.set_height(lv.SIZE_CONTENT)
    r.set_flex_flow(lv.FLEX_FLOW.ROW)
    r.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
    r.set_style_pad_column(gap, 0)
    r.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return r


def column(parent, gap=6):
    """Transparent flex column, full width, content height."""
    c = bare(lv.obj(parent))
    c.set_width(lv.pct(100))
    c.set_height(lv.SIZE_CONTENT)
    c.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    c.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.START)
    c.set_style_pad_row(gap, 0)
    c.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return c


def chip(parent, text, color=ACCENT):
    """Small rounded tag, e.g. a tech name."""
    c = lv.obj(parent)
    c.add_style(STYLE_CHIP, 0)
    c.set_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT)
    c.remove_flag(lv.obj.FLAG.SCROLLABLE)
    label(c, text, FONT_S, color)
    return c


def hbar(parent, name, value, color=ACCENT, suffix="%"):
    """Single-line meter: 'name  [####--]  80%'. 4 objects per call - this
    is the hottest builder on the heaviest page, keep it lean."""
    r = row(parent, gap=8)
    n = label(r, name, FONT_S, TEXT)
    n.set_width(110)
    n.set_long_mode(lv.label.LONG_MODE.DOTS)
    b = lv.bar(r)
    b.set_height(6)
    b.set_flex_grow(1)
    b.set_range(0, 100)
    b.set_style_bg_color(SURFACE_2, lv.PART.MAIN)
    b.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
    b.set_style_radius(3, lv.PART.MAIN)
    b.set_style_bg_color(color, lv.PART.INDICATOR)
    b.set_style_bg_opa(lv.OPA.COVER, lv.PART.INDICATOR)
    b.set_style_radius(3, lv.PART.INDICATOR)
    b.set_value(value, True)  # anim enable is a plain bool in this binding
    v = label(r, "%d%s" % (value, suffix), FONT_S, MUTED)
    v.set_width(40)
    v.set_style_text_align(lv.TEXT_ALIGN.RIGHT, 0)
    return b
