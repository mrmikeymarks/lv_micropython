# About page: bio paragraphs in a card, quick-fact rows with symbol icons,
# and a location footer row.

import lvgl as lv
from portfolio import theme

TITLE = "About"


def _fact_row(parent, symbol, text, icon_color, text_color):
    r = theme.row(parent, gap=10)
    icon = theme.label(r, symbol, theme.FONT_S, icon_color)
    icon.set_width(22)
    t = theme.label(r, text, theme.FONT_S, text_color)
    t.set_long_mode(lv.label.LONG_MODE.WRAP)
    t.set_flex_grow(1)
    return r


def build(parent, ctx):
    data = ctx["data"]
    col = theme.column(parent, gap=10)

    # Bio card: lead paragraph bright, the rest muted.
    card = theme.card(col)
    card.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    card.set_style_pad_row(8, 0)
    bio = data["bio"]
    theme.wrapped(card, bio[0], theme.FONT_S, theme.TEXT)
    for para in bio[1:]:
        theme.wrapped(card, para, theme.FONT_S, theme.MUTED)

    theme.title(col, "Quick facts")
    for sym_name, text in data["facts"]:
        _fact_row(col, theme.symbol(sym_name), text,
                  theme.ACCENT_2, theme.TEXT)

    # Location footer, set apart in the teal accent.
    loc = _fact_row(col, lv.SYMBOL.GPS, data["location"],
                    theme.ACCENT, theme.MUTED)
    loc.set_style_pad_top(4, 0)
