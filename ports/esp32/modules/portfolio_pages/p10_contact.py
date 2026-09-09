# Frozen flat-module build of portfolio/pages/p10_contact.py (see apps/portfolio/ for the
# filesystem-installable package variant; keep the two in sync).
# Contact page: reach-me rows (email / website / github), a scannable QR
# code for the website, the call-to-action, and a build-credits footer.

import lvgl as lv
import portfolio_theme as theme

TITLE = "Contact"


def _contact_row(parent, symbol, text):
    r = theme.row(parent, gap=10)
    theme.label(r, symbol, theme.FONT_S, theme.ACCENT)
    theme.label(r, text, theme.FONT_S, theme.TEXT)
    return r


def build(parent, ctx):
    data = ctx["data"]
    col = theme.column(parent, gap=10)
    col.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER,
                       lv.FLEX_ALIGN.CENTER)

    theme.title(col, "Get in touch")

    # The three ways to reach me, grouped on one card.
    c = theme.card(col)
    c.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    c.set_style_pad_row(8, 0)
    _contact_row(c, lv.SYMBOL.ENVELOPE, data["email"])
    _contact_row(c, lv.SYMBOL.WIFI, data["website"])
    _contact_row(c, lv.SYMBOL.DIRECTORY, "@" + data["github"])

    # QR of the website on a light card: dark modules + quiet zone scan best.
    holder = lv.obj(col)
    holder.set_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT)
    holder.set_style_bg_color(theme.TEXT, 0)
    holder.set_style_bg_opa(lv.OPA.COVER, 0)
    holder.set_style_border_width(0, 0)
    holder.set_style_radius(6, 0)
    holder.set_style_pad_all(8, 0)
    holder.remove_flag(lv.obj.FLAG.SCROLLABLE)
    qr = lv.qrcode(holder)
    qr.set_size(96)
    qr.set_dark_color(theme.BG)
    qr.set_light_color(theme.TEXT)
    qr.update(data["website"], len(data["website"]))

    theme.label(col, "scan for the full story", theme.FONT_S, theme.MUTED)

    cta = theme.wrapped(col, data["cta"], theme.FONT_M, theme.TEXT,
                        lv.pct(92))
    cta.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)

    # Footer credit line.
    foot = theme.row(col, gap=8)
    foot.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER,
                        lv.FLEX_ALIGN.CENTER)
    theme.label(foot, lv.SYMBOL.CHARGE, theme.FONT_S, theme.ACCENT_2)
    theme.label(foot, "Built with LVGL 9.3 + MicroPython",
                theme.FONT_S, theme.MUTED)
