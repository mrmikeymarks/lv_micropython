# Developer Portfolio — LVGL 9.3 + MicroPython

A 10-page interactive developer portfolio that runs on a 320×240 ILI9341 +
XPT2046 touch module driven by an ESP32 — no PSRAM required. Navigate with
the header arrows or swipe left/right.

| # | Page | What it shows |
|---|------|---------------|
| 1 | Home | Name, role, tagline, quick stats |
| 2 | About | Bio and quick facts |
| 3 | Skills | Animated skill meters |
| 4 | Stack | Tool/tech chip clouds by category |
| 5 | Projects | Project cards with tech tags and ratings |
| 6 | Experience | Career timeline |
| 7 | Open Source | Contribution bar chart and repo list |
| 8 | Talks & Media | Talks, podcasts, and posts |
| 9 | Interests | Hobby tiles with enthusiasm meters |
| 10 | Contact | Email/site/GitHub + scannable QR code |

> **Frozen variant:** the same app also exists as flat frozen modules in
> `ports/esp32/modules/` (`portfolio_*.py` + `portfolio_pages/`), built into the firmware so no
> RAM is spent on bytecode. Boot it with a one-line filesystem `main.py`:
> `import portfolio_main` (starts immediately) or `import portfolio_launcher`
> (standby screen; the BOOT button on GPIO0 starts it — pin configurable,
> but not 13/25, those are the display/touch chip-selects). Keep the two
> variants in sync (each file's header says which source it derives from).

## Make it yours

All content lives in [portfolio/data.py](portfolio/data.py) — name, skills,
projects, links, everything. Edit that one file; no page code needs to
change. Icons are `lv.SYMBOL` names stored as strings.

## Run on hardware

Flash lv_micropython firmware first (drivers are frozen in):

```bash
./scripts/lvmp flash
```

Then install the app (from `apps/portfolio/`):

```bash
./install.sh
```

Wiring matches the repo default: `sck=19 mosi=18 miso=5`, display
`cs=13 dc=12 rst=4 bl=15`, touch `cs=25`, panel power on pin 14.
Different wiring or panel? Edit [main.py](main.py) — everything below the
driver setup is display-agnostic.

## Run headless (CI / desktop emulator)

Build the unix port with the LVGL binding (a stale build dir causes qstr
collisions — `make clean` first if the build was made without
`USER_C_MODULES`), then:

```bash
make -C ports/unix -j8 VARIANT=standard USER_C_MODULES=$PWD/user_modules
cd apps/portfolio && ../../ports/unix/build-standard/micropython sim_check.py
```

Two harnesses, both must exit 0:

- `sim_check.py` builds every page against a dummy display and reports
  object counts, build time, and heap cost per page (add a page number to
  test one). Run it with `-X heapsize=110k` to mirror a no-PSRAM ESP32.
- `emu_check.py` is the porting sweep: it resolves every `lv.*` name used
  anywhere in the app against the running LVGL 9 binding (so a v8-era name
  like `lv.btn` or `lv.scr_act` fails even on a line no test executes),
  greps for known v8 relic patterns, then click-walks the real prev/next
  buttons through the whole page ring both ways and fires click events on
  every clickable widget of every page.

This local binary is the reference implementation: it is built from the
same `lv_binding_micropython` checkout (LVGL 9.3) the ESP32 firmware is
built from, so what passes here is what runs on the device. The online
simulator (sim.lvgl.io, used by `scripts/lvmp share` for single-file
demos) is frozen at LVGL 9.0 and is **not** API-congruent — e.g. chart and
qrcode APIs differ — so it is not a verification target for this app.

## Memory budget (no-PSRAM boards)

Worst case measured in the emulator (framework + heaviest page + a
device-sized display buffer): ~80 KB. The app defends itself at runtime:
pages are refused with a "not enough memory" notice (still navigable)
rather than thrashing or crashing when headroom runs out.

- Check your board's budget: `mpremote exec "import gc; gc.collect(); print(gc.mem_free())"`
  right after boot. ≥ 100 KB free is comfortable; below that, freeze the
  app into the firmware instead of installing it to the filesystem: add
  `freeze("$(PORT_DIR)/../../apps/portfolio", "portfolio")` style entries
  to the board manifest so the bytecode lives in flash, not RAM.
- `install.sh` ships cross-compiled `.mpy` files by default, which avoids
  the on-device compiler's RAM spikes at every page import (use `--source`
  to install editable `.py` instead).

## Design notes

- **One page at a time.** Pages are imported lazily, built, then evicted
  from `sys.modules` on navigation, so a no-PSRAM board only ever holds one
  page's bytecode and widgets. Timers registered via `app.own_timer()` are
  deleted on page change.
- **Shared theme.** [portfolio/theme.py](portfolio/theme.py) holds the
  palette, the three Montserrat fonts compiled into the firmware (14/16/24),
  and small builders (`card`, `chip`, `hbar`, `title`, …) so pages stay
  short and consistent. The page contract is documented in its header.
- **ASCII + symbols only.** The compiled fonts cover ASCII plus LVGL's
  symbol glyphs — no other Unicode, hence dot ratings instead of ★.
