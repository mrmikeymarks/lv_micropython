# Frozen flat-module build of portfolio/pages/p04_stack.py (see apps/portfolio/ for the
# filesystem-installable package variant; keep the two in sync).
# Tool-stack page: grouped chip clouds of the hardware, firmware, and
# desktop tooling from data["stack"], one accent color per group.

import lvgl as lv
import portfolio_theme as theme

TITLE = "Stack"

_GROUP_COLORS = (theme.ACCENT, theme.ACCENT_2, theme.ACCENT_3, theme.GOOD)


def _chip_cloud(parent):
    """Full-width transparent wrap container for chips."""
    w = lv.obj(parent)
    w.set_style_bg_opa(lv.OPA.TRANSP, 0)
    w.set_style_border_width(0, 0)
    w.set_style_pad_all(0, 0)
    w.set_style_radius(0, 0)
    w.set_width(lv.pct(100))
    w.set_height(lv.SIZE_CONTENT)
    w.set_flex_flow(lv.FLEX_FLOW.ROW_WRAP)
    w.set_style_pad_row(6, 0)
    w.set_style_pad_column(6, 0)
    w.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return w


def build(parent, ctx):
    col = theme.column(parent, gap=8)

    for i, (group, items) in enumerate(ctx["data"]["stack"]):
        color = _GROUP_COLORS[i % len(_GROUP_COLORS)]
        theme.title(col, group, color)
        cloud = _chip_cloud(col)
        for item in items:
            theme.chip(cloud, item, color)
