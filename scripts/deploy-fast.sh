#!/usr/bin/env bash

# Fast deploy: flash an already-built firmware with esptool directly, skipping
# the make -> cmake -> idf.py wrapper chain (~10-15s of overhead per deploy).
# By default only the application region is written — the bootloader and
# partition table never change between builds, so reflashing them is wasted time.
#
# Usage:
#   deploy-fast.sh [BOARD] [PORT] [BAUD] [--full]
#
#   BOARD   defaults to ESP32_GENERIC (build dir must exist: run a build first)
#   PORT    defaults to the first /dev/cu.usbserial* device
#   BAUD    defaults to 921600
#   --full  also write bootloader + partition table (first flash of a blank
#           board, or after changing partition layout / IDF version)
#
# Rebuild first when code changed:  make -C ports/esp32 BOARD=... (or run-esp32-all.sh)

set -euo pipefail

FULL=0
ARGS=()
for a in "$@"; do
    if [ "$a" = "--full" ]; then FULL=1; else ARGS+=("$a"); fi
done

BOARD="${ARGS[0]:-ESP32_GENERIC}"
PORT="${ARGS[1]:-}"
BAUD="${ARGS[2]:-${BAUD:-921600}}"

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MICROPYTHON="$(dirname "$SCRIPTS_DIR")"
BUILD_DIR="$MICROPYTHON/ports/esp32/build-$BOARD"

if [ ! -f "$BUILD_DIR/micropython.bin" ]; then
    echo "ERROR: $BUILD_DIR/micropython.bin not found — build first (run-esp32-all.sh or make)." >&2
    exit 1
fi

if [ -z "$PORT" ]; then
    PORT="$(ls /dev/cu.usbserial* 2>/dev/null | head -1 || true)"
    [ -n "$PORT" ] || { echo "ERROR: no /dev/cu.usbserial* device found." >&2; exit 1; }
fi

# take the port: stop any serial monitor currently attached to it (it would
# otherwise consume esptool's bytes and corrupt the flash handshake)
HOLDERS="$(lsof -t "$PORT" 2>/dev/null || true)"
if [ -n "$HOLDERS" ]; then
    echo "freeing $PORT (stopping pid(s): $HOLDERS)"
    kill -INT $HOLDERS 2>/dev/null || true
    sleep 1
fi

PY="${IDF_PYTHON_ENV_PATH:-/Volumes/1TB_DAVINCI/.espressif/python_env/idf5.2_py3.12_env}/bin/python"
CHIP="$(sed -n 's/^CONFIG_IDF_TARGET="\(.*\)"$/\1/p' "$BUILD_DIR/sdkconfig" | head -1)"
CHIP="${CHIP:-esp32}"

cd "$BUILD_DIR"
if [ "$FULL" = "1" ]; then
    echo "=== full flash (bootloader + partitions + app) to $PORT @ $BAUD ==="
    exec "$PY" -m esptool --chip "$CHIP" --port "$PORT" -b "$BAUD" \
        --before default_reset --after hard_reset write_flash "@flash_args"
else
    echo "=== app-only flash to $PORT @ $BAUD ==="
    # app offset comes from flash_args (0x10000 on these boards); read it so a
    # different partition layout still deploys to the right place
    APP_OFFSET="$(awk '$2 == "micropython.bin" {print $1}' flash_args)"
    exec "$PY" -m esptool --chip "$CHIP" --port "$PORT" -b "$BAUD" \
        --before default_reset --after hard_reset write_flash \
        --flash_mode keep --flash_freq keep --flash_size keep \
        "${APP_OFFSET:-0x10000}" micropython.bin
fi
