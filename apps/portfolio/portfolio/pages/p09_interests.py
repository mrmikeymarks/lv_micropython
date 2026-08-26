# Interests page: 2-column grid of hobby tiles (symbol, label, and a thin
# enthusiasm bar each) from data["interests"], closed by the CTA line.

import lvgl as lv
from portfolio import theme

TITLE = "Interests"

_COLORS = (theme.ACCENT, theme.ACCENT_2, theme.ACCENT_3, theme.GOOD)

# 2 x 148 + 8 gap = 304 = full usable width of the content area
_TILE_W = 148
_TILE_H = 86


def _tile(parent, sym_name, text, level, color):
    t = theme.tile(parent, _TILE_W, _TILE_H)
    t.set_style_pad_hor(6, 0)  # narrow: "Home automation" needs the room
    t.set_style_pad_ver(10, 0)
    t.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    t.set_flex_align(lv.FLEX_ALIGN.SPACE_BETWEEN,
                     lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)

    theme.label(t, theme.symbol(sym_name), theme.FONT_L, color)
    lbl = theme.wrapped(t, text, theme.FONT_S, theme.TEXT)
    lbl.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)

    b = lv.bar(t)
    b.set_size(lv.pct(100), 4)
    b.set_range(0, 100)
    b.set_style_bg_color(theme.SURFACE_2, lv.PART.MAIN)
    b.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
    b.set_style_radius(2, lv.PART.MAIN)
    b.set_style_bg_color(color, lv.PART.INDICATOR)
    b.set_style_bg_opa(lv.OPA.COVER, lv.PART.INDICATOR)
    b.set_style_radius(2, lv.PART.INDICATOR)
    b.set_value(level, False)
    return t


def build(parent, ctx):
    col = theme.column(parent, gap=8)

    grid = theme.bare(lv.obj(col))
    grid.set_width(lv.pct(100))
    grid.set_height(lv.SIZE_CONTENT)
    grid.set_flex_flow(lv.FLEX_FLOW.ROW_WRAP)
    grid.set_style_pad_row(8, 0)
    grid.set_style_pad_column(8, 0)
    grid.remove_flag(lv.obj.FLAG.SCROLLABLE)

    for i, (sym, name, level) in enumerate(ctx["data"]["interests"]):
        _tile(grid, sym, name, level, _COLORS[i % len(_COLORS)])

    theme.wrapped(col, ctx["data"]["cta"], theme.FONT_S, theme.MUTED)
