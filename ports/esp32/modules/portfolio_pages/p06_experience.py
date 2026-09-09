# Frozen flat-module build of portfolio/pages/p06_experience.py (see apps/portfolio/ for the
# filesystem-installable package variant; keep the two in sync).
# Career timeline: one row per position with a gutter of dots joined by a
# vertical line on the left and a detail card (period/role/org/desc) on the right.

import lvgl as lv
import portfolio_theme as theme

TITLE = "Experience"

DOT = 10          # dot diameter; also the gutter flex-spacer width
DOT_Y = 11        # dot top offset, centers it on the card's period line
LINE_X = 4        # dot center (5) minus half the 2px line width
ROW_GAP = 12      # vertical space between cards (row pad_bottom, line-covered)


def _block(parent, w, h, color, radius):
    b = lv.obj(parent)
    b.set_size(w, h)
    b.set_style_bg_color(color, 0)
    b.set_style_bg_opa(lv.OPA.COVER, 0)
    b.set_style_border_width(0, 0)
    b.set_style_pad_all(0, 0)
    b.set_style_radius(radius, 0)
    return b


def build(parent, ctx):
    exp = ctx["data"]["experience"]
    n = len(exp)
    root = theme.column(parent, gap=0)

    stretch = []  # (row, line, y0): lines sized to the row after layout
    for i, (period, role, org, desc) in enumerate(exp):
        r = theme.row(root, gap=8)
        r.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.START,
                         lv.FLEX_ALIGN.START)
        last = i == n - 1
        if not last:
            r.set_style_pad_bottom(ROW_GAP, 0)

        # Gutter line + dot float over the row so they never disturb the
        # flex layout or the row's SIZE_CONTENT height.
        if not last:
            y0 = DOT_Y + DOT // 2 if i == 0 else 0
            line = _block(r, 2, DOT, theme.SURFACE_2, 0)
            line.add_flag(lv.obj.FLAG.FLOATING)
            line.set_pos(LINE_X, y0)
            stretch.append((r, line, y0))
        elif i > 0:
            # Incoming stub from the previous entry; nothing after the last dot.
            line = _block(r, 2, DOT_Y + DOT // 2, theme.SURFACE_2, 0)
            line.add_flag(lv.obj.FLAG.FLOATING)
            line.set_pos(LINE_X, 0)

        dot = _block(r, DOT, DOT, theme.ACCENT if i == 0 else theme.BORDER,
                     lv.RADIUS_CIRCLE)
        dot.add_flag(lv.obj.FLAG.FLOATING)
        dot.set_pos(0, DOT_Y)

        # Invisible flex spacer reserves the gutter width the floaters sit in.
        gap = lv.obj(r)
        gap.set_size(DOT, 1)
        gap.set_style_bg_opa(lv.OPA.TRANSP, 0)
        gap.set_style_border_width(0, 0)

        c = theme.card(r)
        c.set_flex_grow(1)
        c.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        c.set_style_pad_row(3, 0)
        theme.label(c, period, theme.FONT_S, theme.ACCENT_2)
        theme.wrapped(c, role, theme.FONT_M, theme.TEXT)
        theme.label(c, org, theme.FONT_S, theme.MUTED)
        theme.wrapped(c, desc, theme.FONT_S, theme.MUTED)

    # Cards wrap to different heights, so measure each row before running
    # the connecting line down to its bottom edge (through pad_bottom, so
    # consecutive segments meet exactly).
    root.update_layout()
    for r, line, y0 in stretch:
        line.set_height(r.get_height() - y0)
