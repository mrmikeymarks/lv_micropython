# Frozen flat-module build of portfolio/pages/p05_projects.py (see apps/portfolio/ for the
# filesystem-installable package variant; keep the two in sync).
# Projects: one card per project with name, description, tech chips and a
# five-dot rating drawn from plain lv.objs (no unicode stars).

import lvgl as lv
import portfolio_theme as theme

TITLE = "Projects"


def _dot(parent, earned):
    d = lv.obj(parent)
    d.set_size(8, 8)
    d.set_style_radius(lv.RADIUS_CIRCLE, 0)
    d.set_style_border_width(0, 0)
    d.set_style_bg_color(theme.ACCENT_2 if earned else theme.SURFACE_2, 0)
    d.set_style_bg_opa(lv.OPA.COVER, 0)
    d.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return d


def build(parent, ctx):
    col = theme.column(parent, gap=8)

    for proj in ctx["data"]["projects"]:
        card = theme.card(col)
        card.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        card.set_style_pad_row(4, 0)

        theme.label(card, proj["name"], theme.FONT_M, theme.TEXT)
        theme.wrapped(card, proj["desc"], theme.FONT_S, theme.MUTED)

        bottom = theme.row(card, gap=4)
        bottom.set_style_pad_top(2, 0)
        for tech in proj["tech"]:
            theme.chip(bottom, tech, theme.ACCENT)

        spacer = lv.obj(bottom)
        spacer.set_style_bg_opa(lv.OPA.TRANSP, 0)
        spacer.set_style_border_width(0, 0)
        spacer.set_style_pad_all(0, 0)
        spacer.set_height(1)
        spacer.set_flex_grow(1)

        for i in range(5):
            _dot(bottom, i < proj["stars"])
