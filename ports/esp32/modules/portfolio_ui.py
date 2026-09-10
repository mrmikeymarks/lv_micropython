# Portfolio rendering engine: theme + one renderer per element kind.
#
# Pages are plain text (see apps/portfolio/portfolio.txt for the format):
# one element per line, "kind | field | field ...", at most MAX_ELEMENTS
# per page. render_page() turns a page's lines into widgets, top to bottom.
# The engine is the only thing that needs to be frozen; content lives on
# the filesystem and is streamed one page at a time.

import lvgl as lv

MAX_ELEMENTS = 7

# ---- palette / fonts ---------------------------------------------------

BG = lv.color_hex(0x10141B)
SURFACE = lv.color_hex(0x1B222D)
SURFACE_2 = lv.color_hex(0x27303E)
BORDER = lv.color_hex(0x39465A)
ACCENT = lv.color_hex(0x2EC4B6)
ACCENT_2 = lv.color_hex(0xFFA630)
ACCENT_3 = lv.color_hex(0x8F6BFF)
GOOD = lv.color_hex(0x5DD39E)
WARN = lv.color_hex(0xFFC145)
TEXT = lv.color_hex(0xEAF0F6)
MUTED = lv.color_hex(0x93A1B5)
CYCLE = (ACCENT, ACCENT_2, ACCENT_3, GOOD)

FONT_S = lv.font_montserrat_14
FONT_M = lv.font_montserrat_16
FONT_L = lv.font_montserrat_24

STYLE_CARD = None
STYLE_CHIP = None


def init():
    global STYLE_CARD, STYLE_CHIP
    if STYLE_CARD is not None:
        return
    STYLE_CARD = lv.style_t()
    STYLE_CARD.init()
    STYLE_CARD.set_bg_color(SURFACE)
    STYLE_CARD.set_bg_opa(lv.OPA.COVER)
    STYLE_CARD.set_radius(8)
    STYLE_CARD.set_border_width(1)
    STYLE_CARD.set_border_color(BORDER)
    STYLE_CARD.set_pad_all(8)
    STYLE_CARD.set_width(lv.pct(100))
    STYLE_CARD.set_height(lv.SIZE_CONTENT)
    STYLE_CHIP = lv.style_t()
    STYLE_CHIP.init()
    STYLE_CHIP.set_bg_color(SURFACE_2)
    STYLE_CHIP.set_bg_opa(lv.OPA.COVER)
    STYLE_CHIP.set_radius(10)
    STYLE_CHIP.set_border_width(0)
    STYLE_CHIP.set_pad_hor(8)
    STYLE_CHIP.set_pad_ver(3)


# ---- small builders ----------------------------------------------------

def bare(obj):
    obj.set_style_bg_opa(lv.OPA.TRANSP, 0)
    obj.set_style_border_width(0, 0)
    obj.set_style_pad_all(0, 0)
    obj.set_style_radius(0, 0)
    obj.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return obj


def label(parent, text, font=FONT_S, color=TEXT):
    l = lv.label(parent)
    l.set_text(text)
    l.set_style_text_font(font, 0)
    l.set_style_text_color(color, 0)
    return l


def wrapped(parent, text, font=FONT_S, color=TEXT):
    l = label(parent, text, font, color)
    l.set_long_mode(lv.label.LONG_MODE.WRAP)
    l.set_width(lv.pct(100))
    return l


def row(parent, gap=6):
    r = bare(lv.obj(parent))
    r.set_width(lv.pct(100))
    r.set_height(lv.SIZE_CONTENT)
    r.set_flex_flow(lv.FLEX_FLOW.ROW)
    r.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
    r.set_style_pad_column(gap, 0)
    return r


def column(parent, gap=6):
    c = bare(lv.obj(parent))
    c.set_width(lv.pct(100))
    c.set_height(lv.SIZE_CONTENT)
    c.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    c.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.START)
    c.set_style_pad_row(gap, 0)
    return c


def wrap_row(parent, gap=6):
    r = row(parent, gap)
    r.set_flex_flow(lv.FLEX_FLOW.ROW_WRAP)
    r.set_style_pad_row(gap, 0)
    return r


def card(parent):
    c = lv.obj(parent)
    c.add_style(STYLE_CARD, 0)
    c.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return c


def chip(parent, text, color=ACCENT):
    c = lv.obj(parent)
    c.add_style(STYLE_CHIP, 0)
    c.set_size(lv.SIZE_CONTENT, lv.SIZE_CONTENT)
    c.remove_flag(lv.obj.FLAG.SCROLLABLE)
    label(c, text, FONT_S, color)
    return c


def bar(parent, value, color, height=6):
    b = lv.bar(parent)
    b.set_height(height)
    b.set_range(0, 100)
    b.set_style_bg_color(SURFACE_2, lv.PART.MAIN)
    b.set_style_bg_opa(lv.OPA.COVER, lv.PART.MAIN)
    b.set_style_radius(3, lv.PART.MAIN)
    b.set_style_bg_color(color, lv.PART.INDICATOR)
    b.set_style_bg_opa(lv.OPA.COVER, lv.PART.INDICATOR)
    b.set_style_radius(3, lv.PART.INDICATOR)
    b.set_value(value, True)  # anim enable is a plain bool in this binding
    return b


def dot(parent, size, color):
    d = lv.obj(parent)
    d.set_size(size, size)
    d.set_style_radius(lv.RADIUS_CIRCLE, 0)
    d.set_style_bg_color(color, 0)
    d.set_style_bg_opa(lv.OPA.COVER, 0)
    d.set_style_border_width(0, 0)
    d.set_style_pad_all(0, 0)
    d.remove_flag(lv.obj.FLAG.SCROLLABLE)
    return d


def symbol(name):
    return getattr(lv.SYMBOL, name, lv.SYMBOL.OK)


def split_kv(item, sep=":"):
    """'SYMBOL:text' -> ('SYMBOL', 'text'); splits on the FIRST sep only."""
    k, _, v = item.partition(sep)
    return k.strip(), v.strip()


def to_int(s, default=0):
    try:
        return int(s)
    except ValueError:
        return default


# ---- element renderers: f(parent, fields, ctx) ---------------------------
# ctx: {"i": element index, "next": next element's kind or None,
#       "cycle": running color index}

def _color(ctx):
    c = CYCLE[ctx["cycle"] % len(CYCLE)]
    ctx["cycle"] += 1
    return c


def el_hero(parent, f, ctx):
    name, role, tagline = (f + ["", "", ""])[:3]
    col = column(parent, 4)
    col.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
    hero = row(col, 10)
    hero.set_width(lv.SIZE_CONTENT)
    av = dot(hero, 40, ACCENT)
    parts = name.replace("-", " ").replace("_", " ").split()
    ini = (parts[0][0] + parts[1][0]).upper() if len(parts) >= 2 else name[:2].upper()
    label(av, ini, FONT_M, BG).center()
    who = column(hero, 0)
    who.set_width(lv.SIZE_CONTENT)
    label(who, name, FONT_L, TEXT)
    label(who, role, FONT_S, MUTED)
    rule = bar(col, 100, ACCENT, 3)
    rule.set_width(120)
    rule.set_style_anim_duration(700, 0)
    if tagline:
        t = wrapped(col, tagline, FONT_S, TEXT)
        t.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)


def el_stats(parent, f, ctx):
    r = row(parent, 6)
    for item in f:
        value, name = split_kv(item)
        tile = card(r)
        tile.set_flex_grow(1)
        tile.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        tile.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        tile.set_style_pad_row(0, 0)
        tile.set_style_pad_ver(4, 0)
        label(tile, value, FONT_M, ACCENT)
        label(tile, name, FONT_S, MUTED)


def el_hint(parent, f, ctx):
    r = row(parent, 8)
    r.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
    label(r, lv.SYMBOL.LEFT, FONT_S, MUTED)
    label(r, f[0] if f else "", FONT_S, MUTED)
    label(r, lv.SYMBOL.RIGHT, FONT_S, MUTED)


def el_title(parent, f, ctx):
    r = row(parent, 6)
    tick = lv.obj(r)
    tick.set_size(4, 16)
    tick.set_style_bg_color(ACCENT, 0)
    tick.set_style_bg_opa(lv.OPA.COVER, 0)
    tick.set_style_radius(2, 0)
    tick.set_style_border_width(0, 0)
    label(r, f[0] if f else "", FONT_M, TEXT)


def el_text(parent, f, ctx):
    wrapped(card(parent), " | ".join(f), FONT_S, TEXT)


def el_muted(parent, f, ctx):
    wrapped(parent, " | ".join(f), FONT_S, MUTED)


def el_list(parent, f, ctx):
    col = column(parent, 4)
    for item in f:
        sym, text = split_kv(item)
        r = row(col, 8)
        label(r, symbol(sym), FONT_S, ACCENT_2)
        t = wrapped(r, text, FONT_S, TEXT)
        t.set_flex_grow(1)
        t.set_width(0)  # let flex-grow decide; wrap within it


def el_meters(parent, f, ctx):
    c = card(parent)
    c.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    c.set_style_pad_row(8, 0)
    for item in f:
        name, val = item.rpartition(":")[0].strip(), to_int(item.rpartition(":")[2])
        r = row(c, 8)
        n = label(r, name, FONT_S, TEXT)
        n.set_width(110)
        n.set_long_mode(lv.label.LONG_MODE.DOTS)
        b = bar(r, val, _color(ctx))
        b.set_flex_grow(1)
        v = label(r, "%d%%" % val, FONT_S, MUTED)
        v.set_width(40)
        v.set_style_text_align(lv.TEXT_ALIGN.RIGHT, 0)


def el_chips(parent, f, ctx):
    if f:
        el_title(parent, f[:1], ctx)
    color = _color(ctx)
    w = wrap_row(parent, 6)
    for item in f[1:]:
        chip(w, item, color)


def el_card(parent, f, ctx):
    name, body, tags, stars = (f + ["", "", "", "0"])[:4]
    c = card(parent)
    c.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    c.set_style_pad_row(6, 0)
    label(c, name, FONT_M, TEXT)
    wrapped(c, body, FONT_S, MUTED)
    r = row(c, 4)
    for t in tags.split(","):
        if t.strip():
            chip(r, t.strip(), ACCENT)
    sp = bare(lv.obj(r))
    sp.set_flex_grow(1)
    sp.set_height(1)
    n = min(max(to_int(stars), 0), 5)
    for i in range(5):
        dot(r, 8, ACCENT_2 if i < n else SURFACE_2)


def el_step(parent, f, ctx):
    period, role, org, desc = (f + ["", "", "", ""])[:4]
    r = row(parent, 8)
    r.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.START)
    gutter = column(r, 0)
    gutter.set_width(12)
    gutter.set_height(lv.pct(100))
    gutter.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
    dot(gutter, 10, ACCENT if ctx["first_step"] else BORDER)
    ctx["first_step"] = False
    if ctx["next"] == "step":
        line = lv.obj(gutter)
        line.set_size(2, lv.pct(100))
        line.set_style_bg_color(SURFACE_2, 0)
        line.set_style_bg_opa(lv.OPA.COVER, 0)
        line.set_style_border_width(0, 0)
        line.set_flex_grow(1)
    c = card(r)
    c.set_flex_grow(1)
    c.set_width(0)
    c.set_flex_flow(lv.FLEX_FLOW.COLUMN)
    c.set_style_pad_row(2, 0)
    label(c, period, FONT_S, ACCENT_2)
    label(c, role, FONT_M, TEXT)
    label(c, org, FONT_S, MUTED)
    wrapped(c, desc, FONT_S, MUTED)


def el_chart(parent, f, ctx):
    values = [to_int(v) for v in (f[0] if f else "").split(",") if v.strip()]
    labels = [s.strip() for s in (f[1] if len(f) > 1 else "").split(",")]
    c = card(parent)
    c.set_style_pad_all(4, 0)
    ch = lv.chart(c)
    ch.set_size(lv.pct(100), 100)
    ch.set_type(lv.chart.TYPE.BAR)
    ch.set_point_count(len(values))
    ch.set_axis_range(lv.chart.AXIS.PRIMARY_Y, 0, max(values) if values else 1)
    ch.set_div_line_count(0, 0)
    ch.set_style_bg_opa(lv.OPA.TRANSP, 0)
    ch.set_style_border_width(0, 0)
    ch.set_style_pad_column(4, lv.PART.ITEMS)
    ser = ch.add_series(ACCENT, lv.chart.AXIS.PRIMARY_Y)
    for v in values:
        ch.set_next_value(ser, v)
    if labels and labels[0]:
        r = row(parent, 0)
        r.set_flex_align(lv.FLEX_ALIGN.SPACE_BETWEEN, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        for s in labels:
            label(r, s, FONT_S, MUTED)


_MEDIA_COLORS = {"VIDEO": ACCENT, "AUDIO": ACCENT_3, "FILE": ACCENT_2, "IMAGE": GOOD}


def el_media(parent, f, ctx):
    sym, kind, title, year = (f + ["FILE", "", "", ""])[:4]
    c = card(parent)
    c.set_flex_flow(lv.FLEX_FLOW.ROW)
    c.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
    c.set_style_pad_column(8, 0)
    badge = bare(lv.obj(c))
    badge.set_size(32, 32)
    badge.set_style_bg_color(SURFACE_2, 0)
    badge.set_style_bg_opa(lv.OPA.COVER, 0)
    badge.set_style_radius(6, 0)
    label(badge, symbol(sym), FONT_M, _MEDIA_COLORS.get(sym, ACCENT)).center()
    col = column(c, 2)
    col.set_flex_grow(1)
    col.set_width(0)
    wrapped(col, title, FONT_S, TEXT)
    label(col, "%s - %s" % (kind, year), FONT_S, MUTED)


def el_grid(parent, f, ctx):
    w = wrap_row(parent, 8)
    for item in f:
        sym, rest = split_kv(item)
        name, level = rest.rpartition(":")[0].strip(), to_int(rest.rpartition(":")[2])
        color = _color(ctx)
        t = card(w)
        t.set_size(148, 86)  # 2 x 148 + 8 gap = 304 = usable width
        t.set_style_pad_hor(6, 0)
        t.set_style_pad_ver(10, 0)
        t.set_flex_flow(lv.FLEX_FLOW.COLUMN)
        t.set_flex_align(lv.FLEX_ALIGN.SPACE_BETWEEN, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
        label(t, symbol(sym), FONT_L, color)
        n = wrapped(t, name, FONT_S, TEXT)
        n.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
        b = bar(t, level, color, 4)
        b.set_width(lv.pct(100))


def el_qr(parent, f, ctx):
    url, caption = (f + ["", ""])[:2]
    col = column(parent, 4)
    col.set_flex_align(lv.FLEX_ALIGN.START, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
    holder = bare(lv.obj(col))
    holder.set_size(108, 108)
    holder.set_style_bg_color(TEXT, 0)
    holder.set_style_bg_opa(lv.OPA.COVER, 0)
    holder.set_style_radius(6, 0)
    qr = lv.qrcode(holder)
    qr.set_size(96)
    qr.set_dark_color(BG)
    qr.set_light_color(TEXT)
    qr.update(url, len(url))
    qr.center()
    if caption:
        label(col, caption, FONT_S, MUTED)


def el_footer(parent, f, ctx):
    r = row(parent, 6)
    r.set_flex_align(lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
    label(r, lv.SYMBOL.CHARGE, FONT_S, ACCENT)
    label(r, " | ".join(f), FONT_S, MUTED)


RENDERERS = {
    "hero": el_hero, "stats": el_stats, "hint": el_hint, "title": el_title,
    "text": el_text, "muted": el_muted, "list": el_list, "meters": el_meters,
    "chips": el_chips, "card": el_card, "step": el_step, "chart": el_chart,
    "media": el_media, "grid": el_grid, "qr": el_qr, "footer": el_footer,
}


# ---- page assembly -------------------------------------------------------

def parse(line):
    """'kind | a | b' -> ('kind', ['a', 'b']); None for blank/comment lines."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = [p.strip() for p in line.split("|")]
    return parts[0].lower(), parts[1:]


def render_page(parent, lines):
    """Build a page from its text lines. Unknown kinds and over-cap lines
    render as visible warnings instead of failing, so a typo in the content
    file never takes the app down."""
    init()
    parsed = [p for p in (parse(l) for l in lines) if p]
    col = column(parent, 8)
    ctx = {"cycle": 0, "first_step": True, "next": None, "i": 0}
    for i, (kind, fields) in enumerate(parsed[:MAX_ELEMENTS]):
        ctx["i"] = i
        ctx["next"] = parsed[i + 1][0] if i + 1 < len(parsed) else None
        fn = RENDERERS.get(kind)
        if fn is None:
            wrapped(col, "? unknown element: " + kind, FONT_S, WARN)
        else:
            fn(col, fields, ctx)
    if len(parsed) > MAX_ELEMENTS:
        wrapped(col, "! page has %d elements, max %d" % (len(parsed), MAX_ELEMENTS),
                FONT_S, WARN)
    return col
