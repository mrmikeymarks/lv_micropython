# LVGL UI demos — one file, three targets

Every demo in this folder is a single self-contained script that runs
unchanged in three places:

| Target | Command | What renders |
|---|---|---|
| Desktop simulator | `lvmp sim demos/hello_touch.py` | SDL window on the Mac, mouse = touch. LVGL **9.3** — identical to the firmware. First run builds the simulator once (~5-10 min). |
| ESP32 device | `dev.sh demos/hello_touch.py` | Pushed as `main.py`, board resets, serial output streams. Hardware wiring lives in the frozen `hw_esp32` module — demos never mention pins. |
| Online simulator (client links) | `lvmp share demos/hello_touch.py` | Prints a `sim.lvgl.io` URL that auto-loads the script from this public repo. No login. Openable on phones (desktop-width page — pinch-zoom). |

## Workflow

1. Edit the demo, iterate with `lvmp sim` (instant, no hardware).
2. Sanity-check on the device with `dev.sh` when it matters.
3. Commit + push, then `lvmp share` for a client link. SHA-pinned links
   never change behind a client's back; use `--branch` for a live link.

## The one rule: stay inside LVGL 9.0 APIs in shared demos

The online simulator is frozen at **LVGL 9.0.0 / MicroPython 1.20.0**
(every browser build in existence derives from one 2024 snapshot). The
desktop simulator and device run **LVGL 9.3**. Core widgets are identical
across 9.x (`lv.obj`, `lv.label`, `lv.button`, `lv.slider`, `lv.dropdown`,
`align`, `add_event_cb`, `lv.screen_load`, styles, flex/grid) — but
features introduced in 9.1–9.3 (e.g. `lv.lottie`, `lv.translation`,
`lv.xml`) will fail in the browser. Test the link once before sending it.

## How a demo file is structured

```python
def build_ui(): ...   # pure LVGL, 9.0-safe

# bootstrap (copy from hello_touch.py):
#   esp32         -> import hw_esp32; build_ui()
#   darwin/linux  -> SDL window + lv_utils.event_loop(asynchronous=True)
#                    + build_ui() + asyncio.Loop.run_forever()
#   web simulator -> import display_driver; build_ui()
```

Keep everything in one file — the online simulator's `?script=` loader
fetches exactly one URL.

## Known limitations

- The sim.lvgl.io page is a desktop IDE layout; on phones it renders at
  desktop width (pinch-zoom to the canvas). Touch input on phones is
  expected to work via SDL's touch-to-mouse mapping but should be verified
  per demo. A mobile-first self-hosted viewer is a possible phase 2.
- The sim's own "Save/share" button is broken upstream (expired TLS cert on
  its snippet backend since 2024) — only `?script=<raw URL>` links work,
  which is what `lvmp share` generates.
