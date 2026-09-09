# Frozen flat-module build of portfolio/pages/p01_home.py (see apps/portfolio/ for the
# filesystem-installable package variant; keep the two in sync).
# Hero landing page: avatar badge, name/role/tagline, three stat tiles,
# and a swipe hint. One animated accent bar eases in under the name.

import lvgl as lv
import portfolio_theme as theme

TITLE = "Home"


def _initials(name):
    parts = name.replace("-", " ").replace("_", " ").split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return name[:2].upper()


def build(parent, ctx):
    data = ctx["data"]
    # Tight vertical budget: everything below must fit the 192px inner
    # viewport so the swipe hint is visible without scrolling.
    col = theme.column(parent, gap=4)
    col.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER,
                       lv.FLEX_ALIGN.CENTER)

    # Hero row: avatar badge next to name + role.
    hero = theme.row(col, gap=10)
    hero.set_width(lv.SIZE_CONTENT)
    av = lv.obj(hero)
    av.set_size(40, 40)
    av.set_style_radius(lv.RADIUS_CIRCLE, 0)
    av.set_style_bg_color(theme.ACCENT, 0)
    av.set_style_bg_opa(lv.OPA.COVER, 0)
    av.set_style_border_width(0, 0)
    av.set_style_pad_all(0, 0)
    av.remove_flag(lv.obj.FLAG.SCROLLABLE)
    ini = theme.label(av, _initials(data["name"]), theme.FONT_M, theme.BG)
    ini.center()
    who = theme.column(hero, gap=0)
    who.set_width(lv.SIZE_CONTENT)
    theme.label(who, data["name"], theme.FONT_L, theme.TEXT)
    theme.label(who, data["role"], theme.FONT_S, theme.MUTED)

    # Thin accent rule that eases in under the hero.
    rule = lv.bar(col)
    rule.set_size(120, 3)
    rule.set_range(0, 100)
    rule.set_style_bg_color(theme.SURFACE_2, lv.PART.MAIN)
    rule.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
    rule.set_style_radius(2, lv.PART.MAIN)
    rule.set_style_bg_color(theme.ACCENT, lv.PART.INDICATOR)
    rule.set_style_bg_opa(lv.OPA.COVER, lv.PART.INDICATOR)
    rule.set_style_radius(2, lv.PART.INDICATOR)
    rule.set_style_anim_duration(700, 0)
    rule.set_value(0, False)
    rule.set_value(100, True)

    tag = theme.wrapped(col, data["tagline"], theme.FONT_S, theme.TEXT,
                        lv.pct(100))
    tag.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)

    # Three stat tiles in a row.
    r = theme.row(col, gap=6)
    for name, value in data["stats"]:
        tile = theme.card(r)
        tile.set_flex_grow(1)
        tile.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        tile.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER,
                            lv.FLEX_ALIGN.CENTER)
        tile.set_style_pad_row(0, 0)
        tile.set_style_pad_ver(4, 0)
        theme.label(tile, value, theme.FONT_M, theme.ACCENT)
        theme.label(tile, name, theme.FONT_S, theme.MUTED)

    # Swipe hint.
    hint = theme.row(col, gap=8)
    hint.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER,
                        lv.FLEX_ALIGN.CENTER)
    theme.label(hint, lv.SYMBOL.LEFT, theme.FONT_S, theme.MUTED)
    theme.label(hint, "swipe", theme.FONT_S, theme.MUTED)
    theme.label(hint, lv.SYMBOL.RIGHT, theme.FONT_S, theme.MUTED)
