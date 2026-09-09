# Frozen flat-module build of portfolio/pages/p03_skills.py (see apps/portfolio/ for the
# filesystem-installable package variant; keep the two in sync).
# Skill meters: staggered horizontal bars for every (name, level) in
# data["skills"], grouped into two sections.

import lvgl as lv
import portfolio_theme as theme

TITLE = "Skills"

_COLORS = (theme.ACCENT, theme.ACCENT_2, theme.ACCENT_3, theme.GOOD)


def build(parent, ctx):
    col = theme.column(parent, gap=8)
    skills = ctx["data"]["skills"]
    bars = []  # (bar, target value), filled in build order

    def section(heading, items):
        theme.title(col, heading)
        c = theme.card(col)
        c.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        c.set_style_pad_row(8, 0)
        for name, level in items:
            b = theme.hbar(c, name, level, _COLORS[len(bars) % len(_COLORS)])
            b.set_value(0, False)  # park at zero; the timer reveals it
            bars.append((b, level))

    section("Languages & frameworks", skills[:5])
    section("Also dangerous with", skills[5:])

    theme.label(col, "Self-assessed on shipped projects.",
                theme.FONT_S, theme.MUTED)

    # Reveal one bar per tick. Once every bar is animated the timer pauses
    # and never touches a widget again; the app deletes it on page leave.
    state = {"i": 0}

    def reveal(t):
        i = state["i"]
        if i >= len(bars):
            t.pause()
            return
        b, target = bars[i]
        b.set_value(target, True)
        state["i"] = i + 1

    ctx["app"].own_timer(lv.timer_create(reveal, 120, None))
