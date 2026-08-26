# Talks & Media: press list - one card per item with a colored symbol badge,
# a wrapped title, and a muted "kind - year" sub-line.

import lvgl as lv
from portfolio import theme

TITLE = "Talks & Media"

# Badge symbol color keyed by the symbol name stored in data.py.
_KIND_COLOR = {
    "VIDEO": theme.ACCENT,
    "AUDIO": theme.ACCENT_3,
    "FILE": theme.ACCENT_2,
    "IMAGE": theme.GOOD,
}


def _badge(parent, symbol_name):
    b = lv.obj(parent)
    b.set_size(32, 32)
    b.set_style_bg_color(theme.SURFACE_2, 0)
    b.set_style_bg_opa(lv.OPA.COVER, 0)
    b.set_style_radius(8, 0)
    b.set_style_border_width(0, 0)
    b.set_style_pad_all(0, 0)
    b.remove_flag(lv.obj.FLAG.SCROLLABLE)
    sym = theme.symbol(symbol_name, lv.SYMBOL.FILE)
    color = _KIND_COLOR.get(symbol_name, theme.ACCENT)
    icon = theme.label(b, sym, theme.FONT_M, color)
    icon.center()
    return b


def build(parent, ctx):
    col = theme.column(parent, gap=8)

    for symbol_name, kind, name, year in ctx["data"]["media"]:
        card = theme.card(col)
        card.set_flex_flow(lv.FLEX_FLOW.ROW)
        card.set_flex_align(
            lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER
        )
        card.set_style_pad_column(10, 0)

        _badge(card, symbol_name)

        body = theme.column(card, gap=2)
        body.set_flex_grow(1)  # take the width left of the badge
        theme.wrapped(body, name, theme.FONT_S, theme.TEXT)
        theme.label(body, "%s - %s" % (kind, year), theme.FONT_S, theme.MUTED)
