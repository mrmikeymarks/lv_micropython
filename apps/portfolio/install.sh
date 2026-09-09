#!/usr/bin/env bash

# Install the portfolio app onto a board already running lv_micropython
# firmware (see scripts/run-esp32-all.sh for building/flashing that).
#
# Usage:
#   install.sh [PORT] [--source]
#     PORT      defaults to the first /dev/cu.usbserial* device
#     --source  install plain .py files instead of cross-compiled .mpy
#               (easier to poke at on-device, but costs RAM: the on-device
#               compiler spikes the heap at every page import, which is
#               exactly what a no-PSRAM board can't afford)
#
# By default every module is cross-compiled to .mpy on the host and only
# the .mpy files are copied (a stray .py beside a .mpy would shadow it).
# main.py always ships as source - the boot script is run, not imported.

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MICROPYTHON="$(cd "$APP_DIR/../.." && pwd)"
MPY_CROSS="$MICROPYTHON/mpy-cross/build/mpy-cross"

PORT=""
MODE="mpy"
for arg in "$@"; do
    case "$arg" in
        --source) MODE="src" ;;
        *) PORT="$arg" ;;
    esac
done

if [ -z "$PORT" ]; then
    PORT="$(ls /dev/cu.usbserial* 2>/dev/null | head -1 || true)"
    if [ -z "$PORT" ]; then
        echo "ERROR: no /dev/cu.usbserial* device found. Plug the board in or pass a port." >&2
        exit 1
    fi
fi

MPREMOTE="python $MICROPYTHON/tools/mpremote/mpremote.py connect $PORT"

STAGE="$APP_DIR/.stage"
rm -rf "$STAGE"
mkdir -p "$STAGE"

if [ "$MODE" = "mpy" ]; then
    if [ ! -x "$MPY_CROSS" ]; then
        echo "=== Building mpy-cross (first run only) ==="
        make -C "$MICROPYTHON/mpy-cross"
    fi
    echo "=== Cross-compiling portfolio to .mpy ==="
    (cd "$APP_DIR" && find portfolio -name '*.py') | while read -r f; do
        mkdir -p "$STAGE/$(dirname "$f")"
        "$MPY_CROSS" -o "$STAGE/${f%.py}.mpy" "$APP_DIR/$f"
    done
else
    echo "=== Staging portfolio sources ==="
    (cd "$APP_DIR" && find portfolio -name '*.py') | while read -r f; do
        mkdir -p "$STAGE/$(dirname "$f")"
        cp "$APP_DIR/$f" "$STAGE/$f"
    done
fi

echo "=== Installing to $PORT ==="
cd "$STAGE"
$MPREMOTE fs cp "$APP_DIR/main.py" :main.py
$MPREMOTE fs cp -r portfolio :
cd "$APP_DIR"
rm -rf "$STAGE"

echo "=== Resetting board ==="
$MPREMOTE reset
echo "Done. The portfolio starts on boot; swipe or use the header arrows."
