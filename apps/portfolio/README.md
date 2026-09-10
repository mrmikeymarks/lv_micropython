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
display `cs=13 dc=12 rst=4 bl=15`, panel power 14, touch `cs=25`.

## Check content before installing

Both harnesses run against the unix build of this repo (LVGL 9.3, same
binding as the firmware — `make -C ports/unix VARIANT=standard
USER_C_MODULES=$PWD/user_modules`), from `apps/portfolio/`:

- `sim_check.py [file] [page]` — lints the content (unknown element kinds,
  more than 7 per page, non-ASCII, unknown `lv.SYMBOL` names), then builds
  every page headless and reports objects, build time, heap cost, widgets
  spilling past the screen edge, and navigation wrap-around. Run with
  `-X heapsize=110k` (and `PORTFOLIO_MODULES` pointing at mpy-cross output)
  to mirror a no-PSRAM board.
- `emu_check.py [file]` — resolves every `lv.*` name in the engine against
  the running binding (catches v8-era API), then click-walks the real
  prev/next buttons through the page ring both ways and fires click events
  on every clickable widget.

## Memory

The engine keeps ≥24 KB free before building a page and ≥12 KB after;
otherwise it shows a "not enough memory" notice (still navigable) instead
of thrashing. Measure your board with
`mpremote exec "import gc; gc.collect(); print(gc.mem_free())"`.
Fonts are montserrat 14/16/24, ASCII + `lv.SYMBOL` glyphs only.
