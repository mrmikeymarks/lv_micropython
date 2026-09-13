# Developer Portfolio — LVGL 9.3 + MicroPython

A swipeable multi-page portfolio for a 320×240 ILI9341 + XPT2046 touch
module on an ESP32 — no PSRAM required. Navigate with the header arrows or
swipe left/right.

**All content is one text file.** [portfolio.txt](portfolio.txt) is the
only thing you edit: one element per line, top to bottom, at most 7 per
page, `= Title` starts a page. It lives on the board's filesystem and is
streamed one page at a time, so changing your portfolio is `edit → lvmp
install` — no firmware rebuild, no compiler on the device.

```
= Skills
title  | Languages & frameworks
meters | MicroPython:92 | C / C++:88 | Python:90
muted  | Self-assessed on shipped projects.
```

The format reference (all 16 element kinds) is in the header of
`portfolio.txt` itself.

## Layout

| Where | File | Role |
|-------|------|------|
| firmware (frozen) | `ports/esp32/modules/portfolio_ui.py` | theme + one renderer per element kind |
| firmware (frozen) | `ports/esp32/modules/portfolio_app.py` | header/nav shell, streams pages from the file |
| firmware (frozen) | `ports/esp32/modules/portfolio_main.py` | entry: `import portfolio_main` starts it |
| firmware (frozen) | `ports/esp32/modules/portfolio_launcher.py` | optional: standby screen, BOOT button starts it |
| board filesystem | `/portfolio.txt` | your content |
| board filesystem | `/main.py` | one line: `import portfolio_main` (or `_launcher`) |

The whole engine is ~11 KB of frozen bytecode; the content is ~5 KB on the
filesystem and never occupies RAM beyond the page being shown.

## Run on hardware

```bash
lvmp flash                  # build + flash firmware (engine frozen in), installs content
lvmp install                # content only, after editing portfolio.txt
lvmp install --launcher     # boot to standby; BOOT button (GPIO0) starts it
```

Wiring lives in `ports/esp32/modules/hw_esp32.py`: `sck=19 mosi=18 miso=5`,
display `cs=13 dc=12 rst=4 bl=15`, panel power 14, touch `cs=33` with `T_IRQ` on 26.

## Check content before installing

Both harnesses run against the unix build of this repo (LVGL 9.3, same
binding as the firmware — `make -C ports/unix VARIANT=standard
USER_C_MODULES=$PWD/user_modules`), from `apps/portfolio/`:

- `sim_check.py [file] [page]` — lints the content (unknown element kinds,
  more than 7 per page, non-ASCII, unknown `lv.SYMBOL` names), then builds
  every page headless and reports objects, build time, heap cost, widgets
  spilling past the screen edge, and navigation wrap-around. To mirror a
  no-PSRAM board run it with `-X heapsize=120k` and `PORTFOLIO_MODULES`
  pointing at mpy-cross output of the engine: the emulator process is
  ~10 KB heavier than the board (harness bookkeeping) and loads the
  engine's bytecode into RAM, which the frozen firmware doesn't — so 120k
  here is a conservative stand-in for a 110 KB device heap.
- `emu_check.py [file]` — resolves every `lv.*` name in the engine against
  the running binding (catches v8-era API), then click-walks the real
  prev/next buttons through the page ring both ways and fires click events
  on every clickable widget.

## Memory and robustness

The engine keeps ≥24 KB free before building a page and ≥12 KB after;
otherwise it shows a "not enough memory" notice (still navigable) instead
of thrashing. Measure your board with
`mpremote exec "import gc; gc.collect(); print(gc.mem_free())"`.

The content file is treated as untrusted input (it was fuzzed with ~700
hostile files): any line endings or a BOM are accepted, non-ASCII bytes
render as `?` (the fonts — montserrat 14/16/24 — only have ASCII and
`lv.SYMBOL` glyphs), lines are capped at 400 bytes, numbers are clamped,
symbol names are vetted before lookup, each element shows at most a fixed
number of items (`+N more` beyond that), and a page whose estimated widget
count exceeds 90 is refused with a notice rather than letting LVGL run out
of memory mid-build (which crashes without a Python exception). Mistakes
always render as a visible warning label, never as a dead board.
