#!/usr/bin/env bash

# Run an LVGL demo on the desktop simulator (unix port + SDL window).
# Builds ports/unix/build-lvgl/micropython on first use (~5-10 min once).
#
# Usage:
#   sim.sh demos/hello_touch.py
#   sim.sh                # just start a REPL with lvgl available
#
# The SDL window stands in for the ILI9341; the mouse stands in for touch.
# Same LVGL version (9.3) and color depth as the ESP32 firmware.

set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MICROPYTHON="$(dirname "$SCRIPTS_DIR")"
BIN="$MICROPYTHON/ports/unix/build-lvgl/micropython"

if [ ! -x "$BIN" ]; then
    echo "=== first run: building the desktop simulator (unix port, VARIANT=lvgl) ==="
    make -C "$MICROPYTHON/mpy-cross"
    make -C "$MICROPYTHON/ports/unix" submodules VARIANT=lvgl
    make -C "$MICROPYTHON/ports/unix" VARIANT=lvgl
fi

if [ $# -ge 1 ]; then
    exec "$BIN" "$@"
else
    exec "$BIN"
fi
