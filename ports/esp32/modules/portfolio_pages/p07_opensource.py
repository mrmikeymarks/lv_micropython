# Frozen flat-module build of portfolio/pages/p07_opensource.py (see apps/portfolio/ for the
# filesystem-installable package variant; keep the two in sync).
# Open source: yearly contribution bar chart plus the short list of
# repos I actually touch, all data-driven from data.py's "oss" block.

import lvgl as lv
import portfolio_theme as theme

TITLE = "Open Source"


def _contrib_chart(parent, contribs):
    ch = lv.chart(parent)
    ch.set_width(lv.pct(100))
    ch.set_height(100)
    ch.set_type(lv.chart.TYPE.BAR)
    ch.set_point_count(len(contribs))
    top = ((max(contribs) + 19) // 10) * 10  # headroom above tallest bar
    ch.set_axis_range(lv.chart.AXIS.PRIMARY_Y, 0, top)
    ch.set_div_line_count(3, 0)  # horizontal guides only

    # SURFACE card look without theme.STYLE_CARD (charts draw their own frame)
    ch.set_style_bg_color(theme.SURFACE, lv.PART.MAIN)
    ch.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
    ch.set_style_border_width(0, lv.PART.MAIN)
    ch.set_style_radius(8, lv.PART.MAIN)
    ch.set_style_pad_all(8, lv.PART.MAIN)
    ch.set_style_line_color(theme.SURFACE_2, lv.PART.MAIN)  # muted div lines
    ch.set_style_line_width(1, lv.PART.MAIN)
    ch.set_style_pad_column(8, lv.PART.MAIN)  # gap between bars
    ch.set_style_radius(2, lv.PART.ITEMS)
    ch.remove_flag(lv.obj.FLAG.SCROLLABLE)

    ser = ch.add_series(theme.ACCENT, lv.chart.AXIS.PRIMARY_Y)
    for v in contribs:
        ch.set_next_value(ser, v)
    return ch


def build(parent, ctx):
    oss = ctx["data"]["oss"]
    col = theme.column(parent, gap=8)

    theme.title(col, "Contributions")
    _contrib_chart(col, oss["contribs"])

    years = theme.row(col)
    years.set_flex_align(lv.FLEX_ALIGN.SPACE_BETWEEN,
                         lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
    years.set_style_pad_hor(10, 0)  # roughly under the bar centers
    for y in oss["years"]:
        theme.label(years, y, theme.FONT_S, theme.MUTED)

    theme.title(col, "Repos I touch")
    card = theme.card(col)
    card.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    card.set_style_pad_row(8, 0)
    for repo, note in oss["repos"]:
        r = theme.row(card)
        theme.label(r, lv.SYMBOL.DIRECTORY, theme.FONT_S, theme.ACCENT)
        theme.label(r, repo, theme.FONT_S, theme.TEXT)
        n = theme.label(r, note, theme.FONT_S, theme.MUTED)
        n.set_flex_grow(1)  # takes leftover width, truncates if squeezed
        n.set_long_mode(lv.label.LONG_MODE.DOTS)
        n.set_style_text_align(lv.TEXT_ALIGN.RIGHT, 0)
